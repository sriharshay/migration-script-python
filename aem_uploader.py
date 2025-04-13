"""
AEM Image Processor Module

Handles image processing and upload to AEM DAM with folder structure management
"""

import os
import time
import requests
import logging
from typing import Tuple
from urllib.parse import urlparse
from config_loader import ConfigLoader
from requests.auth import HTTPBasicAuth       

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AEMUploader:
    """
    Handles AEM DAM operations including folder creation and asset upload
    
    Attributes:
        base_url (str): AEM API base URL
        headers (dict): Headers from config
        retries (int): Number of retry attempts
        retry_delay (int): Delay between retries in seconds
    """
    
    def __init__(self):
        self.aem_config = ConfigLoader().get('aem', {})
        self.base_url = self.aem_config.get('base_url', 'http://localhost:4502')
        self.headers = {
            'Cookie': 'cq-authoring-mode=TOUCH'
        }
        self.retries = self.aem_config.get('retries', 3)
        self.timeout = self.aem_config.get('timeout', 15)
        self.retry_delay = self.aem_config.get('retry_delay', 5)

    def create_folder(self, folder_path: str) -> bool:
        """
        Create folder structure in AEM DAM recursively
        
        Args:
            folder_path: Full DAM path (e.g. '/content/dam/project/set1')
            
        Returns:
            bool: True if folder creation succeeded
        """
        folders = folder_path.strip('/').split('/')[2:]  # Skip /content/dam
        current_path = '/content/dam'
        
        for folder in folders:
            current_path = f"{current_path}/{folder}"
            api_path = current_path.replace('/content/dam', '/api/assets', 1)
            check_url = f"{self.base_url}{api_path}.json"
            
            # Check if folder exists
            response = self._retry_request('GET', check_url)
            if response.status_code == 200:
                continue
                
            # Create folder if missing
            create_url = f"{self.base_url}{api_path.rsplit('.json',1)[0]}"
            payload = {
                "class": "assetFolder",
                "properties": {"jcr:title": folder.title()}
            }
            response = self._retry_request(
                'POST', create_url,
                headers={'Content-Type': 'application/json', **self.headers},
                json=payload
            )
            
            if response.status_code != 201:
                logger.error(f"Failed creating folder {current_path}: {response.text}")
                return False
                
        return True

    def upload_asset(self, file_path: str, file_data: bytes, content_type: str) -> Tuple[bool, str]:
        """
        Upload asset to AEM DAM
        
        Args:
            file_path: Target DAM path (e.g. '/content/dam/project/image.jpg')
            file_data: Binary file content
            content_type: MIME type of the asset
            
        Returns:
            Tuple: (success status, new DAM path or error message)
        """
        try:
            # Create parent folders first
            parent_folder = os.path.dirname(file_path)
            if not self.create_folder(parent_folder):
                return False, "Folder creation failed"
                
            api_path = file_path.replace('/content/dam', '/api/assets', 1)
            upload_url = f"{self.base_url}{api_path}"
            
            headers = {
                'Content-Type': content_type,
                'Content-Transfer-Encoding': content_type,
                **self.headers
            }
            
            response = self._retry_request(
                'POST', upload_url,
                headers=headers,
                data=file_data
            )
            
            if response.status_code == 201:
                return True, file_path
            logger.error(f"Upload failed: {response.status_code} - {response.text}")
            return False, response.text
        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            return False, str(e)

    def _retry_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Retry wrapper for HTTP requests"""
        for attempt in range(self.retries + 1):
            response = requests.request(method, url, auth=HTTPBasicAuth(self.aem_config['username'], self.aem_config['password']), **kwargs)
            if response.status_code < 500:
                return response
            logger.warning(f"Retry {attempt+1}/{self.retries} for {url}")
            time.sleep(self.retry_delay)
        return response
