"""
Config Manager - Singleton Pattern
Centralized configuration management
"""

import json


class ConfigManager:
    """
    Singleton for centralized configuration management.
    Ensures only one instance exists throughout the program.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls):
        """Get the singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._config = {}
        self._initialized = True

    def load(self, config_path='config/config.json'):
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                self._config = json.load(f)
            print(f"[ConfigManager] ✓ Configuration loaded from {config_path}")
        except Exception as e:
            print(f"[ConfigManager] ✗ Error loading config: {e}")
            self._config = {}

    def get(self, key_path, default=None):
        """
        Access configuration value using dot notation.
        
        Args:
            key_path: dot-separated path (e.g., 'device.uid' or 'lora.frequency')
            default: default value if key not found
            
        Returns:
            configuration value or default
            
        Example:
            config.get('device.uid')
            config.get('lora.pins.sck', 18)
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default

    def get_config(self):
        """Return complete configuration"""
        return self._config
    
    def set(self, key_path, value):
        """
        Set configuration value using dot notation.
        
        Args:
            key_path: dot-separated path (e.g., 'device.uid')
            value: value to set
        """
        keys = key_path.split('.')
        config = self._config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def save(self, config_path='config/config.json'):
        """Save configuration to JSON file"""
        try:
            with open(config_path, 'w') as f:
                json.dump(self._config, f, indent=2)
            print(f"[ConfigManager] ✓ Configuration saved to {config_path}")
        except Exception as e:
            print(f"[ConfigManager] ✗ Error saving config: {e}")