from typing import List
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
from .payloads.dispatcher import WebhookDispatcher
from .payloads.base_event import FileEvent, BaseEvent

_logger = logging.getLogger(__name__)


class WebhookProcessor(models.Model):
    _name = "webhook.processor"
    _description = "Webhook Event Processor"

    name = fields.Char(string="Name", default="Webhook Processor")

    def process_webhook_event(self, provider_name: str, payload_data):
        """
        Procesar evento de webhook con protección mejorada contra duplicados.
        """

        with self.env.cr.savepoint():
            try:
                dispatcher_webhook = WebhookDispatcher(provider_name, payload_data)
                payload = dispatcher_webhook.extract_event()

                if not payload.is_incoming:

                    return {"status": "skipped", "message": "Not an incoming message"}

                message_id = payload.message.message_id_provider_chat

                # ✅ VERIFICACIÓN MEJORADA DE DUPLICADOS
                if message_id:
                    # Verificar si ya existe con lock
                    if self._check_and_lock_duplicate(message_id):
                        _logger.info(
                            "Duplicate message detected and skipped: %s", message_id
                        )
                        return {
                            "status": "duplicate",
                            "message": "Message already processed",
                            "message_id": message_id,
                        }

                # Procesar el webhook
                result = self._process_webhook_core(
                    provider_name,
                    payload.user_id,
                    payload.message,
                    payload.channel_name or provider_name,
                    payload.user_name,
                    payload,
                )

                return result

            except ValueError as e:
                _logger.error("Validation error processing webhook: %s", str(e))
                raise
            except Exception as e:
                _logger.error("Unexpected error processing webhook: %s", str(e))
                raise

    def _check_and_lock_duplicate(self, message_id_provider_chat):
        """
        Verificar duplicados con bloqueo de fila para evitar condiciones de carrera.
        Retorna True si es duplicado, False si es nuevo.
        """
        if not message_id_provider_chat:
            return False

        try:
            # Intentar obtener un lock exclusivo en la fila si existe
            self.env.cr.execute(
                """
                SELECT id FROM mail_message
                WHERE message_id_provider_chat = %s
                FOR UPDATE NOWAIT
            """,
                (message_id_provider_chat,),
            )

            result = self.env.cr.fetchone()
            if result:
                # Ya existe el mensaje
                return True

            # No existe, continuamos con el procesamiento
            return False

        except Exception as e:
            # Si hay error obteniendo el lock, probablemente otro proceso lo está procesando
            _logger.warning(
                "Could not acquire lock for message %s: %s",
                message_id_provider_chat,
                str(e),
            )
            return True  # Asumir duplicado para evitar procesamiento concurrente

    def _process_webhook_core(
        self, provider_name, user_id, message, channel_name, user_name, payload
    ):
        """Lógica core del procesamiento del webhook"""

        if not user_id:
            raise ValueError("user_id is required")

        # Obtener o crear el partner
        partner = self.env["res.partner"].find_or_create_partner(
            {
                "user_id": user_id,
                "provider_name": provider_name,
                "user_name": user_name,
                "user_channel": channel_name or provider_name,
            }
        )

        if not partner:
            raise ValueError("Partner not found or created")

        # Obtener usuario interno
        internal_user = self._get_internal_user()
        if not internal_user:
            raise ValueError("Internal user not found")

        # Crear o buscar canal
        members = [partner.id, internal_user.id]
        channel = self.env["mail.channel"].find_or_create_channel(
            provider_name=provider_name,
            channel_name=channel_name or provider_name,
            partner_ids=members,
            external_channel_id=user_id,
            extra_metadata=payload.metadata or {},
        )

        # Crear mensaje con verificación final
        message_channel = self._create_message_with_final_check(
            channel, message, partner, payload
        )

        return {
            "status": "success",
            "message": "Message received and processed successfully",
            "channel_id": channel.id,
            "partner_id": partner.id,
            "message_id": message_channel.id if message_channel else None,
        }

    def _create_message_with_final_check(
        self, channel, message, partner, payload: BaseEvent
    ):
        """
        Crear mensaje con verificación final por si acaso.
        """
        message_id_provider = getattr(message, "message_id_provider_chat", None)

        # ✅ VERIFICACIÓN FINAL MEJORADA
        if message_id_provider:
            # Usar el método mejorado de verificación
            existing = self.env["mail.message"].check_duplicate_by_provider_id(
                message_id_provider
            )
            if existing:

                return existing

        # Crear el mensaje
        try:
            # ✅ PROCESAR ARCHIVOS SI EXISTEN
            message_event = payload.message
            attachment_ids = []

            if hasattr(message_event, "files") and message_event.files:
                attachment_ids = self._process_message_files(
                    channel, message_event.files
                )
            attachment_models = self.env["ir.attachment"].sudo().browse(attachment_ids)
            body = self.generate_message_body_native(message.content, attachment_models)
            # ✅ CREAR MENSAJE DE WEBHOOK - SIEMPRE skip_send_to_provider=True
            message_channel = channel.with_context(
                skip_send_to_provider=True,  # ✅ NUNCA reenviar mensajes de webhook
                webhook_source=True,
            ).message_post(
                body=body,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                author_id=partner.id,
                attachment_ids=attachment_ids,  # ✅ ARCHIVOS ADJUNTOS
            )

            # ✅ MARCAR CORRECTAMENTE EL MENSAJE
            if message_channel:
                values_to_write = {
                    "is_from_webhook": True,  # ✅ Marcar como webhook
                }

                # ✅ SOBRESCRIBIR EL UUID CON EL DEL PROVEEDOR
                if message_id_provider:
                    values_to_write["message_id_provider_chat"] = message_id_provider

                message_channel.write(values_to_write)

                _logger.info(
                    "Created webhook message %s with provider_id: %s",
                    message_channel.id,
                    message_id_provider,
                )

            return message_channel

        except Exception as e:
            _logger.error("Error creating message: %s", str(e))
            raise

    def _get_internal_user(self):
        """Obtener el usuario interno (operador del chat)"""
        return self.env.ref("base.user_admin").sudo().partner_id

    def _process_message_files(self, channel, files: List[FileEvent]) -> List[int]:
        """
        Procesar lista de FileEvent y crear attachments
        Retorna lista de IDs de attachments creados
        """
        attachment_ids = []

        try:
            for file_event in files:
                attachment = self._create_attachment_from_file_event(
                    channel, file_event
                )
                if attachment:
                    attachment_ids.append(attachment.id)
                else:
                    _logger.warning(
                        "Failed to create attachment for file: %s", file_event.name
                    )

            _logger.info(
                "Processed %s files, created %s attachments",
                len(files),
                len(attachment_ids),
            )
            return attachment_ids

        except Exception as e:
            _logger.error("Error processing message files: %s", str(e))
            return attachment_ids  # Retornar los que sí se crearon

    def _create_attachment_from_file_event(self, channel, file_event: FileEvent):
        """Crear ir.attachment desde FileEvent Maneja tanto URLs como datos base64"""

        try:
            # ✅ CASO 1: Si hay URL, descargar archivo
            if file_event.url:
                return self._download_and_create_attachment(file_event, channel)

            # ✅ CASO 2: Si hay datos base64, usar directamente
            elif file_event.datas:
                return self._create_attachment_from_data(channel, file_event)

            else:
                _logger.warning("FileEvent sin URL ni datos: %s", file_event.name)
                return False

        except Exception as e:
            _logger.error("Error processing FileEvent %s: %s", file_event.name, str(e))
            return False

    def _download_and_create_attachment(self, file_event: FileEvent, channel=None):
        """Descargar archivo desde URL y crear attachment"""
        try:
            import requests
            from urllib.parse import urlparse
            import mimetypes
            import base64

            response = requests.get(file_event.url, timeout=10)
            response.raise_for_status()

            # Convertir a base64
            file_data_b64 = base64.b64encode(response.content).decode("utf-8")

            # Detectar mimetype si no está definido
            mimetype = file_event.mimetype
            if not mimetype:
                mimetype = response.headers.get("content-type")
                if not mimetype:
                    mimetype, _ = mimetypes.guess_type(
                        file_event.url or file_event.name
                    )
                    mimetype = mimetype or "application/octet-stream"

            # Obtener nombre del archivo si no está definido
            name = file_event.name
            if not name:
                parsed_url = urlparse(file_event.url)
                path = parsed_url.path
                if isinstance(path, bytes):
                    path = path.decode("utf-8", errors="replace")
                name = path.split("/")[-1] or "archivo_descargado"

            # Crear attachment con todos los campos disponibles
            attachment_data = {
                "name": name,
                "type": file_event.type,
                "datas": file_data_b64,
                "res_model": "mail.channel",  # ✅ modelo correcto,
                "url": file_event.url,  # URL original si aplica
                "res_id": channel.id if channel else None,
                "mimetype": mimetype,
            }

            # ✅ CAMPOS OPCIONALES DE FileEvent
            if file_event.description:
                attachment_data["description"] = file_event.description
            if file_event.access_token:
                attachment_data["access_token"] = file_event.access_token
            if file_event.checksum:
                attachment_data["checksum"] = file_event.checksum

            attachment = self.env["ir.attachment"].sudo().create(attachment_data)

            _logger.info(
                "Downloaded and created attachment from URL: %s -> ID: %s",
                file_event.url,
                attachment.id,
            )
            return attachment

        except Exception as e:
            _logger.error(
                "Error downloading file from URL %s: %s", file_event.url, str(e)
            )
            return False

    def _create_attachment_from_data(self, channel, file_event: FileEvent):
        """Crear attachment desde datos base64 existentes"""
        try:
            import mimetypes

            # Limpiar base64 si viene con prefijo data:
            datas = file_event.datas
            if datas.startswith("data:"):
                # Extraer mimetype del data URI si no está definido
                if not file_event.mimetype:
                    mimetype_part = datas.split(";")[0].split(":")[1]
                    file_event.mimetype = mimetype_part
                datas = datas.split(",")[1]

            # Detectar mimetype si no está definido
            mimetype = file_event.mimetype
            if not mimetype and file_event.name:
                mimetype, _ = mimetypes.guess_type(file_event.name)
                mimetype = mimetype or "application/octet-stream"

            # Crear attachment con todos los campos
            attachment_data = {
                "name": file_event.name or "archivo_webhook",
                "type": file_event.type,
                "datas": datas,
                "res_model": "mail.channel",  # ✅ modelo correcto,
                "res_id": channel.id,
                "url": file_event.url,  # URL original si aplica
                "mimetype": mimetype,
            }

            # ✅ CAMPOS OPCIONALES DE FileEvent
            if file_event.description:
                attachment_data["description"] = file_event.description
            if file_event.access_token:
                attachment_data["access_token"] = file_event.access_token
            if file_event.checksum:
                attachment_data["checksum"] = file_event.checksum

            attachment = self.env["ir.attachment"].sudo().create(attachment_data)

            _logger.info(
                "Created attachment from base64 data: %s -> ID: %s",
                file_event.name,
                attachment.id,
            )
            return attachment

        except Exception as e:
            _logger.error(
                "Error creating attachment from base64 for %s: %s",
                file_event.name,
                str(e),
            )
            return False

    # ✅ MÉTODO AUXILIAR PARA VALIDAR ARCHIVOS ANTES DE PROCESAR
    def _validate_file_event(self, file_event: FileEvent) -> bool:
        """Validar que FileEvent tiene los datos mínimos necesarios"""
        if not file_event.name:
            _logger.warning("FileEvent without name")
            return False

        if not file_event.url and not file_event.datas:
            _logger.warning("FileEvent %s without URL or data", file_event.name)
            return False

        # Validar que base64 es válido si está presente
        if file_event.datas:
            try:
                # Limpiar prefijo si existe
                data_to_validate = file_event.datas
                if data_to_validate.startswith("data:"):
                    data_to_validate = data_to_validate.split(",")[1]

                # Intentar decodificar
                base64.b64decode(data_to_validate)
                return True
            except Exception as e:
                _logger.warning(
                    "FileEvent %s has invalid base64 data: %s", file_event.name, str(e)
                )
                return False

        return True
        # Método adicional para limpiar mensajes duplicados si ya existen

    @api.model
    def cleanup_duplicate_messages(self):
        """
        Método de utilidad para limpiar mensajes duplicados existentes.
        Ejecutar manualmente si ya tienes duplicados.
        """
        _logger.info("Starting duplicate cleanup...")

        # Buscar mensajes duplicados
        self.env.cr.execute(
            """
            SELECT message_id_provider_chat, array_agg(id ORDER BY id) as ids
            FROM mail_message 
            WHERE message_id_provider_chat IS NOT NULL
            GROUP BY message_id_provider_chat
            HAVING COUNT(*) > 1
        """
        )

        duplicates = self.env.cr.fetchall()

        for message_id_provider, ids in duplicates:
            # Mantener el primer mensaje, eliminar los demás
            keep_id = ids[0]
            delete_ids = ids[1:]

            _logger.info(
                "Found duplicates for %s: keeping %s, deleting %s",
                message_id_provider,
                keep_id,
                delete_ids,
            )

            # Eliminar los duplicados
            self.env["mail.message"].browse(delete_ids).unlink()

        _logger.info(
            "Duplicate cleanup completed. Processed %s groups", len(duplicates)
        )

    # Método para obtener estadísticas de procesamiento
    @api.model
    def get_processing_stats(self):
        """Obtener estadísticas de procesamiento de webhooks"""

        # Contar mensajes por proveedor
        self.env.cr.execute(
            """
            SELECT 
                CASE 
                    WHEN message_id_provider_chat IS NOT NULL THEN 'webhook'
                    ELSE 'regular'
                END as source_type,
                COUNT(*) as count
            FROM mail_message
            WHERE create_date >= NOW() - INTERVAL '24 hours'
            GROUP BY source_type
        """
        )

        stats = dict(self.env.cr.fetchall())

        return {
            "webhook_messages_24h": stats.get("webhook", 0),
            "regular_messages_24h": stats.get("regular", 0),
            "total_messages_24h": sum(stats.values()),
        }

    # Método alternativo usando templates nativos de Odoo

    def generate_message_body_native(
        self, original_body: str, attachments: List[models.Model]
    ) -> str:
        """
        Genera el contenido usando el motor de templates nativo de Odoo
        para obtener exactamente la misma representación.
        """
        if not attachments:
            return original_body or ""
        return self.generate_message_body(original_body, attachments)

        # # Renderizar usando el template nativo de mail.message
        # try:
        #     # Obtener el template de attachments de Odoo
        #     template = (
        #         self.env["ir.ui.view"]
        #         .sudo()
        #         ._render_template(
        #             "mail.message_attachment_list",
        #             {
        #                 "attachments": attachments,
        #                 "message": self,  # Si tienes acceso al mensaje
        #             },
        #         )
        #     )

        #     body_parts = [original_body or "", template]
        #     return "<br/>".join(filter(None, body_parts))

        # except Exception as e:
        #     # Fallback al método manual si no funciona el template
        #     return self.generate_message_body(original_body, attachments)

    def generate_message_body(
        self, original_body: str, attachments: List[models.Model]
    ) -> str:
        """
        Genera el contenido del body del mensaje usando el mismo formato
        que Odoo utiliza nativamente para los attachments.
        """
        if not attachments:
            return original_body or ""

        # El body original va primero
        body_parts = [original_body or ""]

        # Generar los attachments usando la estructura nativa de Odoo
        attachment_html = self._generate_native_attachments_html(attachments)
        if attachment_html:
            body_parts.append(attachment_html)

        return "<br/>".join(filter(None, body_parts))

    def _generate_native_attachments_html(self, attachments: List[models.Model]) -> str:
        """
        Genera HTML para attachments usando la estructura nativa de Odoo.
        """
        if not attachments:
            return ""

        attachment_items = []

        for attachment in attachments:
            attachment_html = self._render_single_attachment(attachment)
            if attachment_html:
                attachment_items.append(attachment_html)

        if not attachment_items:
            return ""

        # Contenedor principal similar al que usa Odoo
        return f"""
        <div class="o_mail_attachment_list">
            {"".join(attachment_items)}
        </div>
        """

    def _render_single_attachment(self, attachment) -> str:
        """
        Renderiza un attachment individual usando la estructura de Odoo.
        """

        mimetype = attachment.mimetype or ""
        file_size = self._format_file_size(attachment.file_size or 0)
        file_url = f"/web/content/{attachment.id}"
        download_url = f"/web/content/{attachment.id}?download=true"

        # Determinar el icono basado en el tipo de archivo
        file_icon = self._get_file_icon(mimetype, attachment.name)

        if mimetype.startswith("image/"):
            return self._render_image_attachment(
                attachment, file_url, download_url, file_size
            )
        elif mimetype == "application/pdf":
            return self._render_pdf_attachment(
                attachment, file_url, download_url, file_size, file_icon
            )
        elif mimetype.startswith("video/"):
            return self._render_video_attachment(
                attachment, file_url, download_url, file_size, file_icon
            )
        elif mimetype.startswith("audio/"):
            return self._render_audio_attachment(
                attachment, file_url, download_url, file_size, file_icon
            )
        else:
            return self._render_generic_attachment(
                attachment, file_url, download_url, file_size, file_icon
            )

    def _render_image_attachment(
        self, attachment, file_url, download_url, file_size
    ) -> str:
        """Renderiza attachment de imagen como lo hace Odoo."""
        import mimetypes

        extension = mimetypes.guess_extension(attachment.mimetype) or ".jpg"
        return f"""
            <div class="o_AttachmentList_partialList o_AttachmentList_partialListImages d-flex flex-grow-1 flex-wrap">
	            <div role="menu" class="o_AttachmentList_attachment mw-100 mb-1 me-1" aria-label="{attachment.name+extension}" >
	        	    <div class="o_AttachmentImage d-flex position-relative flex-shrink-0" tabindex="0" aria-label="View image" role="menuitem" title="{attachment.name}{extension}" data-id="{attachment.id}" data-mimetype="{attachment.mimetype}">
	        		    <img class="img img-fluid my-0 mx-auto" src="{file_url}"  alt="{attachment.name}{extension}" style="max-width: min(100%, 1920px); max-height: 300px;">
	        			    <div class="o_AttachmentImage_imageOverlay position-absolute top-0 bottom-0 start-0 end-0 p-2 text-white opacity-0 opacity-100-hover d-flex align-items-end flax-wrap flex-column">
	        				  
	        				    <div class="o_AttachmentImage_action o_AttachmentImage_actionDownload btn btn-sm btn-dark rounded opacity-75 opacity-100-hover mt-auto" title="Descargar">
                					     <a href="{download_url}" class="o_AttachmentCard_asideItem o_AttachmentCard_asideItemUnlink btn top-0 justify-content-center align-items-center d-flex w-100 h-100 rounded-0 bg-300" 
                                            title="Descargar" download="{attachment.name}{extension}">
                                            <i class="fa fa-download"></i>
                                         </a>
	        				    </div>
	        			    </div>
	        		</div>
	        	</div>
	        </div>
        """

    def _render_pdf_attachment(
        self, attachment, file_url, download_url, file_size, file_icon
    ) -> str:
        """Renderiza attachment PDF como lo hace Odoo."""
        return f"""
        	<div class="o_AttachmentList_attachment mw-100 mb-1 me-1">
        		<div class="o_AttachmentCard o-has-card-details d-flex rounded bg-300 o-viewable" role="menu" title="{attachment.name}.pdf" aria-label="{attachment.name}.pdf" data-id="{attachment.id}">
        			<div class="o_AttachmentCard_image o_image flex-shrink-0 m-1 o-attachment-viewable opacity-75-hover" role="menuitem" aria-label="Preview" tabindex="0" data-mimetype="application/pdf"></div>
        			<div class="o_AttachmentCard_details d-flex justify-content-center flex-column px-1">
        				<div class="o_AttachmentCard_filename text-truncate">{attachment.name}.pdf</div>
        				<small class="o_AttachmentCard_extension text-uppercase">pdf</small>
        			</div>
        			<div class="o_AttachmentCard_aside position-relative rounded-end overflow-hidden o-hasMultipleActions d-flex flex-column">
                    	<button class="o_AttachmentCard_asideItem o_AttachmentCard_asideItemUnlink btn top-0 justify-content-center align-items-center d-flex w-100 h-100 rounded-0 bg-300" title="Eliminar">
                    		<i class="fa fa-trash" role="img" aria-label="Remove"></i>
                    	</button>
                    	  <a href="{download_url}" class="o_AttachmentCard_asideItem o_AttachmentCard_asideItemUnlink btn top-0 justify-content-center align-items-center d-flex w-100 h-100 rounded-0 bg-300" 
                       title="Descargar" download="{attachment.name}.pdf">
                        <i class="fa fa-download"></i>
                        </a>
                    </div>
        		</div>
        	</div>
        """

    def _render_video_attachment(
        self, attachment, file_url, download_url, file_size, file_icon
    ) -> str:
        """Renderiza attachment de video."""
        return f"""
        <div class="o_mail_attachment o_mail_attachment_video" data-id="{attachment.id}">
            <div class="o_mail_attachment_video_container">
                <video controls style="max-width: 100%; max-height: 300px;">
                    <source src="{file_url}" type="{attachment.mimetype}">
                    Tu navegador no soporta el elemento video.
                </video>
            </div>
            <div class="o_mail_attachment_info">
                <div class="o_mail_attachment_info_text">
                    <i class="{file_icon}"></i>
                    <span class="o_mail_attachment_name" title="{attachment.name}">{attachment.name}</span>
                    <small class="o_mail_attachment_size text-muted">{file_size}</small>
                </div>
                <div class="o_mail_attachment_actions">
                    <a href="{download_url}" class="o_mail_attachment_download btn btn-sm btn-outline-secondary" 
                       title="Descargar" download="{attachment.name}">
                        <i class="fa fa-download"></i>
                    </a>
                </div>
            </div>
        </div>
        """

    def _render_audio_attachment(
        self, attachment, file_url, download_url, file_size, file_icon
    ) -> str:
        """Renderiza attachment de audio."""
        return f"""
        <div class="o_mail_attachment o_mail_attachment_audio" data-id="{attachment.id}">
            <div class="o_mail_attachment_audio_container">
                <audio controls style="width: 100%;">
                    <source src="{file_url}" type="{attachment.mimetype}">
                    Tu navegador no soporta el elemento audio.
                </audio>
            </div>
            <div class="o_mail_attachment_info">
                <div class="o_mail_attachment_info_text">
                    <i class="{file_icon}"></i>
                    <span class="o_mail_attachment_name" title="{attachment.name}">{attachment.name}</span>
                    <small class="o_mail_attachment_size text-muted">{file_size}</small>
                </div>
                <div class="o_mail_attachment_actions">
                    <a href="{download_url}" class="o_mail_attachment_download btn btn-sm btn-outline-secondary" 
                       title="Descargar" download="{attachment.name}">
                        <i class="fa fa-download"></i>
                    </a>
                </div>
            </div>
        </div>
        """

    def _render_generic_attachment(
        self, attachment, file_url, download_url, file_size, file_icon
    ) -> str:
        """Renderiza attachment genérico como lo hace Odoo."""
        return f"""
        <div class="o_mail_attachment o_mail_attachment_generic" data-id="{attachment.id}">
            <div class="o_mail_attachment_info">
                <div class="o_mail_attachment_info_text">
                    <i class="{file_icon}"></i>
                    <span class="o_mail_attachment_name" title="{attachment.name}">{attachment.name}</span>
                    <small class="o_mail_attachment_size text-muted">{file_size}</small>
                </div>
                <div class="o_mail_attachment_actions">
                    <a href="{file_url}" class="btn btn-sm btn-outline-primary" target="_blank" title="Abrir">
                        <i class="fa fa-external-link"></i>
                    </a>
                    <a href="{download_url}" class="o_mail_attachment_download btn btn-sm btn-outline-secondary" 
                       title="Descargar" download="{attachment.name}">
                        <i class="fa fa-download"></i>
                    </a>
                </div>
            </div>
        </div>
        """

    def _get_file_icon(self, mimetype: str, filename: str) -> str:
        """Retorna el icono apropiado para el tipo de archivo."""
        if mimetype.startswith("image/"):
            return "fa fa-file-image-o"
        elif mimetype == "application/pdf":
            return "fa fa-file-pdf-o"
        elif mimetype.startswith("video/"):
            return "fa fa-file-video-o"
        elif mimetype.startswith("audio/"):
            return "fa fa-file-audio-o"
        elif mimetype in [
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]:
            return "fa fa-file-word-o"
        elif mimetype in [
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]:
            return "fa fa-file-excel-o"
        elif mimetype in [
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ]:
            return "fa fa-file-powerpoint-o"
        elif mimetype == "application/zip" or mimetype.startswith("application/x-"):
            return "fa fa-file-archive-o"
        elif mimetype == "text/plain":
            return "fa fa-file-text-o"
        else:
            return "fa fa-file-o"

    def _format_file_size(self, size_bytes: int) -> str:
        """Formatea el tamaño del archivo de manera legible."""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        size = float(size_bytes)

        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1

        return f"{size:.1f} {size_names[i]}"
