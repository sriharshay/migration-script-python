import requests
import json
import time
import logging
from typing import Dict, Any
from config_loader import ConfigLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResponseFromMS:
    """Class to handle HTTP requests and response processing"""
    
    def __init__(self, url: str, timeout: int = 10, headers: Dict[str, str] = None, 
                 retries: int = 3):
        """
        Initialize the URL fetcher
        
        :param url: Target URL to fetch
        :param timeout: Request timeout in seconds (default: 10)
        :param headers: Optional request headers
        :param auth: Optional authentication tuple (username, password)
        :param retries: Number of retry attempts for failed requests (default: 3)
        """
        self.ms = ConfigLoader().ms
        self.url = url
        self.timeout = timeout
        self.headers = headers or {}
        self.retries = retries
        self.result = {
            'statusCode': 500,
            'result': {}
        }

    def execute(self) -> Dict[str, Any]:
        """Execute the request and process response"""
        retries = self.ms.get('retries', 3)
        timeout = self.ms.get('timeout', 15)
        retry_delay = self.ms.get('retry_delay', 3)
        for attempt in range(retries + 1):
            try:
                response = requests.request('GET', url=self.url, timeout=timeout)
                return self._process_response(response)
            except requests.exceptions.RequestException as e:
                if attempt == retries:
                    return self._handle_error(e)
                logger.warning(f"Retry {attempt+1}/{retries} for {self.url}: error {str(e)}")
                time.sleep(retry_delay)
        return self.result

    def _process_response(self, response: requests.Response) -> Dict[str, Any]:
        """Process successful response"""
        self.result['statusCode'] = response.status_code
        
        try:
            self.result['result'] = response.json()
        except json.JSONDecodeError:
            self.result['result'] = {
                'error': 'Invalid JSON response',
                'content': response.text[:500]  # Limit content size
            }
        
        return self.result

    def _handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle request errors"""
        self.result['result'] = {
            'errorType': error.__class__.__name__,
            'message': str(error),
            'url': self.url
        }
        return self.result

    @property
    def status_code(self) -> int:
        """Get last status code received"""
        return self.result['statusCode']

    @property
    def response_data(self) -> Any:
        """Get last response data received"""
        return self.result['result']