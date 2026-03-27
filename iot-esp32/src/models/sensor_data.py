"""
Sensor Data DTO - Data Transfer Object Pattern
Standardized format for sensor data across the entire system.
"""

import time


class SensorReading:
    """Represents a single sensor reading with code, value, and unit."""
    
    def __init__(self, code, value, unit=""):
        self.code = code      # "TA", "HS", etc.
        self.value = value        # 22.5
        self.unit = unit          # "°C", "%", "hPa", "lux"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'code': self.code,
            'value': self.value,
            'unit': self.unit
        }


class SensorData:
    """
    DTO for sensor data.
    Standardized format used throughout the system for consistency.
    """
    
    def __init__(self, sensor_name, sensor_type, codes=None, index=1):
        self.sensor_name = sensor_name
        self.sensor_type = sensor_type
        self.codes = codes  # Mapping of metric to code (e.g., {"temperature": "TA"})
        self.index = index  # Sensor index for compact format (e.g., "1TA")
        self.readings = []
        self.is_valid = True
        self.error = None
    
    def add_reading(self, code, value, unit=""):
        """Add a reading to this sensor data."""
        # Check if float value is effectively an integer (MicroPython compatible)
        try:
            if isinstance(value, float):
                if value == int(value):
                    value = int(value)
                else:
                    value = round(value, 1)
            self.readings.append(SensorReading(code, value, unit))
        except (ValueError, TypeError):
            print(f"Error converting value {value} to float")
            pass
    
    def get_reading(self, code):
        """Get reading value by metric_code."""
        for reading in self.readings:
            if reading.code == code:
                return reading.value
        return None
    
    def set_error(self, error_message):
        """Mark data as invalid with error message."""
        self.is_valid = False
        self.error = error_message
    
    def to_dict(self):
        """Convert to full dictionary (for WiFi/HTTP communication)."""
        return {
            'sensor': self.sensor_name,
            'type': self.sensor_type,
            'index': self.index,
            'codes': self.codes,
            'valid': self.is_valid,
            'readings': [r.to_dict() for r in self.readings],
            'error': self.error
        }
    
    def to_compact(self):
        """
        Convert to raw compact format (index + code + value).
        Returns:
            dict: {f"{index}{code}": value, ...}
            Example: {"1TA": 25.3, "1HA": 45.0}
        """
        if not self.codes:
            raise ValueError("Sensor codes must be provided")

        compact_data = {}

        for reading in self.readings:
            metric_code = reading.code
            if not metric_code:
                continue
            compact_data[f"{self.index}{metric_code}"] = reading.value

        return compact_data
    
    def __repr__(self):
        readings_str = ", ".join(
            f"{r.code}={r.value}{r.unit}" for r in self.readings
        )
        return f"SensorData({self.sensor_name}: {readings_str})"
