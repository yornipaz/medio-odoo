from enum import Enum


class ProviderType(Enum):
    """
    Enum representa los diferentes tipos de proveedores de servicios de mensajería.
    """

    BOTPRESS = "botpress"
    HEYNOW = "heynow"
    TWILIO = "twilio"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    FACEBOOK = "facebook"
    SLACK = "slack"
    DISCORD = "discord"
