from .provider import Provider
from typing import Dict, Any


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
            "partnerUser": {"id": 49, "names": "Alejandro", "lastNames": "Marin"},
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

        return self.env["ir.config_parameter"].sudo().get_param("provider.token")

    def _get_base_url(self) -> str:

        return self.env["ir.config_parameter"].sudo().get_param("provider.base_url")

    def _get_patner_user(self) -> Dict[str, Any]:
        # logica para obtener el para el partner user de hey now

        return {"id": 49, "names": "Alejandro", "lastNames": "Marin"}

    def _clean_html(self, body) -> str:
        """
        Convierte el contenido HTML del mail.message.body en texto plano apto para WhatsApp.
        """
        from bs4 import BeautifulSoup
        from markupsafe import Markup

        if isinstance(body, Markup):
            body = str(body)

        soup = BeautifulSoup(body, "html.parser")

        # Eliminar imágenes (emojis, stickers, etc.)
        for img in soup.find_all("img"):
            img.decompose()

        # Eliminar elementos de formato innecesarios
        for tag in soup(["script", "style"]):
            tag.decompose()

        # Eliminar spans y elementos vacíos o con datos técnicos
        for span in soup.find_all("span"):
            if not span.get_text(strip=True):
                span.decompose()

        # Convertir a texto plano
        text = soup.get_text(separator=" ", strip=True)

        # Limpiar múltiples espacios
        return " ".join(text.split())
