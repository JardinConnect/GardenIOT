"""
Sensor Data DTO - Data Transfer Object Pattern
Standardized format for sensor data across the entire system.
"""

import time


class SensorReading:
    """Represents a single sensor reading with metric, value, and unit."""
    
    def __init__(self, metric, value, unit=""):
        self.metric = metric      # "temperature", "humidity", etc.
        self.value = value        # 22.5
        self.unit = unit          # "°C", "%", "hPa", "lux"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'metric': self.metric,
            'value': self.value,
            'unit': self.unit
        }


class SensorData:
    """
    DTO for sensor data.
    Standardized format used throughout the system for consistency.
    """
    
    def __init__(self, sensor_name, sensor_type):
        self.sensor_name = sensor_name
        self.sensor_type = sensor_type
        self.timestamp = time.time() # TODO : use RTC timestamp if available
        self.readings = []
        self.is_valid = True
        self.error = None
    
    def add_reading(self, metric, value, unit=""):
        """Add a reading to this sensor data."""
        self.readings.append(SensorReading(metric, value, unit))
    
    def get_reading(self, metric):
        """Get reading value by metric name."""
        for reading in self.readings:
            if reading.metric == metric:
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
            'timestamp': self.timestamp,
            'valid': self.is_valid,
            'readings': [r.to_dict() for r in self.readings],
            'error': self.error
        }
    
    def to_compact(self, codes=None, index=1):
        """
        Convert to raw compact format (index + code + value).
        Returns:
            dict: {f"{index}{code}": value, ...}
            Example: {"1TA": 25.3, "1HA": 45.0}
        """
        if not codes:
            raise ValueError("Sensor codes must be provided")

        compact_data = {}

        for reading in self.readings:
            metric_code = codes.get(reading.metric)
            if not metric_code:
                continue
            try:
                compact_data[f"{index}{metric_code}"] = float(reading.value)
            except (ValueError, TypeError):
                continue

        return compact_data
    
    def __repr__(self):
        readings_str = ", ".join(
            f"{r.metric}={r.value}{r.unit}" for r in self.readings
        )
        return f"SensorData({self.sensor_name}: {readings_str})"
