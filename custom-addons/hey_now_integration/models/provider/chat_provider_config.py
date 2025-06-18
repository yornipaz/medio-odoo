from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class ChatProviderConfig:
    id: int
    name: str
    provider_type: str
    is_active: bool
    base_url: str
    allowed_channel_ids: List[Dict[str, Any]]  # Campo obligatorio
    auth_token: str = ""  # Campo con valor por defecto
    config_extra: Optional[Dict[str, Any]] = None  # Opcional
