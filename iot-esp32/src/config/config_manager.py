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

    def load(self, config_path='/src/config/config.json'):
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                self._config = json.load(f)
            print(f"[ConfigManager] Configuration loaded from {config_path}")
        except Exception as e:
            print(f"[ConfigManager] Error loading config: {e}")
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
            key_path: dot-separated path (e.g., 'device.uid' or 'sensors.0.alerts.temp')
            value: value to set
        """
        keys = key_path.split('.')
        config = self._config
        
        for i, key in enumerate(keys[:-1]):
            # Check if current key is a numeric index for array access
            if key.isdigit():
                # Convert to integer for array indexing
                index = int(key)
                # Ensure the parent is a list and has enough elements
                if isinstance(config, list):
                    # Extend list if needed with empty dicts
                    while len(config) <= index:
                        config.append({})
                else:
                    # Convert dict to list if we're trying to use numeric index
                    config = [config] if config else []
                    while len(config) <= index:
                        config.append({})
                config = config[index]
            else:
                # Regular dictionary key
                if key not in config:
                    config[key] = {}
                config = config[key]
        
        # Handle the last key
        last_key = keys[-1]
        if last_key.isdigit():
            # Numeric index for array
            index = int(last_key)
            if isinstance(config, list):
                while len(config) <= index:
                    config.append({})
                config[index] = value
            else:
                # Convert to list if needed
                config = [config] if config else []
                while len(config) <= index:
                    config.append({})
                config[index] = value
        else:
            # Regular dictionary key
            config[last_key] = value
    
    def save(self, config_path='/src/config/config.json', read_after_save=False):
        """Save configuration to JSON file"""
        try:
            with open(config_path, 'w') as f:
                json.dump(self._config, f)
            print(f"[ConfigManager] Configuration saved to {config_path}")
            # Lire et afficher le contenu du fichier config.json
            if read_after_save:
                with open('/src/config/config.json', 'r') as f:
                    config_content = f.read()
                    print("Contenu du fichier config.json :")
                    print(config_content)
        except Exception as e:
            print(f"[ConfigManager] Error saving config: {e}")

    def get_sensor_identifier(self, sensor_name):
        """
        Get sensor identifier for a specific sensor.

        Args:
            sensor_name: name of the sensor

        Returns:
            dict: codes mapping (e.g., {'temperature': 'TA', 'humidity': 'HA'})

        Raises:
            ValueError: if sensor is enabled but has no codes
        """
        sensors = self.get('sensors', [])

        for sensor in sensors:
            if sensor.get('name') == sensor_name:
                codes = sensor.get('codes', {})
                index = sensor.get('index', 1)

                if sensor.get('enabled', False) and not codes:
                    raise ValueError(
                        f"Sensor '{sensor_name}' is enabled but has no codes defined"
                    )

                return codes, index

        raise ValueError(f"Sensor '{sensor_name}' not found in configuration")