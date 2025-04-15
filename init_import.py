import datetime
import logging
import pandas as pd
from time import time
from config_loader import ConfigLoader
from excel_data import ExcelDataHandler
from url_builder import URLBuilder
from response_from_ms import ResponseFromMS
from process_ms_response import MSResponseHandler
from aem_connector import AEMConnector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_data(data, columns):
    if not data:
        raise ValueError("No data found in Excel file")
    
    for idx, row in enumerate(data, 1):
        for col in columns:
            if col not in row:
                raise ValueError(f"Row {idx} missing column '{col}'")
            if pd.isna(row[col]):
                print(f"Warning: Missing value in row {idx}, column '{col}'")

def main():
    start_time = time()
    config = ConfigLoader()
    excel_file_path = config.excel.get('file_path')
    excel_columns = config.excel.get('columns')
    try:
        # Excel Data Validation
        handler = ExcelDataHandler(
            file_path=excel_file_path,
            columns=excel_columns
        )
        data = handler.read_data()
        validate_data(data, excel_columns)
        print("\n✅ Excel data validation successful!")
        print(f"   Found {len(data)} rows")
        data = data[:4]
        records = len(data[:4])
        print(f"   Process only {records} rows")
        # print(f"   First row sample: {data[:5]}")
    except Exception as e:
        raise SystemExit(f"\n❌ ExcelDataHandler failed: {str(e)}")
    
    # URL Generation Validation
    # print(f"Endpoint template {config.ms.get('endpoint')}")
    for idx, excel_row in enumerate(data):
        try:
            builder = URLBuilder(
                url_template=config.ms.get('endpoint'),
                excel_row=excel_row
            )
            url = builder.build_url()
            print(f"\nProcessing {idx + 1}/{records} page")
            print(f"URL: {url}")
            try:
                response = ResponseFromMS(
                    url=url,
                    timeout=config.ms.get('timeout'),
                    retries=config.ms.get('retries'),
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                ).execute()
                # print(f"Response: {response}")
                handler = MSResponseHandler(response)
                processed_response = handler.get_processed_json()
                # print(f"processed response {processed_response}")
                try:
                    aem_repsonse = AEMConnector(
                        endpoint_url=config.aem.get('endpoint'),
                        username=config.aem.get('username'),
                        password=config.aem.get('password'),
                        payload=processed_response
                    ).connect()
                    print(f"AEM response {aem_repsonse}")
                except Exception as e:
                    print(f"\n❌ CreatePageHandler failed: {str(e)}")
                    pass
            except Exception as e:
                print(f"\n❌ ResponseFromMS failed: {str(e)}")
                pass
        except Exception as e:
            print(f"\n❌ URLBuilder failed: {str(e)}")
            pass
    elapsed_time_seconds = time() - start_time
    elapsed_time_ms = int(elapsed_time_seconds * 1000)
    time_delta = datetime.timedelta(milliseconds=elapsed_time_ms)
    hours, remainder = divmod(time_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = time_delta.microseconds // 1000
    print(f"\n⌛ Import duration: {hours}h {minutes}m {seconds}s {milliseconds}ms")
    
if __name__ == "__main__":
    main()