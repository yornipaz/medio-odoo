from abc import ABC, abstractmethod
from typing import Dict, Any


class Provider(ABC):
    """
    Abstract base class for all providers.
    """

    @abstractmethod
    def get_url(self, config=None) -> str:
        """
        Get the URL for the provider's API.

        :param url_base: Base URL from system configuration
        :param config: Additional configuration data
        :return: Complete URL as string
        """
        pass

    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        """
        Get the headers required for API requests.

        :return: Dictionary of headers
        """
        pass

    @abstractmethod
    def get_payload(
        self, message: Dict[str, Any], config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Get the payload to be sent to the provider.

        :param message: Odoo message object
        :param channel: Odoo channel object
        :param config: Configuration metadata from channel
        :return: Dictionary representing the payload
        """
        pass
