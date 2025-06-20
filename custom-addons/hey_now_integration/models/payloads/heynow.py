import datetime
from typing import Dict, Any, List
from uuid import uuid4
from .base_event import MessageEvent, MessageEventType, FileEvent
from ..provider.provider_type import ProviderType
from .base_event import BaseEvent
from enum import Enum
import logging

_logger = logging.getLogger(__name__)


class HeynowChannelType(Enum):
    WHATSAPP = 1
    FACEBOOK_MESSENGER = 2
    TWITTER = 3
    WEB_CHAT = 4
    FACEBOOK_WALL = 5
    WAVY = 6
    INSTAGRAM = 7
    MERCADO_LIBRE = 8
    SINCH = 9
    MERCADO_LIBRE_MENSAJES = 10
    CALL = 11
    PS_TWILIO = 12
    PS_YOUTUBE = 13
    PS_SMOOCH_WSP = 14
    PS_TWITTER_DM = 15
    PS_INSTAGRAM = 16
    PS_WAVY = 17
    PS_TWITTER = 18
    PS_WABOX = 19
    PS_MESSENGER = 20
    PS_ONEMARKETER = 21
    PS_TWITTER_TWEET = 22
    PS_FEED = 23
    TWITTER_DM = 24
    GOOGLE_BUSINESS_MESSAGES = 25
    MERCADO_LIBRE_RECLAMOS = 26
    BOTMAKER = 27
    TEAMS = 28
    TELEGRAM = 29
    API_CHANNEL = 30
    INSTAGRAM_DIRECT = 31
    SINCH_SMS = 32
    DIALOG_360 = 33
    TWILIO = 34
    WHATSAPP_CLOUD = 35
    GUPSHUP = 36
    HEY_TEST_CHANNEL = 37
    T2_VOICE = 38
    MAILBOT = 39
    FLOW_SERVICE = 40

    def etiqueta(self):
        etiquetas = {
            self.WHATSAPP: "WhatsApp",
            self.FACEBOOK_MESSENGER: "Facebook Messenger",
            self.TWITTER: "Twitter",
            self.WEB_CHAT: "Web Chat",
            self.FACEBOOK_WALL: "Facebook Muro",
            self.WAVY: "Wavy",
            self.INSTAGRAM: "Instagram",
            self.MERCADO_LIBRE: "Mercado Libre",
            self.SINCH: "Sinch",
            self.MERCADO_LIBRE_MENSAJES: "Mercado Libre (Mensajes)",
            self.CALL: "Call",
            self.PS_TWILIO: "ps_twilio",
            self.PS_YOUTUBE: "ps_youtube",
            self.PS_SMOOCH_WSP: "ps_smooch-wsp",
            self.PS_TWITTER_DM: "ps_twitterDM",
            self.PS_INSTAGRAM: "ps_instagram",
            self.PS_WAVY: "ps_wavy",
            self.PS_TWITTER: "ps_twitter",
            self.PS_WABOX: "ps_wabox",
            self.PS_MESSENGER: "ps_messenger",
            self.PS_ONEMARKETER: "ps_onemarketer",
            self.PS_TWITTER_TWEET: "ps_twitterTweet",
            self.PS_FEED: "ps_feed",
            self.TWITTER_DM: "Twitter DM",
            self.GOOGLE_BUSINESS_MESSAGES: "Google Business Messages",
            self.MERCADO_LIBRE_RECLAMOS: "Mercado Libre Reclamos",
            self.BOTMAKER: "Botmaker",
            self.TEAMS: "Teams",
            self.TELEGRAM: "Telegram",
            self.API_CHANNEL: "ApiChannel",
            self.INSTAGRAM_DIRECT: "Instagram Direct",
            self.SINCH_SMS: "SinchSMS",
            self.DIALOG_360: "360Dialog",
            self.TWILIO: "twilio",
            self.WHATSAPP_CLOUD: "WhatsApp",
            self.GUPSHUP: "gupshup",
            self.HEY_TEST_CHANNEL: "HeyTestChannel",
            self.T2_VOICE: "T2Voice",
            self.MAILBOT: "MailBot",
            self.FLOW_SERVICE: "Flow Service",
        }
        return etiquetas.get(self, "Desconocido")

    @classmethod
    def from_int(cls, valor: int) -> str:
        try:
            return cls(valor).etiqueta()
        except ValueError:
            return "Desconocido"


class HeynowPayload:
    def __init__(self, raw: dict):
        self.raw = raw

    def extract(self) -> BaseEvent:
        event = self.raw.get("event", {})
        new_data = event.get("new", {})
        contact = new_data.get("__contact") or self.raw.get("data", {}).get(
            "__contact", {}
        )

        key = event.get("key", {})
        channel_type_name = HeynowChannelType.from_int(key.get("channel", 0))
        message = self._get_message()
        is_incoming = self._calculate_is_incoming()

        return BaseEvent(
            user_id=key.get("clientId"),
            message=message,
            user_name=f"{contact.get('first_name', channel_type_name)} {contact.get('last_name', '') or ''} ",
            channel_name=self._get_chanel_name(),
            channel=channel_type_name,
            is_incoming=is_incoming,
            metadata={
                "clientId": key.get("clientId"),
                "session": key.get("session"),
                "platformId": key.get("platformId"),
                "channel": key.get("channel"),
                "channel_type": channel_type_name,
            },
        )

    def _get_chanel_name(self) -> str:
        """
        Returns the channel name for the Heynow payload.
        """
        key = self.raw.get("event", {}).get("key", {})
        data = self.raw.get("data", {})
        new_data = self.raw.get("event", {}).get("new", {})
        contact_data = new_data.get("__contact") or self.raw.get("data", {}).get(
            "__contact", {}
        )
        if contact_data:
            return f'{contact_data.get("first_name")} {contact_data.get("last_name", "") or ""} - {HeynowChannelType.from_int(key.get("channel", 0))} '

        return f'{HeynowChannelType.from_int(key.get("channel", 0))} {data.get("contactId", "Nuevo Contacto")}'

    def _get_message(self) -> MessageEvent:
        """
        Returns the message for the Heynow payload.
        """
        data = self.raw.get("data", {})
        last_message_trace = data.get("lastMessageTrace", {})
        message = last_message_trace.get("message", "")
        meta_data = data.get("metaData", {})
        message_type = MessageEventType.TEXT
        files = None
        if meta_data.get("temporal"):
            files = self._formatter_files(meta_data.get("temporal", []))
            if files and len(files) > 0:
                mime_type = getattr(files[0], "mimetype", "text/plain")
                _logger.info(
                    "Mime type: %s", getattr(files[0], "mimetype", " no trajo")
                )

                message_type = MessageEventType.from_mime_type(mime_type)

        message_id_provider_chat = last_message_trace.get(
            "idMessageHey", self._get_custom_id()
        )
        provider_message_hey_id = last_message_trace.get(
            "idMessageHey", self._get_custom_id()
        )

        return MessageEvent(
            id=provider_message_hey_id,
            content=message,
            message_type=message_type,
            message_id_provider_chat=message_id_provider_chat,
            metadata=meta_data or {},
            files=files,
            provider_type=ProviderType.HEYNOW,
        )

    def _calculate_is_incoming(self) -> bool:
        """
        Returns the is_incoming flag for the Heynow payload.
        """
        data = self.raw.get("data", {})
        return data.get("incoming", False)

    def _formatter_files(self, files: List[Dict[str, Any]]) -> List[FileEvent]:
        """
        Returns the files for the Heynow payload.
        """
        if not files:
            return []

        return [
            FileEvent(
                name=file.get("name", ""),
                datas=file.get("data", ""),
                type="binary" if file.get("data") else "url",
                mimetype=file.get("mimeType", ""),
                description=file.get(
                    "description",
                    f'Archivo {file.get("name", "")} de HeyNow de {HeynowChannelType.from_int(file.get("channel", 0))}',
                ),
                url=file.get("urlFileshare", ""),
                file_size=file.get("size", 0),
                metadata={
                    "encode": file.get("encode", ""),
                    "channel": HeynowChannelType.from_int(file.get("channel", 0)),
                    "platform_id": file.get("platformId", 0),
                    "temporal_id": file.get("temporalId", ""),
                    "index_date": datetime.date.today(),
                },
            )
            for file in files
        ]

    def _get_custom_id(self) -> str:
        """
        Returns the custom ID for the Heynow payload.
        """

        return str(uuid4())
