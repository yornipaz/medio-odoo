from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
from .payloads.dispatcher import WebhookDispatcher

_logger = logging.getLogger(__name__)


class WebhookProcessor(models.Model):
    _name = "webhook.processor"
    _description = "Webhook Event Processor"

    name = fields.Char(string="Name", default="Webhook Processor")

    def process_webhook_event(self, provider_name, webhook_data):
        """
        Procesar evento de webhook con protección mejorada contra duplicados.
        """
        _logger.info("Processing webhook event for provider: %s", provider_name)

        with self.env.cr.savepoint():
            try:
                # Extraer datos del mensaje
                dispatcher = WebhookDispatcher(provider_name, webhook_data)
                payload = dispatcher.extract_event()

                if not payload.is_incoming:
                    _logger.info("Skipping non-incoming message")
                    return {"status": "skipped", "message": "Not an incoming message"}

                message_id = payload.message.message_id_provider_chat
                _logger.info("Processing message ID: %s", message_id)

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

                _logger.info("Webhook processed successfully: %s", result)
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

    def _create_message_with_final_check(self, channel, message, partner, payload):
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
                _logger.warning(
                    "Message already exists during final check: %s", message_id_provider
                )
                return existing

        # Crear el mensaje
        try:
            # ✅ CREAR MENSAJE DE WEBHOOK - SIEMPRE skip_send_to_provider=True
            message_channel = channel.with_context(
                skip_send_to_provider=True,  # ✅ NUNCA reenviar mensajes de webhook
                webhook_source=True,
            ).message_post(
                body=message.content,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                author_id=partner.id,
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
