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
        self.aem = ConfigLoader().get('aem', {})
        self.base_url = self.aem.get('base_url', 'http://localhost:4502')
        self.headers = {
            'Cookie': 'cq-authoring-mode=TOUCH'
        }

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
        auth = HTTPBasicAuth(self.aem['username'], self.aem['password'])
        retries = self.aem.get('retries', 3)
        timeout = self.aem.get('timeout', 15)
        retry_delay = self.aem.get('retry_delay', 5)
        for attempt in range(retries + 1):
            try:
                response = requests.request(method, url, timeout=timeout, auth=auth, **kwargs)
                if response.status_code in (200, 201):
                    return response
            except requests.exceptions.RequestException as e:
                logger.warning(f"Retry {attempt+1}/{retries} for {url}: error {str(e)}")
                time.sleep(retry_delay)
        return response
