from .provider import Provider
from .heynow import HeynowProvider
from .provider_type import ProviderType


class ProviderDispatcher:
    def __init__(self, provider_name: str, env):
        self.provider_name = provider_name
        self.env = env

    def get_provider(self) -> Provider:

        if self.provider_name == ProviderType.HEYNOW.value:
            return HeynowProvider(self.env)
        else:
            raise ValueError(f"Unsupported provider: {self.provider_name}")
