from typing import Dict, List, Type
from ..provider.provider_type import ProviderType
from .provider_service import ProviderService
from .heynow import HeyNowProviderService


class ProviderServiceFactory:
    """
    Factory para crear instancias de ProviderService según el tipo de proveedor.
    Ahora cada proveedor obtiene su propia configuración automáticamente.
    """

    _providers: Dict[ProviderType, Type[ProviderService]] = {
        ProviderType.HEYNOW: HeyNowProviderService,
    }

    @classmethod
    def create_provider(cls, env, provider_type: ProviderType) -> ProviderService:
        """
        Crear una instancia del proveedor especificado.
        La configuración se obtiene automáticamente desde la base de datos.

        :param provider_type: Tipo de proveedor a crear
        :return: Instancia del proveedor
        :raises ValueError: Si el tipo de proveedor no está soportado o no tiene configuración activa
        """
        if provider_type not in cls._providers:
            raise ValueError(f"Proveedor {provider_type.value} no está soportado")

        provider_class = cls._providers[provider_type]
        return provider_class(env, provider_type)

    @classmethod
    def register_provider(
        cls, provider_type: ProviderType, provider_class: Type[ProviderService]
    ):
        """Registrar un nuevo tipo de proveedor."""
        cls._providers[provider_type] = provider_class

    @classmethod
    def get_supported_providers(cls) -> List[ProviderType]:
        """Obtener lista de proveedores soportados."""
        return list(cls._providers.keys())
