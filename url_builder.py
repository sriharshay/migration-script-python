import re
import yaml
import time
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class URLBuilder:
    def __init__(self, url_template, excel_row):
        #self.url_template = self.config['api']['ms_endpoint']
        self.url_template = url_template
        self.placeholders = self._extract_placeholders()
        self.excel_row = excel_row

    def _load_config(self, path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def _extract_placeholders(self):
        return re.findall(r'<([^>]+)>', self.url_template)

    def _validate_config(self):
        if 'excel' not in self.config:
            raise ValueError("Missing 'excel' section in config")
        if 'api' not in self.config or 'ms_endpoint' not in self.config['api']:
            raise ValueError("Missing 'api.ms_endpoint' in config")
        
        placeholders = self._extract_placeholders()
        excel_columns = self.config['excel'].get('columns', [])
        missing = [ph for ph in placeholders if ph not in excel_columns]
        if missing:
            raise ValueError(f"URL placeholders {missing} missing from Excel columns in config")

    def build_url(self):
        """Generate URLs with values from Excel data"""
        excel_row = self.excel_row
        url = self.url_template
        for ph in self.placeholders:
            value = excel_row[ph]
            if pd.isna(value):
                raise ValueError(f"Missing value for '{ph}'")
            url = url.replace(f'<{ph}>', str(value))
        
        return f"{url}&_{time.time_ns() * excel_row['ID']}" 