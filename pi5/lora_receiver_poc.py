#!/usr/bin/env python3
import time
import board
import busio
import digitalio
import adafruit_rfm9x
from datetime import datetime
import re

# LoRa pins on Raspberry Pi
CS    = digitalio.DigitalInOut(board.D5)    # Chip Select (GPIO 5)
RESET = digitalio.DigitalInOut(board.D25)   # Reset       (GPIO 25)

# SPI bus
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# Initialize LoRa radio
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 433.0)
rfm9x.tx_power = 23

# Message types
MESSAGE_TYPES = {
    "1": "DATA",
    "2": "ALERT",
    "3": "ERROR"
}

# Sensor types
SENSOR_TYPES = {
    "TA": "Temp Air",
    "TS": "Temp Sol",
    "HA": "Humid Air",
    "HS": "Humid Sol",
    "B": "Batterie",
    "L": "Luminosité"
}

def parse_message(message):
    """Parse the LoRa message according to protocol"""
    try:
        # Check if message starts with B and ends with E
        if not message.startswith('B|') or not message.endswith('|E'):
            return None
        
        # Remove B| and |E
        content = message[2:-2]
        parts = content.split('|')
        
        if len(parts) != 4:
            return None
        
        msg_type, timestamp, uid, data_str = parts
        
        # Parse timestamp
        dt = datetime.fromtimestamp(int(timestamp))
        
        parsed = {
            'type': MESSAGE_TYPES.get(msg_type, "UNKNOWN"),
            'timestamp': dt.strftime('%Y-%m-%d %H:%M:%S'),
            'uid': uid,
            'data': parse_sensor_data(data_str)
        }
        
        return parsed
    except Exception as e:
        print(f"Error parsing message: {e}")
        return None

def parse_sensor_data(data_str):
    """Parse sensor data string"""
    sensors = {}
    
    # Pattern to match sensor data: optional digit + sensor code + value
    pattern = r'(\d?)([A-Z]+)(\d+|ERR)'
    matches = re.findall(pattern, data_str)
    
    for match in matches:
        sensor_num, sensor_type, value = match
        
        # Handle sensor numbering (for multiple sensors of same type)
        if sensor_num:
            sensor_key = f"{sensor_type}{sensor_num}"
        else:
            sensor_key = sensor_type
        
        # Get sensor name
        sensor_name = SENSOR_TYPES.get(sensor_type, sensor_type)
        if sensor_num:
            sensor_name = f"{sensor_name} {sensor_num}"
        
        # Handle value
        if value == "ERR":
            sensors[sensor_key] = {'name': sensor_name, 'value': 'ERROR'}
        else:
            val = int(value)
            # Format value based on sensor type
            if sensor_type in ['HA', 'HS', 'B', 'L']:
                sensors[sensor_key] = {'name': sensor_name, 'value': f"{val}%"}
            elif sensor_type in ['TA', 'TS']:
                sensors[sensor_key] = {'name': sensor_name, 'value': f"{val}°C"}
            else:
                sensors[sensor_key] = {'name': sensor_name, 'value': val}
    
    return sensors

def display_data(parsed_msg):
    """Display parsed message in a nice format"""
    print("\n" + "="*60)
    print(f"📡 Message Type: {parsed_msg['type']}")
    print(f"⏰ Timestamp: {parsed_msg['timestamp']}")
    print(f"🆔 Node UID: {parsed_msg['uid']}")
    print("-"*60)
    print("📊 Sensor Data:")
    
    for sensor_id, sensor_info in parsed_msg['data'].items():
        icon = ""
        if 'Temp' in sensor_info['name']:
            icon = "🌡️"
        elif 'Humid' in sensor_info['name']:
            icon = "💧"
        elif 'Batterie' in sensor_info['name']:
            icon = "🔋"
        elif 'Luminosité' in sensor_info['name']:
            icon = "☀️"
        
        print(f"  {icon} {sensor_info['name']}: {sensor_info['value']}")
    
    print("="*60)

print("🚀 LoRa Receiver POC - Garden IOT")
print("📡 Waiting for sensor data...")
print("-"*60)

packet_count = 0

while True:
    packet = rfm9x.receive(timeout=1.0)
    
    if packet is not None:
        packet_count += 1
        
        # Convert from bytes to string
        message = packet.decode("utf-8", errors="ignore").strip()
        
        # Show raw message
        print(f"\n[Packet #{packet_count}] Raw: {message}")
        
        # Parse and display
        parsed = parse_message(message)
        if parsed:
            display_data(parsed)
        else:
            print("⚠️  Invalid message format")
        
        # Show RSSI (signal strength)
        if rfm9x.last_rssi is not None:
            print(f"📶 Signal Strength: {rfm9x.last_rssi} dBm")