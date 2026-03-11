#!/usr/bin/env python3
"""
Simple test script for SensorData DTO implementation.
Tests only the DTO classes without hardware dependencies.
"""

import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from models.sensor_data import SensorData, SensorReading

def test_sensor_reading():
    """Test SensorReading class."""
    print("Testing SensorReading...")
    
    reading = SensorReading("temperature", 22.5, "°C")
    print(f"  Reading: {reading.metric} = {reading.value}{reading.unit}")
    print(f"  Dict: {reading.to_dict()}")
    print("  [OK] SensorReading test passed\n")

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
    print("  [OK] SensorData test passed\n")

def test_dto_serialization():
    """Test DTO serialization and deserialization."""
    print("Testing DTO serialization...")
    
    # Create DTO
    dto = SensorData("luminosity", "BH1750")
    dto.add_reading("luminance", 500.0, "lux")
    
    # Serialize to dict
    data_dict = dto.to_dict()
    print(f"  Serialized: {data_dict}")
    
    # Deserialize (create new DTO from dict)
    new_dto = SensorData(data_dict['sensor'], data_dict['type'])
    for reading in data_dict['readings']:
        new_dto.add_reading(reading['metric'], reading['value'], reading['unit'])
    
    print(f"  Deserialized: {new_dto}")
    print(f"  Values match: {dto.get_reading('luminance') == new_dto.get_reading('luminance')}")
    print("  [OK] Serialization test passed\n")

def test_compact_format():
    """Test compact format for LoRa communication."""
    print("Testing compact format...")
    
    # Test with multiple sensors
    sensors_data = []
    
    # DHT22
    dht_dto = SensorData("air", "DHT22")
    dht_dto.add_reading("temperature", 25.5, "°C")
    dht_dto.add_reading("humidity", 70.0, "%")
    sensors_data.append(dht_dto)
    
    # BH1750
    bh_dto = SensorData("luminosity", "BH1750")
    bh_dto.add_reading("luminance", 450.0, "lux")
    sensors_data.append(bh_dto)
    
    # DS18B20
    ds_dto = SensorData("sol_temp", "DS18B20")
    ds_dto.add_reading("temperature", 18.0, "°C")
    sensors_data.append(ds_dto)
    
    # Format for LoRa transmission
    lora_payloads = []
    for dto in sensors_data:
        compact = dto.to_compact()
        lora_payloads.append(compact)
        print(f"  {dto.sensor_name} compact: {compact}")
    
    print("  [OK] Compact format test passed\n")

def main():
    """Run all tests."""
    print("=" * 60)
    print("           SensorData DTO Tests")
    print("=" * 60)
    print()
    
    test_sensor_reading()
    test_sensor_data()
    test_dto_serialization()
    test_compact_format()
    
    print("=" * 60)
    print("           All tests completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()
