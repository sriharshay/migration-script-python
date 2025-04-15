# README
1. Install python packages
    ```
    pip install requests pandas openpyxl pyyaml bs4
    ```
2. Update the [config.yaml](config.yaml), if needed update the [config_loader.py](config_loader.py)
    ## Usage in Other Modules:
    ```
    from config_loader import ConfigLoader

    ### Get singleton instance
    cfg = ConfigLoader()

    # Access configuration
    excel_columns = cfg.excel.get('columns', [])
    ms_endpoint = cfg.ms.get('endpoint')

    # Get nested configuration
    aem_timeout = cfg.get('aem.connection.timeout', 30)

    # Force reload if needed
    cfg.reload_config()
    ```
3. Start the import process 
    ```
    python init_import.py 
    ```
4. Import process can be limited to only few excel entries with by updating the for loop 
   ```data``` to ```data[:5]``` in [init_import.py](init_import.py)
5. Excel file data is processed in [excel_data.py](excel_data.py)
6. If there is any issue in conncting to the microservice endpoint, troubleshoot [response_from_ms.py](response_from_ms.py) module.
7. Respense from the micro service endpoint is validated in [process_ms_response.py](process_ms_response.py) module.
8. Validated miscro service endpoint response is fed to AEM [aem_connector.py](aem_connector.py) module.

----------
## TODO
1. ~~Identify the component type based on elements available~~
2. Extract the component data from html markup and create a component json - AEM import ready JSON (component compatible strucuture)
3. ~~Identify image and check how to leverage python to upload the image in dam~~
4. ~~Update the image URL and other attributes so that it will reflect the image component - AEM import ready JSON (component compatible strucuture)~~
Parse the HTML, identify components, customize the components, add default properties (static), remove unncessary attributes, improved logging in an application logger  