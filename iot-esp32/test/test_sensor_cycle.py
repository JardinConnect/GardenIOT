#!/usr/bin/env python3
"""
Test script to verify complete sensor cycle and LoRa message sending.
This simulates what should happen in the main application.
"""

import sys
import time
import json

# Add src to path
sys.path.append('/src')

from config.config_manager import ConfigManager
from core.hardware_manager import HardwareManager
from core.sensor_manager import SensorManager
from core.event_bus import EventBus
from communication.lora_protocol import LoRaProtocol
from communication.communication_manager import CommunicationManager

def test_sensor_cycle():
    print("="*60)
    print("Testing Complete Sensor Cycle")
    print("="*60)
    
    # Initialize components
    config = ConfigManager.get_instance()
    config.load('/src/config/config.json')
    
    event_bus = EventBus()
    hardware = HardwareManager(config)
    
    # Initialize hardware
    print("Initializing hardware...")
    try:
        hardware.init_i2c()
        lora_hw = hardware.init_lora_hardware()
        rtc = hardware.init_rtc()
        print("Hardware initialized")
    except Exception as e:
        print(f"Hardware init failed: {e}")
        return False
    
    # Initialize sensors
    print("Initializing sensors...")
    try:
        sensor_manager = SensorManager(config, hardware, event_bus)
        sensor_manager.initialize_sensors()
        print("Sensors initialized")
    except Exception as e:
        print(f"Sensor init failed: {e}")
        return False
    
    # Initialize communication
    print("Initializing communication...")
    try:
        lora_protocol = LoRaProtocol(
            lora=lora_hw,
            uid=config.get('device.uid'),
            rtc=rtc,
            config=config.get('lora', {})
        )
        communication = CommunicationManager(primary_strategy=lora_protocol)
        print("Communication initialized")
    except Exception as e:
        print(f"Communication init failed: {e}")
        return False
    
    # Test sensor reading
    print("\n" + "="*40)
    print("Reading all sensors...")
    print("="*40)
    
    sensor_data = sensor_manager.read_all_sensors()
    
    print(f"\nSensor data collected:")
    for sensor_name, data in sensor_data.items():
        print(f"  {sensor_name}: {data}")
    
    if not sensor_data:
        print("No sensor data collected")
        return False
    
    # Test data formatting
    print("\n" + "="*40)
    print("Formatting sensor data...")
    print("="*40)
    
    formatted_parts = []
    for sensor_name, readings in sensor_data.items():
        try:
            sensor_codes = config.get_sensor_codes(sensor_name)
            
            if not sensor_codes:
                print(f"  No codes for sensor '{sensor_name}', skipping")
                continue
            
            # Extract data from readings
            if isinstance(readings, dict):
                data = readings.get('data', readings)
                if 'readings' in data:
                    values = {}
                    for r in data['readings']:
                        values[r['metric']] = r['value']
                    data = values
            else:
                continue
            
            for metric, value in data.items():
                if metric in sensor_codes:
                    code = sensor_codes[metric]
                    try:
                        int_value = int(round(float(value)))
                        formatted_parts.append(f"1{code}{int_value}")
                        print(f"  Formatted {sensor_name}.{metric}: {code}{int_value}")
                    except (ValueError, TypeError) as e:
                        print(f"  Invalid value for {sensor_name}.{metric}: {value} ({e})")
        
        except Exception as e:
            print(f"  Format error for '{sensor_name}': {e}")
    
    if not formatted_parts:
        print("No valid sensor data to format")
        return False
    
    payload = ";".join(formatted_parts)
    print(f"\nFinal payload: {payload}")
    
    # Test message building
    print("\n" + "="*40)
    print("Building LoRa message...")
    print("="*40)
    
    message = {
        'type': 'D',
        'uid': config.get('device.uid'),
        'data': payload
    }
    
    print(f"Message: {message}")
    
    # Test sending (without actually sending to avoid LoRa issues)
    print("\n" + "="*40)
    print("Testing message formatting...")
    print("="*40)
    
    try:
        built_message = lora_protocol._build_message(message)
        print(f"Built message: {built_message}")
        
        padded_message = "XXXX" + built_message
        print(f"Padded message: {padded_message}")
        
        frame = padded_message.encode('utf-8')
        print(f"Frame bytes: {frame}")
        print(f"Frame length: {len(frame)} bytes")
        
        print("Message formatting successful")
        lora_protocol.send(message, expect_ack=True)  # Test send without waiting for ACK
        return True
        
    except Exception as e:
        print(f"Message formatting failed: {e}")
        return False

if __name__ == "__main__":
    try:
        success = test_sensor_cycle()
        print("\n" + "="*60)
        if success:
            print("Sensor cycle test PASSED")
        else:
            print("Sensor cycle test FAILED")
        print("="*60)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()