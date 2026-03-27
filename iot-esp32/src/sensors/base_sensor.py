import time
from models.sensor_data import SensorData

class BaseSensor:
    def __init__(self, name, pin=None, **kwargs):
        self.name = name
        self.pin = pin
        self.codes = kwargs.get('codes', {})  # Mapping of metric to code (e.g., {"temperature": "TA"})
        self.index = kwargs.get('index', 1)  # Sensor index for compact format (e.g., "1TA")
        self._last_reading = None
        self._last_read_time = 0
        self._read_interval = kwargs.get('read_interval', 2)
        self._error_count = 0
        self._max_errors = kwargs.get('max_errors', 5)
        self._hardware_available = True

    def init_hardware(self):
        """Check hardware availability. Call after subclass __init__."""
        try:
            self._hardware_available = self._check_hardware()
        except Exception as e:
            self._hardware_available = False
            print(f"  [{self.name}] Hardware check failed: {e}")
        
        if not self._hardware_available:
            print(f"  [{self.name}] Hardware NOT detected - sensor disabled")
        else:
            print(f"  [{self.name}] Hardware OK")

    def _check_hardware(self):
        """Override in subclass to verify hardware is connected.
        Returns True if hardware is detected, False otherwise."""
        return True

    def read(self, force=False):
        """Template Method : ne pas surcharger"""
        if not self._hardware_available:
            return None
        
        if not force and not self._should_read():
            return self._last_reading
        
        try:
            raw_data = self._read_raw()
        except Exception as e:
            self._error_count += 1
            print(f"  [{self.name}] Read error ({self._error_count}x): {e}")
            return self._last_reading

        if raw_data is None:
            self._error_count += 1
            print(f"  [{self.name}] No data returned ({self._error_count}x)")
            return self._last_reading

        if not self._validate(raw_data):
            self._error_count += 1
            print(f"  [{self.name}] Invalid data ({self._error_count}x): {raw_data}")
            return self._last_reading

        # Create DTO with sensor data
        dto = self._create_dto(raw_data)
        
        self._error_count = 0
        self._last_reading = dto
        self._last_read_time = time.time()
        return dto

    def _read_raw(self):
        raise NotImplementedError

    def _validate(self, data):
        raise NotImplementedError

    def _create_dto(self, raw_data):
        """Create SensorData DTO from raw data."""
        dto = SensorData(self.name, self.__class__.__name__, codes=self.codes, index=self.index)
        
        for metric, value in raw_data.items():
            # Try to determine unit based on metric name
            unit = self._get_unit_for_metric(metric)
            dto.add_reading(metric, value, unit)
        
        return dto

    def _get_unit_for_metric(self, metric):
        """Determine unit based on metric name."""
        units = {
            # 'temperature': '°C',
            'temperature': 'C',
            'humidity': '%',
            'luminance': 'lux',
            'luminosity': 'lux',
            'soil_moisture': '%',
            'pressure': 'hPa'
        }
        return units.get(metric, '')

    def _should_read(self):
        # TODO : use rtc timestamp if available
        return (time.time() - self._last_read_time) >= self._read_interval

    def is_healthy(self):
        """Check if sensor is functioning properly."""
        return self._error_count < self._max_errors