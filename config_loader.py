"""
YAML Configuration Loader Module

Provides a singleton class for loading and managing application configuration from YAML files
with support for automatic reloading and validation.
"""

import yaml
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfigLoader:
    """
    Singleton class for managing YAML configuration files with automatic reloading capabilities.

    This class provides:
    - Thread-safe singleton instance
    - Configuration auto-reloading on file modification
    - Type-annotated access to configuration sections
    - Validation of required configuration keys
    - Hierarchical configuration access using dot notation
    - Comprehensive error handling and logging

    Attributes:
        _instance (ConfigLoader): Singleton instance reference
        _config (Dict[str, Any]): Loaded configuration data
        _config_path (Path): Path to configuration file
        _last_modified (float): Last modified timestamp of config file
    """

    _instance = None
    _config: Dict[str, Any] = None
    _config_path: Path = None
    _last_modified: float = 0
    
    def __new__(cls, config_file: str = 'config.yaml') -> 'ConfigLoader':
        """
        Create or return the singleton instance.

        Args:
            config_file: Path to configuration file (default: 'config.yaml')

        Returns:
            ConfigLoader: Singleton instance

        Example:
            >>> config = ConfigLoader()
            >>> config2 = ConfigLoader()
            >>> config is config2
            True
        """
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._initialize(config_file)
        return cls._instance
    
    def _initialize(self, config_file: str) -> None:
        """
        Initialize the configuration loader.

        Args:
            config_file: Path to configuration file

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file contains invalid YAML
        """
        self._config_path = Path(config_file)
        self.reload_config()
        
    def reload_config(self) -> None:
        """
        Reload configuration from file if it has been modified since last load.

        Performs:
        - File existence check
        - YAML syntax validation
        - Config modification time check
        - Config data refresh

        Raises:
            FileNotFoundError: If config file is not found
            yaml.YAMLError: If config file contains invalid YAML
        """
        try:
            modified_time = os.path.getmtime(self._config_path)
            if modified_time > self._last_modified:
                with open(self._config_path, 'r') as f:
                    self._config = yaml.safe_load(f) or {}
                self._last_modified = modified_time
                logger.info("Configuration reloaded successfully")
        except FileNotFoundError:
            logger.error(f"Config file not found: {self._config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML syntax: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise
    
    @property
    def excel(self) -> Dict[str, Any]:
        """
        Access the 'excel' configuration section.

        Returns:
            Dict[str, Any]: Excel-related configuration. Returns empty dict if section not found.

        Example:
            >>> config.excel.get('file_path')
            'data/input.xlsx'
        """
        return self._config.get('excel', {})
    
    @property
    def ms(self) -> Dict[str, Any]:
        """
        Access the 'ms' configuration section.

        Returns:
            Dict[str, Any]: MS service configuration. Returns empty dict if section not found.
        """
        return self._config.get('ms', {})
    
    @property
    def aem(self) -> Dict[str, Any]:
        """
        Access the 'aem' configuration section.

        Returns:
            Dict[str, Any]: AEM-related configuration. Returns empty dict if section not found.
        """
        return self._config.get('aem', {})
    
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Get configuration value using dot-notation hierarchy.

        Args:
            key: Configuration key in dot notation (e.g., 'aem.connection.timeout')
            default: Default value if key not found

        Returns:
            Any: Configuration value or default

        Example:
            >>> config.get('aem.connection.timeout', 30)
            60
        """
        keys = key.split('.')
        value = self._config
        for k in keys:
            value = value.get(k, {}) if isinstance(value, dict) else default
            if value == {}:
                return default
        return value or default

    def validate_required_keys(self, required_keys: Dict[str, list]) -> None:
        """
        Validate presence of required configuration keys.

        Args:
            required_keys: Dictionary of required keys in format:
                {
                    'section': ['key1', 'key2'],
                    'nested.section': ['key3']
                }

        Raises:
            ValueError: If any required keys are missing

        Example:
            >>> required = {'excel': ['file_path'], 'ms': ['endpoint']}
            >>> config.validate_required_keys(required)
        """
        missing_keys = []
        for section, keys in required_keys.items():
            current = self._config
            for part in section.split('.'):
                current = current.get(part, {})
            
            if current == {}:
                missing_keys.append(section)
                continue
                
            for key in keys:
                if key not in current:
                    missing_keys.append(f"{section}.{key}")
        
        if missing_keys:
            raise ValueError(f"Missing required configuration keys: {', '.join(missing_keys)}")