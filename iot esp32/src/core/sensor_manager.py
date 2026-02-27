"""
Sensor Manager - Manages all sensors and their readings.
Publishes sensor events to EventBus (Observer Pattern).
"""

from sensors.sensor_factory import SensorFactory


class SensorManager:
    """
    Manages sensor lifecycle and data collection.
    Uses Factory Pattern for sensor creation.
    Publishes events via Observer Pattern.
    """
    
    def __init__(self, config, hardware_manager, event_bus):
        """
        Initialize sensor manager.
        
        Args:
            config: ConfigManager instance
            hardware_manager: HardwareManager instance (for I2C access)
            event_bus: EventBus instance (for publishing events)
        """
        self.config = config
        self.hardware = hardware_manager
        self.event_bus = event_bus
        self.sensors = {}
        
        # Register available sensor types
        self._register_sensor_types()
    
    def _register_sensor_types(self):
        """Register all available sensor types in the Factory"""
        from sensors.dth22_sensor import DHT22Sensor
        from sensors.ds18b20 import DS18B20Sensor
        from sensors.bh1750_sensor import BH1750Sensor
        from sensors.lm393_sensor import LM393Sensor
        
        SensorFactory.register("dht22", DHT22Sensor)
        SensorFactory.register("ds18b20", DS18B20Sensor)
        SensorFactory.register("bh1750", BH1750Sensor)
        SensorFactory.register("lm393", LM393Sensor)
        
        print("[SensorManager] Sensor types registered")
    
    def initialize_sensors(self):
        """Initialize all enabled sensors from config"""
        sensors_config = self.config.get('sensors', [])
        
        for sensor_cfg in sensors_config:
            if not sensor_cfg.get('enabled', False):
                continue
            
            try:
                # Prepare parameters for sensor
                params = {
                    'name': sensor_cfg['name'],
                    'pin': sensor_cfg.get('pin'),
                    'i2c': self.hardware.i2c,  # Pass I2C bus if available
                }
                
                # Add custom params from config
                if 'params' in sensor_cfg:
                    params.update(sensor_cfg['params'])
                
                # Create sensor via Factory
                sensor = SensorFactory.create(sensor_cfg['type'], **params)
                self.sensors[sensor_cfg['name']] = sensor
                
                print(f"[SensorManager] ✓ Sensor '{sensor_cfg['name']}' ({sensor_cfg['type']}) initialized")
            
            except Exception as e:
                print(f"[SensorManager] ✗ Failed to init sensor '{sensor_cfg['name']}': {e}")
                
                # Publish error event
                self.event_bus.publish('sensor.init_error', {
                    'sensor': sensor_cfg['name'],
                    'error': str(e)
                })
        
        print(f"[SensorManager] ✓ {len(self.sensors)} sensors ready")
    
    def read_all_sensors(self):
        """
        Read all sensors and publish events.
        
        Returns:
            dict: {sensor_name: sensor_data}
        """
        results = {}
        
        for name, sensor in self.sensors.items():
            try:
                dto = sensor.read()
                
                if dto and dto.is_valid:
                    results[name] = dto.to_dict()
                    
                    # Publish sensor data event (Observer Pattern)
                    self.event_bus.publish('sensor.data', {
                        'sensor': name,
                        'data': dto.to_dict()
                    })
                
            except Exception as e:
                print(f"[SensorManager] Error reading {name}: {e}")
                
                # Publish error event
                self.event_bus.publish('sensor.read_error', {
                    'sensor': name,
                    'error': str(e)
                })
        
        return results
    
    def read_sensor(self, sensor_name):
        """
        Read a specific sensor by name.
        
        Args:
            sensor_name: name of the sensor
            
        Returns:
            dict or None: sensor data
        """
        sensor = self.sensors.get(sensor_name)
        
        if not sensor:
            print(f"[SensorManager] Sensor '{sensor_name}' not found")
            return None
        
        try:
            data = sensor.read()
            
            if data:
                self.event_bus.publish('sensor.data', {
                    'sensor': sensor_name,
                    'data': data
                })
            
            return data
        
        except Exception as e:
            print(f"[SensorManager] Error reading {sensor_name}: {e}")
            
            self.event_bus.publish('sensor.read_error', {
                'sensor': sensor_name,
                'error': str(e)
            })
            
            return None
    
    def get_sensor(self, sensor_name):
        """Get sensor instance by name"""
        return self.sensors.get(sensor_name)
    
    def get_all_sensors(self):
        """Get all sensor instances"""
        return self.sensors
