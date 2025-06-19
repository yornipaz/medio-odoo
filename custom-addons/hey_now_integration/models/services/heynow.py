from ..provider.provider_type import ProviderType
from .provider_service import ProviderService


class HeyNowProviderService(ProviderService):
    """Implementación específica para el proveedor HeyNow."""

    def __init__(self, env, provider_type: ProviderType = ProviderType.HEYNOW):
        self.env = env
        super().__init__(env, provider_type)

    def get_auth_token(self) -> str:
        return self.config.auth_token if self.config is not None else ""

    def get_base_url(self) -> str:
        return self.config.base_url if self.config is not None else ""

    def get_is_valid(self) -> bool:
        return bool(
            self.config is not None
            and self.config.auth_token
            and self.config.base_url
            and self.config.is_active
        )

    def get_is_valid_channel(self, channel_name) -> bool:
        if self.config is None or not hasattr(self.config, "allowed_channel_ids"):
            return False
        allowed_channel_name = [
            str(ch.get("name", "")) for ch in self.config.allowed_channel_ids
        ]
        return str(channel_name) in allowed_channel_name
