from dataclasses import asdict, dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from ..provider.provider_type import ProviderType
from uuid import uuid4
from datetime import datetime
import json


class MessageEventType(Enum):
    TEXT = "text"
    HTML = "html"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    LOCATION = "location"
    CONTACT = "contact"
    STICKER = "sticker"
    VOICE_NOTE = "voice_note"
    FILE = "file"
    UNKNOWN = "unknown"

    @staticmethod
    def from_mime_type(mime_type: str) -> "MessageEventType":
        MIME_TYPE_MAP = {
            # Text
            "text/plain": MessageEventType.TEXT,
            "text/html": MessageEventType.HTML,
            # Images
            "image/jpeg": MessageEventType.IMAGE,
            "image/jpg": MessageEventType.IMAGE,
            "image/png": MessageEventType.IMAGE,
            "image/gif": MessageEventType.IMAGE,
            "image/webp": MessageEventType.IMAGE,
            "image/bmp": MessageEventType.IMAGE,
            "image/tiff": MessageEventType.IMAGE,
            "image/svg+xml": MessageEventType.IMAGE,
            # Audio
            "audio/mpeg": MessageEventType.AUDIO,
            "audio/mp3": MessageEventType.AUDIO,
            "audio/mp4": MessageEventType.AUDIO,
            "audio/x-wav": MessageEventType.AUDIO,
            "audio/wav": MessageEventType.AUDIO,
            "audio/aac": MessageEventType.AUDIO,
            "audio/ogg": MessageEventType.VOICE_NOTE,
            "audio/opus": MessageEventType.VOICE_NOTE,
            "audio/webm": MessageEventType.AUDIO,
            "audio/amr": MessageEventType.VOICE_NOTE,
            # Video
            "video/mp4": MessageEventType.VIDEO,
            "video/x-matroska": MessageEventType.VIDEO,
            "video/webm": MessageEventType.VIDEO,
            "video/ogg": MessageEventType.VIDEO,
            "video/quicktime": MessageEventType.VIDEO,
            "video/x-msvideo": MessageEventType.VIDEO,  # AVI
            "video/x-ms-wmv": MessageEventType.VIDEO,
            # Documents
            "application/pdf": MessageEventType.DOCUMENT,
            "application/msword": MessageEventType.DOCUMENT,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": MessageEventType.DOCUMENT,
            "application/vnd.ms-excel": MessageEventType.DOCUMENT,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": MessageEventType.DOCUMENT,
            "application/vnd.ms-powerpoint": MessageEventType.DOCUMENT,
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": MessageEventType.DOCUMENT,
            "application/zip": MessageEventType.DOCUMENT,
            "application/x-rar-compressed": MessageEventType.DOCUMENT,
            "application/json": MessageEventType.DOCUMENT,
            "text/csv": MessageEventType.DOCUMENT,
            "application/xml": MessageEventType.DOCUMENT,
            # Otros tipos personalizados
            "application/x-location": MessageEventType.LOCATION,
            "application/x-contact": MessageEventType.CONTACT,
            "application/x-sticker": MessageEventType.STICKER,
        }
        return MIME_TYPE_MAP.get(mime_type, MessageEventType.UNKNOWN)


@dataclass
class FileEvent:
    """Clase para representar archivos que serán convertidos a ir.attachment en Odoo 16"""

    # Campos requeridos por Odoo
    name: str = ""  # Nombre del archivo (requerido)
    datas: str = ""  # Contenido del archivo en base64 (requerido)
    type: str = "binary"
    # Campos opcionales pero recomendados
    mimetype: Optional[str] = None  # Tipo MIME del archivo

    # Campos adicionales opcionales
    description: Optional[str] = None  # Descripción del archivo
    public: bool = False  # Si el archivo es público
    access_token: Optional[str] = None  # Token de acceso
    checksum: Optional[str] = None  # Checksum del archivo
    url: Optional[str] = None  # URL original del archivo (si aplica)
    file_size: Optional[int] = None  # Tamaño del archivo en bytes
    metadata: Dict[str, Any] = field(default_factory=dict)  # Metadata adicional


@dataclass
class MessageEvent:
    id: str = field(default_factory=lambda: str(uuid4()))
    message_type: MessageEventType = MessageEventType.TEXT
    content: str = ""
    files: Optional[List[FileEvent]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    provider_type: ProviderType = ProviderType.HEYNOW
    created_at: datetime = field(default_factory=datetime.now)
    message_id_provider_chat: Optional[str] = None


@dataclass
class BaseEvent:
    user_id: str
    message: MessageEvent
    user_name: str
    channel_name: str
    channel: str  # Tipo de canal de comunicacion por el cual proviene el mensaje Whatsapp,Instagram,Messeger,etc...
    is_incoming: bool  # Indica si el mensaje es entrante o saliente cuando sea True es de entrada(de un usurio) y de debe procesar
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self):
        """Convertir a JSON string"""
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    def to_dict(self):
        """Convertir a diccionario"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        """Crear desde diccionario"""
        # Reconstruir objetos anidados
        if "message" in data and data["message"]:
            message_data = data["message"]
            files = None
            if "files" in message_data and message_data["files"]:
                files = [FileEvent(**file_data) for file_data in message_data["files"]]
            data["message"] = MessageEvent(
                content=message_data["content"],
                message_id_provider_chat=message_data.get("message_id_provider_chat"),
                files=files,
            )
        return cls(**data)

    @classmethod
    def from_json(cls, json_str):
        """Crear desde JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
