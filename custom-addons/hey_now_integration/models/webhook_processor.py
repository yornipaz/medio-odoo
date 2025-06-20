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
            )  and not 
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
            body = self._generate_message_body(message.content, attachment_models)
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

    def _generate_message_body(
        self, original_body: str, attachments: List[models.Model]
    ) -> str:
        """
        Genera el contenido del body del mensaje incluyendo vista previa de imágenes y enlaces a archivos.
        """
        preview_parts = []

        for att in attachments:
            mimetype = att.mimetype or ""
            file_url = f"/web/content/{att.id}"

            if mimetype.startswith("image/"):
                # Mostrar imagen
                preview_parts.append(
                    f'<img src="{file_url}" style="max-width: 400px;" /><br/>'
                )
            elif mimetype == "application/pdf":
                # Mostrar PDF embebido
                preview_parts.append(
                    f'<embed src="{file_url}" type="application/pdf" width="100%" height="600px"><br/>'
                )
            else:
                # Mostrar como enlace
                preview_parts.append(
                    f'<a href="{file_url}" target="_blank">📎 {att.name}</a><br/>'
                )

        # Combinar el texto original con los previews
        return (original_body or "") + "<br/>" + "".join(preview_parts)
