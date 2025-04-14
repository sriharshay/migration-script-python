import requests
import json
import logging
from typing import Union, Dict, Any
from time import time
from requests.auth import HTTPBasicAuth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AEMConnector:
    """
    Handles API requests with timeout and error handling
    
    Parameters:
    - endpoint_url (str): API endpoint from config.yaml (api.aem_endpoint)
    - payload (Union[list, dict]): JSON data to send
    - timeout (int): Timeout in seconds (default: 10)
    """
    
    def __init__(self, endpoint_url: str, username: str, password: str, payload: Union[list, dict], timeout: int = 10):
        if not isinstance(endpoint_url, str) or not endpoint_url.startswith(('http://', 'https://')):
            raise ValueError("Invalid endpoint URL format")
            
        if not isinstance(payload, (list, dict)):
            raise TypeError("Payload must be a string")
            
        self.endpoint = endpoint_url
        self.username = username
        self.password = password
        self.payload = payload
        self.timeout = timeout
        self.response_template = {
            "statusCode": 500,
            "result": {},
            "duration": 0.0
        }

    def connect(self) -> Dict[str, Any]:
        """Execute POST request with payload"""
        start_time = time()
        # print("payload before POST request", self.payload)
        try:
            response = requests.post(
                self.endpoint,
                auth=HTTPBasicAuth(self.username, self.password),
                json=self.payload,
                timeout=self.timeout,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            )
            # print("Request headers:", response.request.headers)
            # print("Sent body:", response.request.body)
            # Should show valid JSON with double quotes
            return self._handle_success(response, start_time)
            
        except requests.exceptions.Timeout:
            return self._handle_error(504, "Request timed out", start_time)
            
        except requests.exceptions.RequestException as e:
            return self._handle_error(500, str(e), start_time)
            
        except Exception as e:
            return self._handle_error(500, f"Unexpected error: {str(e)}", start_time)

    def _handle_success(self, response: requests.Response, start: float) -> Dict[str, Any]:
        """Process successful response"""
        result = self.response_template.copy()
        result["statusCode"] = response.status_code
        result["duration"] = round(time() - start, 2)
        
        try:
            result["result"] = response.json()
        except json.JSONDecodeError:
            result["result"] = {
                "raw_response": response.text[:500],
                "error": "Invalid JSON format"
            }
            
        return result

    def _handle_error(self, code: int, message: str, start: float) -> Dict[str, Any]:
        """Handle errors and timeouts"""
        result = self.response_template.copy()
        result["statusCode"] = code
        result["result"] = {
            "error": message,
            "endpoint": self.endpoint
        }
        result["duration"] = round(time() - start, 2)
        return result