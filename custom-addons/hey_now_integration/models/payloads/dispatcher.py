from .heynow import HeynowPayload

# Aquí puedes importar futuros proveedores como:
# from .botpress import BotpressPayload
from .base_event import BaseEvent


class WebhookDispatcher:
    def __init__(self, provider_name: str, raw_payload: dict):
        self.provider_name = provider_name
        self.raw_payload = raw_payload

    def extract_event(self) -> BaseEvent:
        if self.provider_name == "heynow":
            return HeynowPayload(self.raw_payload).extract()
        # elif self.provider_name == "botpress":
        #     return BotpressPayload(self.raw_payload).extract()
        else:
            raise ValueError(f"Unsupported provider: {self.provider_name}")
