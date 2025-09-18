import time
import board
import busio
import digitalio
import adafruit_rfm9x
from datetime import datetime

# LoRa pins on Raspberry Pi
CS    = digitalio.DigitalInOut(board.D5)    # Chip Select (GPIO 5)
RESET = digitalio.DigitalInOut(board.D25)   # Reset       (GPIO 25)

# SPI bus
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# Initialize LoRa radio
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 433.0)
rfm9x.tx_power = 23

# Message types
MSG_TYPE_DATA = 1
MSG_TYPE_ALERT = 2
MSG_TYPE_ERROR = 3

# Sensor types mapping
SENSOR_TYPES = {
    'TA': 'Température Air',
    'TS': 'Température Sol',
    'HA': 'Humidité Air',
    'HS': 'Humidité Sol',
    'B': 'Batterie',
    'L': 'Luminosité'
}

def parse_protocol_message(message):
    """
    Parse messages in format: XXXXB|TYPE|TIMESTAMP|UID|DATAS|E
    where DATAS is like: 1B100:1TA21:1TS22:1HA65:1HS45:L50
    """
    try:
        # Remove the XXXX prefix if present
        if message.startswith('XXXX'):
            message = message[4:]
            
        # Check message boundaries
        if not message.startswith('B|') or not message.endswith('|E'):
            return None
            
        # Remove boundaries and split
        content = message[2:-2]  # Remove B| and |E
        parts = content.split('|')
        
        if len(parts) != 4:
            return None
            
        msg_type = int(parts[0])
        timestamp = int(parts[1])
        uid = parts[2]
        data_section = parts[3]
        
        # Parse data section based on message type
        if msg_type == MSG_TYPE_DATA:
            # Split sensor data by ':'
            sensor_data = {}
            data_parts = data_section.split(':')
            
            for part in data_parts:
                if not part:
                    continue
                    
                # Parse each sensor data (e.g., "1B100", "1TA21", "L50")
                sensor_id = None
                sensor_type = None
                value = None
                
                # Check if it starts with a digit (sensor ID)
                if part[0].isdigit():
                    sensor_id = part[0]
                    remaining = part[1:]
                else:
                    remaining = part
                
                # Extract sensor type (1-2 letters)
                if len(remaining) >= 2:
                    if remaining[0:2] in SENSOR_TYPES:
                        sensor_type = remaining[0:2]
                        value = remaining[2:]
                    elif remaining[0] in SENSOR_TYPES:
                        sensor_type = remaining[0]
                        value = remaining[1:]
                
                # Check if value is an error
                if not value or value == "":
                    value = "0"
                
                if sensor_type and value:
                    key = f"{sensor_id}_{sensor_type}" if sensor_id else sensor_type
                    sensor_data[key] = {
                        'type': SENSOR_TYPES.get(sensor_type, sensor_type),
                        'value': value,
                        'sensor_id': sensor_id
                    }
            
            return {
                'type': 'DATA',
                'timestamp': timestamp,
                'uid': uid,
                'sensors': sensor_data
            }
            
        elif msg_type == MSG_TYPE_ALERT:
            # Parse alert (e.g., "2HS0")
            sensor_id = None
            if data_section[0].isdigit():
                sensor_id = data_section[0]
                remaining = data_section[1:]
            else:
                remaining = data_section
                
            # Extract sensor type and value
            sensor_type = remaining[:2] if len(remaining) >= 2 else remaining
            value = remaining[2:] if len(remaining) > 2 else '0'
            
            return {
                'type': 'ALERT',
                'timestamp': timestamp,
                'uid': uid,
                'sensor': SENSOR_TYPES.get(sensor_type, sensor_type),
                'sensor_id': sensor_id,
                'value': value
            }
            
        elif msg_type == MSG_TYPE_ERROR:
            # Parse error (e.g., "1HSERR")
            sensor_id = None
            if data_section[0].isdigit():
                sensor_id = data_section[0]
                remaining = data_section[1:]
            else:
                remaining = data_section
                
            # Extract sensor type
            sensor_type = remaining.replace('ERR', '')
            
            return {
                'type': 'ERROR',
                'timestamp': timestamp,
                'uid': uid,
                'sensor': SENSOR_TYPES.get(sensor_type, sensor_type),
                'sensor_id': sensor_id
            }
            
    except Exception as e:
        print(f"Error parsing message: {e}")
        return None

def format_parsed_data(parsed):
    """Format parsed data for display"""
    if not parsed:
        return "Invalid message"
        
    dt = datetime.fromtimestamp(parsed['timestamp'])
    output = []
    output.append(f"📡 {parsed['type']} from {parsed['uid']} at {dt.strftime('%H:%M:%S')}")
    
    if parsed['type'] == 'DATA':
        for key, data in parsed['sensors'].items():
            sensor_label = f"Capteur {data['sensor_id']}" if data['sensor_id'] else ""
            # Add unit based on sensor type
            unit = "%"
            if data['type'] == 'Température Air' or data['type'] == 'Température Sol':
                unit = "°C"
            elif data['type'] == 'Luminosité':
                unit = " lux"  
            output.append(f"   • {data['type']} {sensor_label}: {data['value']}{unit}")
            
    elif parsed['type'] == 'ALERT':
        sensor_label = f"Capteur {parsed['sensor_id']}" if parsed['sensor_id'] else ""
        output.append(f"   ⚠️ {parsed['sensor']} {sensor_label}: {parsed['value']}%")
        
    elif parsed['type'] == 'ERROR':
        sensor_label = f"Capteur {parsed['sensor_id']}" if parsed['sensor_id'] else ""
        output.append(f"   ❌ Erreur {parsed['sensor']} {sensor_label}")
        
    return "\n".join(output)

print("📡 LoRa Protocol Receiver Ready")
print("📡 Waiting for protocol messages (with XXXX prefix)...")
print("-" * 40)

while True:
    packet = rfm9x.receive()
    
    if packet is not None:
        # Convert from bytes to string
        message = packet.decode("utf-8", errors="ignore").strip()
        print(f"\n📥 Raw: {message}")
        
        # Parse the protocol message
        parsed = parse_protocol_message(message)
        
        if parsed:
            print(format_parsed_data(parsed))
        else:
            # Try parsing as simple format (nano_lora_final)
            try:
                # Remove XXXX if present
                if message.startswith('XXXX'):
                    message = message[4:]
                    
                parts = message.split(',')
                data = {}
                for part in parts:
                    if ':' in part:
                        key, value = part.split(':', 1)
                        data[key] = value
                
                if data:
                    print("📊 Simple format:")
                    for key, value in data.items():
                        print(f"   • {key}: {value}")
                else:
                    print(f"   ⚠️ Unable to parse message")
                    
            except Exception as e:
                print(f"   ⚠️ Unable to parse message: {e}")
        
        print("-" * 40)
    
    time.sleep(0.5)
