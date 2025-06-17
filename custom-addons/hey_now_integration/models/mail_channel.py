from .provider.dispatcher import ProviderDispatcher
from odoo import models, fields, api
import requests
import logging
import json

_logger = logging.getLogger(__name__)


class MailChannel(models.Model):
    _inherit = "mail.channel"

    provider_metadata = fields.Json("Provider Metadata")
    provider_name = fields.Text("Nombre del proveedor")
    external_channel_id = fields.Text("ID del canal externo")

    @api.model
    def message_post(self, **kwargs):
        """Override message_post to send responses to webhook"""

        # ✅ VERIFICACIONES PARA EVITAR LOOPS

        # 1. Si tiene flag para evitar reenvío al proveedor
        if self.env.context.get("skip_send_to_provider"):
            return super().message_post(**kwargs)

        # 2. Si es mensaje de webhook
        if self.env.context.get("webhook_source"):
            return super().message_post(**kwargs)

        # Crear mensaje normalmente (con UUID automático)
        message = super().message_post(**kwargs)

        _logger.info(
            "Processing message_post for channel %s, message %s", self.id, message.id
        )

        # ✅ LÓGICA CORRECTA: Solo enviar mensajes de usuarios internos
        should_send_to_provider = (
            self.channel_type == "chat"
            and message.author_id
            and not getattr(message.author_id, "is_provider_chat_user", False)
            and message.message_type == "comment"
            and self.provider_name  # Solo si tiene proveedor configurado
            and not getattr(
                message, "is_from_webhook", False
            )  # ✅ NO enviar mensajes de webhook
        )

        if should_send_to_provider:
            try:
                _logger.info(
                    "Sending internal message to provider: %s (UUID: %s)",
                    message.id,
                    message.message_id_provider_chat,
                )
                self._send_to_provider(message, self.provider_name)
            except Exception as e:
                _logger.error(f"Error sending message to provider: {e}")
                # No fallar el message_post por errores en el envío al proveedor
        else:
            _logger.info(
                "Skipping send to provider for message %s - is_from_webhook: %s",
                message.id,
                getattr(message, "is_from_webhook", False),
            )

        return message

    def _send_to_provider(self, message, provider_name: str = "Botpress"):
        """Enviar mensaje al webhook del proveedor - versión simplificada"""
        try:
            # Obtener el proveedor
            provider = ProviderDispatcher(provider_name, self.env).get_provider()

            # Obtener la URL del webhook
            webhook_url = provider.get_url(config=self.provider_metadata)
            if not webhook_url:
                _logger.warning("No webhook URL configured for %s", provider_name)
                return

            _logger.info(
                "Sending message to provider %s at URL: %s", provider_name, webhook_url
            )

            # Preparar los datos para enviar
            payload = provider.get_payload(message)
            headers = provider.get_headers()

            # Enviar con timeout optimizado
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=10,  # Timeout reducido
            )

            if response.status_code == 200:
                _logger.info("Message sent to provider successfully")
            else:
                _logger.error(
                    "Failed to send message to provider. Status: %s, Response: %s",
                    response.status_code,
                    response.text,
                )

        except ValueError as e:
            _logger.error("Provider configuration error: %s", str(e))
        except requests.exceptions.Timeout:
            _logger.error("Timeout sending message to provider")
        except requests.exceptions.RequestException as e:
            _logger.error("Request error sending message to provider: %s", str(e))
        except Exception as e:
            _logger.error("Unexpected error sending message to provider: %s", str(e))

    def find_or_create_channel(
        self,
        provider_name: str,
        channel_name: str,
        external_channel_id: str,
        partner_ids: list,
        extra_metadata=None,
    ):
        """
        Busca un canal existente o crea uno nuevo - Versión simplificada.
        Queue Jobs maneja la concurrencia, no necesitamos locks complejos.
        """
        # Buscar canal existente
        channel = self.sudo().search(
            [
                ("external_channel_id", "=", external_channel_id),
                ("channel_type", "=", "chat"),
            ],
            limit=1,
        )

        if channel:
            _logger.info("Found existing channel: %s", channel.id)

            # Verificar y actualizar miembros si es necesario
            current_partner_ids = set(channel.channel_partner_ids.ids)
            expected_partner_ids = set(partner_ids)

            if current_partner_ids != expected_partner_ids:
                missing_partners = expected_partner_ids - current_partner_ids
                if missing_partners:
                    _logger.info("Adding missing partners: %s", list(missing_partners))
                    channel.add_members(list(missing_partners))

            # Actualizar metadata si es diferente
            if extra_metadata and not self._compare_provider_metadata(
                channel.provider_metadata, extra_metadata
            ):
                _logger.info("Updating channel metadata")
                channel.write({"provider_metadata": extra_metadata})

            return channel

        # Crear nuevo canal - Sin manejo complejo de concurrencia
        _logger.info("Creating new channel for external_id: %s", external_channel_id)

        try:
            channel = self.sudo().create(
                {
                    "name": channel_name,
                    "channel_type": "chat",
                    "description": f"Canal de chat para {channel_name}",
                    "provider_name": provider_name,
                    "external_channel_id": external_channel_id,
                    "provider_metadata": extra_metadata or {},
                }
            )

            # Agregar miembros
            channel.add_members(partner_ids)

            _logger.info("Created new channel: %s", channel.id)
            return channel

        except Exception as e:
            _logger.error(f"Error creating channel: {e}")

            # Buscar de nuevo por si otro job lo creó mientras tanto
            channel = self.sudo().search(
                [
                    ("external_channel_id", "=", external_channel_id),
                    ("channel_type", "=", "chat"),
                ],
                limit=1,
            )

            if channel:
                _logger.info("Channel was created by another process: %s", channel.id)
                return channel
            else:
                raise

    def _compare_provider_metadata(self, current_metadata, new_metadata):
        """Comparar metadata del proveedor para detectar cambios"""
        try:
            current_str = json.dumps(current_metadata or {}, sort_keys=True)
            new_str = json.dumps(new_metadata or {}, sort_keys=True)
            return current_str == new_str
        except Exception as e:
            _logger.error(f"Error comparing metadata: {e}")
            return False
