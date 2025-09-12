"""
Garden IoT - Raspberry Pi5 LoRa Receiver v2 - Backward Compatible
Version: 2.1 - ACK Support with backward compatibility

Features:
- Supports both old format: XXXXB|Type|Timestamp|UID|Data|E (v2 nano)
- Supports new format: XXXXB|Type|Timestamp|UID|MsgId|Data|E (v3 nano)
- Automatic ACK responses to data messages
- Enhanced logging and error handling
"""

import time
import board
import busio
import digitalio
import adafruit_rfm9x
import sqlite3
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lora_rx_v2_compat.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# LoRa pins on Raspberry Pi
CS = digitalio.DigitalInOut(board.D5)    # Chip Select (GPIO 5)
RESET = digitalio.DigitalInOut(board.D25) # Reset       (GPIO 25)

# SPI bus
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# Initialize LoRa radio
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 433.0)

# Set higher power
rfm9x.tx_power = 23

# Message types
MSG_TYPE_DATA = 1
MSG_TYPE_ACK = 2
MSG_TYPE_ALERT = 3
MSG_TYPE_CONFIG = 4

# Pi5 identifier
PI5_UID = "pi5"

# Message counter for generating fake message IDs for v2 format
message_counter = 0

class ProtocolParser:
    @staticmethod
    def parse_message(message):
        """
        Parse protocol message accounting for 4-char LoRa offset:
        - Nano sends: XXXXB|Type|Timestamp|UID|Data|E (v2 format with offset padding)
        - Pi5 receives: B|Type|Timestamp|UID|Data|E (4 chars lost)
        - Nano sends: XXXXB|Type|Timestamp|UID|MsgId|Data|E (v3 format with offset padding)  
        - Pi5 receives: B|Type|Timestamp|UID|MsgId|Data|E (4 chars lost)
        """
        global message_counter
        try:
            message = message.strip()
            
            # All messages should start with B| due to 4-char offset
            if not message.startswith("B|") or not message.endswith("|E"):
                logger.warning(f"Invalid message format (expected B|...|E): {message}")
                return None
            
            # Remove B| and |E
            content = message[2:-2]
            parts = content.split("|")
            
            # Try to detect if it's v2 (4 parts) or v3 (5+ parts) format
            if len(parts) == 4:
                # v2 format: Type|Timestamp|UID|Data
                message_counter += 1
                fake_msg_id = message_counter
                
                return {
                    'type': int(parts[0]),
                    'timestamp': int(parts[1]),
                    'uid': parts[2],
                    'msg_id': fake_msg_id,  # Generated ID for v2
                    'data': parts[3],
                    'raw': message,
                    'format_version': 'v2'
                }
            elif len(parts) >= 5:
                # v3 format: Type|Timestamp|UID|MsgId|Data
                return {
                    'type': int(parts[0]),
                    'timestamp': int(parts[1]),
                    'uid': parts[2],
                    'msg_id': int(parts[3]),
                    'data': parts[4] if len(parts) > 4 else "",
                    'raw': message,
                    'format_version': 'v3'
                }
            else:
                logger.warning(f"Insufficient parts in message ({len(parts)} parts): {message}")
                return None
                
        except Exception as e:
            logger.error(f"Error parsing message '{message}': {e}")
            return None
    
    @staticmethod
    def parse_sensor_data(data_str):
        """
        Parse sensor data: 1B100:1TA21:1TS22:1HA65:1HS45:1L114
        Returns dict with sensor values
        """
        try:
            sensors = {}
            parts = data_str.split(":")
            
            for part in parts:
                if len(part) < 3:
                    continue
                    
                # Extract sensor type and value
                sensor_id = part[:2]  # e.g., "1B", "1T", "1H", "1L"
                sensor_type = part[2:4]  # e.g., "BA", "TA", "HA", "HS"
                value_str = part[4:]  # The numeric value or "ERR"
                
                if value_str == "ERR":
                    sensors[sensor_type] = None
                    continue
                
                try:
                    value = int(value_str)
                    sensors[sensor_type] = value
                except ValueError:
                    logger.warning(f"Invalid sensor value: {part}")
                    sensors[sensor_type] = None
            
            return sensors
        except Exception as e:
            logger.error(f"Error parsing sensor data '{data_str}': {e}")
            return {}

class DatabaseManager:
    def __init__(self, db_path="lora_data_v2_compat.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    msg_type INTEGER,
                    timestamp INTEGER,
                    uid TEXT,
                    msg_id INTEGER,
                    data TEXT,
                    raw_message TEXT,
                    rssi INTEGER,
                    format_version TEXT DEFAULT 'v2'
                )
            ''')
            
            # Create sensor_data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sensor_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER,
                    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    uid TEXT,
                    battery INTEGER,
                    temp_air INTEGER,
                    temp_soil INTEGER,
                    humidity_air INTEGER,
                    humidity_soil INTEGER,
                    light INTEGER,
                    FOREIGN KEY (message_id) REFERENCES messages (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def store_message(self, parsed_msg, rssi):
        """Store message in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO messages 
                (msg_type, timestamp, uid, msg_id, data, raw_message, rssi, format_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                parsed_msg['type'],
                parsed_msg['timestamp'],
                parsed_msg['uid'],
                parsed_msg['msg_id'],
                parsed_msg['data'],
                parsed_msg['raw'],
                rssi,
                parsed_msg['format_version']
            ))
            
            message_db_id = cursor.lastrowid
            
            # If it's a data message, parse and store sensor data
            if parsed_msg['type'] == MSG_TYPE_DATA and message_db_id > 0:
                sensors = ProtocolParser.parse_sensor_data(parsed_msg['data'])
                
                cursor.execute('''
                    INSERT INTO sensor_data 
                    (message_id, uid, battery, temp_air, temp_soil, humidity_air, humidity_soil, light)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    message_db_id,
                    parsed_msg['uid'],
                    sensors.get('B'),
                    sensors.get('TA'),
                    sensors.get('TS'),
                    sensors.get('HA'),
                    sensors.get('HS'),
                    sensors.get('L')
                ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error storing message: {e}")
            return False

class LoRaReceiver:
    def __init__(self):
        self.db_manager = DatabaseManager()
        logger.info("📡 LoRa Receiver v2.1 - Backward Compatible Ready")
        logger.info("📡 Supports: v2 (B|...) and v3 (XXXXB|...|MsgId|...) formats")
        logger.info("📡 ACK Support: Enabled")
        logger.info("📡 Waiting for LoRa packets...")
    
    def send_ack(self, original_msg):
        """Send ACK message back to sender"""
        try:
            timestamp = int(time.time())
            
            # Send ACK in format compatible with sender's version
            if original_msg['format_version'] == 'v2':
                # Simple ACK for v2 format - just confirmation message
                ack_message = f"XXXXB|{MSG_TYPE_ACK}|{timestamp}|{PI5_UID}|ACK_MSG_{original_msg['msg_id']}|E"
            else:
                # Full ACK for v3 format
                ack_message = f"XXXXB|{MSG_TYPE_ACK}|{timestamp}|{PI5_UID}|{original_msg['msg_id']}||E"
            
            logger.info(f"📤 Sending ACK: {ack_message}")
            
            # Send ACK
            rfm9x.send(ack_message.encode('utf-8'))
            logger.info("✅ ACK sent successfully")
            
        except Exception as e:
            logger.error(f"❌ Error sending ACK: {e}")
    
    def process_message(self, message, rssi):
        """Process received message"""
        parsed_msg = ProtocolParser.parse_message(message)
        
        if not parsed_msg:
            return
        
        # Store in database
        stored = self.db_manager.store_message(parsed_msg, rssi)
        
        if parsed_msg['type'] == MSG_TYPE_DATA:
            logger.info(f"📥 Data message from {parsed_msg['uid']} (format: {parsed_msg['format_version']})")
            logger.info(f"   📊 Message ID: {parsed_msg['msg_id']}")
            logger.info(f"   📶 RSSI: {rssi} dBm")
            
            # Parse and display sensor data
            sensors = ProtocolParser.parse_sensor_data(parsed_msg['data'])
            
            if sensors:
                logger.info("   🌡️  Sensor readings:")
                if sensors.get('B') is not None:
                    logger.info(f"      🔋 Battery: {sensors['B']}%")
                if sensors.get('TA') is not None:
                    logger.info(f"      🌡️  Temp Air: {sensors['TA']}°C")
                if sensors.get('TS') is not None:
                    logger.info(f"      🌱 Temp Soil: {sensors['TS']}°C")
                if sensors.get('HA') is not None:
                    logger.info(f"      💧 Humidity Air: {sensors['HA']}%")
                if sensors.get('HS') is not None:
                    logger.info(f"      🌱 Humidity Soil: {sensors['HS']}%")
                if sensors.get('L') is not None:
                    logger.info(f"      💡 Light: {sensors['L']} lux")
            
            # Send ACK for data messages
            self.send_ack(parsed_msg)
            
        elif parsed_msg['type'] == MSG_TYPE_ACK:
            logger.info(f"✅ ACK received from {parsed_msg['uid']} for message {parsed_msg['msg_id']}")
            
        elif parsed_msg['type'] == MSG_TYPE_ALERT:
            logger.warning(f"⚠️  Alert from {parsed_msg['uid']}: {parsed_msg['data']}")
            self.send_ack(parsed_msg)
            
        else:
            logger.info(f"📨 Unknown message type {parsed_msg['type']} from {parsed_msg['uid']}")
    
    def run(self):
        """Main receiver loop"""
        while True:
            try:
                packet = rfm9x.receive(timeout=1.0)
                
                if packet is not None:
                    # Convert from bytes to string
                    message = packet.decode("utf-8", errors="ignore").strip()
                    rssi = rfm9x.last_rssi
                    
                    logger.info(f"📡 Raw: {message}")
                    self.process_message(message, rssi)
                    
            except KeyboardInterrupt:
                logger.info("🛑 Receiver stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                time.sleep(1)  # Brief pause before retrying

if __name__ == "__main__":
    receiver = LoRaReceiver()
    receiver.run()