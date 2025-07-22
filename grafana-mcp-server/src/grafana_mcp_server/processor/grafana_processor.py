import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class Processor:
    """Base processor interface"""
    def get_connection(self):
        pass

    def test_connection(self):
        pass


class GrafanaApiProcessor(Processor):
    """
    Grafana API processor for handling Grafana API interactions.
    Uses API key authentication.
    """
    
    def __init__(self, grafana_host, grafana_api_key, ssl_verify='true'):
        """
        Initialize Grafana API processor.
        
        Args:
            grafana_host: Grafana instance URL (e.g., https://grafana.example.com)
            grafana_api_key: API key for authentication
            ssl_verify: Whether to verify SSL certificates ("true" or "false")
        """
        self.__host = grafana_host.rstrip('/')  # Remove trailing slash
        self.__api_key = grafana_api_key
        self.__ssl_verify = False if ssl_verify and ssl_verify.lower() == 'false' else True
        self.headers = {
            'Authorization': f'Bearer {self.__api_key}'
        }
        
        logger.info(f"Initialized Grafana processor with host: {self.__host}")

    def get_connection(self):
        """Return connection details for debugging"""
        return {
            "host": self.__host,
            "ssl_verify": self.__ssl_verify,
            "auth_method": "api_key",
            "headers": {k: v for k, v in self.headers.items() if k != "Authorization"}
        }

    def test_connection(self):
        """
        Test connection to Grafana API to verify configuration and connectivity.
        Uses the /api/datasources endpoint to verify API access.
        
        Returns:
            bool: True if connection successful
            
        Raises:
            Exception: If connection fails with details about the failure
        """
        try:
            url = '{}/api/datasources'.format(self.__host)
            logger.info(f"Testing Grafana connection to: {url}")
            
            response = requests.get(url, headers=self.headers, verify=self.__ssl_verify, timeout=20)
            if response and response.status_code == 200:
                logger.info("Successfully connected to Grafana API")
                return True
            else:
                status_code = response.status_code if response else None
                raise Exception(
                    f"Failed to connect with Grafana. Status Code: {status_code}. Response Text: {response.text}")
        except Exception as e:
            logger.error(f"Exception occurred while fetching grafana data sources with error: {e}")
            raise e