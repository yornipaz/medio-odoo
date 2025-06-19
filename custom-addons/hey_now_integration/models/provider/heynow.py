from .provider_type import ProviderType
from .provider import Provider
from typing import Dict, Any
from .chat_provider_config import ChatProviderConfig


class HeynowProvider(Provider):
    """
    Heynow provider class.
    """

    def __init__(self, env):
        """
        Initialize the HeynowProvider with Odoo environment.

        :param env: Odoo environment object
        """
        self.env = env
        self._provider_config = None
        self._provider_name = ProviderType.HEYNOW.value

    def get_url(self, config=None) -> str:
        """
        Get the URL of the Heynow API.

        :return: The URL as a string.
        """
        url_base = self._get_base_url()
        if config:
            # If a config is provided, use it to construct the URL
            url_base = config.get("url_base", url_base)
            if not url_base.endswith("/"):
                url_base += "/"
            channel = config.get("channel", "")
            platform_id = config.get("platformId", "")
            client_id = config.get("clientId", "")
            session_id = config.get("session", "")

            url_base += f"{channel}/{platform_id}/{client_id}/{session_id}"
            return url_base

        return url_base

    def get_headers(self) -> Dict[str, str]:
        """
        Get the headers required for API requests to Heynow.

        :return: A dictionary of headers.
        """
        headers = {
            "Content-Type": "application/json",
        }

        # Obtener el token desde los parámetros del sistema de Odoo
        partner_token = self._get_auth_token()
        if partner_token:
            headers["partner-token"] = partner_token

        return headers

    def get_payload(
        self, message: Dict[str, Any], config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Get the payload to be sent to Heynow.

        :param data: The data to include in the payload.
        :return: A dictionary representing the payload.
        """
        message_text = self._clean_html(message.body)

        payload = {
            "text": message_text,
            "partnerUser": self._get_partner_user(),
            "idMessageHey": message.message_id_provider_chat,
        }
        if message.attachment_ids:
            attachment = message.attachment_ids[0]
            payload["file"] = {
                "data": attachment.datas,
                "name": attachment.name,
                "encode": "base64",
                "mimeType": attachment.mimetype,
            }

        return payload

    def _get_auth_token(self) -> str:
        token = ""
        try:
            self._provider_config = self.get_provider_config()
            token = self._provider_config.auth_token
        except Exception as e:
            self.env["ir.logging"].sudo().create(
                {
                    "name": "HeynowProvider",
                    "type": "server",
                    "dbname": self.env.cr.dbname,
                    "level": "ERROR",
                    "message": f"Error retrieving auth token: {str(e)}",
                    "path": __file__,
                    "func": "_get_auth_token",
                    "line": "",
                }
            )

        return token

    def _get_base_url(self) -> str:

        if not self._provider_config:
            self._provider_config = self.get_provider_config()

        if self._provider_config.base_url:
            return self._provider_config.base_url

        return ""

    def _get_partner_user(self) -> Dict[str, Any]:
        # logica para obtener el para el partner user de hey now
        if not self._provider_config:
            self._provider_config = self.get_provider_config()

        if self._provider_config.config_extra:
            return self._provider_config.config_extra.get("partnerUser", {})

        return {}

    def _clean_html(self, body) -> str:
        return self.clear_html_message(body)

    def get_provider_config(self) -> ChatProviderConfig:
        """
        Retrieve the provider configuration from the Odoo environment.

        :return: The provider configuration object.
        """

        provider = self.env["chat.provider"].search(
            [("provider_type", "=", self._provider_name)], limit=1
        )
        if not provider:
            raise ValueError(f"Provider not found: heynow")
        return ChatProviderConfig(
            id=provider.id,
            name=provider.name,
            provider_type=provider.provider_type,
            is_active=provider.is_active,
            base_url=provider.base_url,
            auth_token=provider.auth_token,
            allowed_channel_ids=provider.allowed_channel_ids,
            config_extra=provider.get_config_extra_dict(),
        )
