import logging
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExcelDataHandler:
    def __init__(self, file_path, columns):
        self.file_path = file_path
        self.columns = columns

    def read_data(self):
        """Read Excel file and return data as list of dictionaries"""
        try:
            df = pd.read_excel(self.file_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Excel file not found at {self.file_path}")
        
        # Validate columns exist in DataFrame
        missing_columns = [col for col in self.columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing columns in Excel file: {missing_columns}")
        
        return df[self.columns].to_dict(orient='records')