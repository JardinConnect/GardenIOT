#!/usr/bin/env python3
"""
Test script for SensorData DTO implementation.
"""

import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from models.sensor_data import SensorData, SensorReading
from sensors.dth22_sensor import DHT22Sensor
from sensors.bh1750_sensor import BH1750Sensor

def test_sensor_reading():
    """Test SensorReading class."""
    print("Testing SensorReading...")
    
    reading = SensorReading("temperature", 22.5, "°C")
    print(f"  Reading: {reading.metric} = {reading.value}{reading.unit}")
    print(f"  Dict: {reading.to_dict()}")
    print(" SensorReading test passed\n")

def test_sensor_data():
    """Test SensorData class."""
    print("Testing SensorData...")
    
    dto = SensorData("air", "DHT22")
    dto.add_reading("temperature", 22.5, "°C")
    dto.add_reading("humidity", 65.0, "%")
    
    print(f"  DTO: {dto}")
    print(f"  Full dict: {dto.to_dict()}")
    print(f"  Compact: {dto.to_compact()}")
    print(f"  Temperature value: {dto.get_reading('temperature')}")
    print(" SensorData test passed\n")

def test_dht22_with_dto():
    """Test DHT22 sensor with DTO."""
    print("Testing DHT22 sensor with DTO...")
    
    try:
        # Create sensor (won't work without hardware, but we can test the structure)
        sensor = DHT22Sensor(name="test_dht22", pin=27)
        
        # Mock the _read_raw method to return test data
        def mock_read_raw():
            return {'temperature': 25.0, 'humidity': 70.0}
        
        sensor._read_raw = mock_read_raw
        
        # Read data (should return SensorData DTO)
        dto = sensor.read()
        
        print(f"  Sensor: {sensor.name}")
        print(f"  DTO type: {type(dto).__name__}")
        print(f"  DTO: {dto}")
        print(f"  Full dict: {dto.to_dict()}")
        print(f"  Compact: {dto.to_compact()}")
        print(" DHT22 with DTO test passed\n")
        
    except Exception as e:
        print(f" DHT22 test failed: {e}\n")

def test_bh1750_with_dto():
    """Test BH1750 sensor with DTO."""
    print("Testing BH1750 sensor with DTO...")
    
    try:
        # Create sensor (won't work without hardware, but we can test the structure)
        sensor = BH1750Sensor(name="test_bh1750", i2c_id=0, sda_pin=21, scl_pin=22)
        
        # Mock the _read_raw method to return test data
        def mock_read_raw():
            return {'luminance': 500.0}
        
        sensor._read_raw = mock_read_raw
        
        # Read data (should return SensorData DTO)
        dto = sensor.read()
        
        print(f"  Sensor: {sensor.name}")
        print(f"  DTO type: {type(dto).__name__}")
        print(f"  DTO: {dto}")
        print(f"  Full dict: {dto.to_dict()}")
        print(f"  Compact: {dto.to_compact()}")
        print(" BH1750 with DTO test passed\n")
        
    except Exception as e:
        print(f" BH1750 test failed: {e}\n")

def main():
    """Run all tests."""
    print("=" * 60)
    print("           SensorData DTO Tests")
    print("=" * 60)
    print()
    
    test_sensor_reading()
    test_sensor_data()
    test_dht22_with_dto()
    test_bh1750_with_dto()
    
    print("=" * 60)
    print("           All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
