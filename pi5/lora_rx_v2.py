"""
Garden IoT - Raspberry Pi5 LoRa Receiver v2
Version: 2.0 - ACK Support

Features:
- Bidirectional communication with ACK system
- Protocol parsing: XXXXB|Type|Timestamp|UID|MsgId|Data|E
- Automatic ACK responses to data messages
- Message deduplication
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
        logging.FileHandler('lora_rx_v2.log'),
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

# Set to store processed message IDs to avoid duplicates
processed_messages = set()

class ProtocolParser:
    @staticmethod
    def parse_message(message):
        """
        Parse protocol message: XXXXB|Type|Timestamp|UID|MsgId|Data|E
        Returns dict with parsed fields or None if invalid
        """
        try:
            message = message.strip()
            
            # Check start and end markers
            if not message.startswith("XXXXB|") or not message.endswith("|E"):
                logger.warning(f"Invalid message format: {message}")
                return None
            
            # Remove markers and split
            content = message[6:-2]  # Remove "XXXXB|" and "|E"
            parts = content.split("|")
            
            if len(parts) < 5:
                logger.warning(f"Insufficient parts in message: {message}")
                return None
            
            return {
                'type': int(parts[0]),
                'timestamp': int(parts[1]),
                'uid': parts[2],
                'msg_id': int(parts[3]),
                'data': parts[4] if len(parts) > 4 else "",
                'raw': message
            }
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
    def __init__(self, db_path="lora_data_v2.db"):
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
                    UNIQUE(uid, msg_id)
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
                INSERT OR IGNORE INTO messages 
                (msg_type, timestamp, uid, msg_id, data, raw_message, rssi)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                parsed_msg['type'],
                parsed_msg['timestamp'],
                parsed_msg['uid'],
                parsed_msg['msg_id'],
                parsed_msg['data'],
                parsed_msg['raw'],
                rssi
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
        except sqlite3.IntegrityError:
            logger.info(f"Duplicate message from {parsed_msg['uid']}, msg_id {parsed_msg['msg_id']}")
            return False
        except Exception as e:
            logger.error(f"Error storing message: {e}")
            return False

class LoRaReceiver:
    def __init__(self):
        self.db_manager = DatabaseManager()
        logger.info("📡 LoRa Receiver v2.0 Ready")
        logger.info("📡 ACK Support: Enabled")
        logger.info("📡 Waiting for LoRa packets...")
    
    def send_ack(self, original_msg):
        """Send ACK message back to sender"""
        try:
            timestamp = int(time.time())
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
        
        msg_key = f"{parsed_msg['uid']}-{parsed_msg['msg_id']}"
        
        # Check for duplicates
        if msg_key in processed_messages:
            logger.info(f"🔄 Duplicate message ignored: {msg_key}")
            return
        
        processed_messages.add(msg_key)
        
        # Store in database
        stored = self.db_manager.store_message(parsed_msg, rssi)
        
        if parsed_msg['type'] == MSG_TYPE_DATA:
            logger.info(f"📥 Data message from {parsed_msg['uid']}")
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
        
        # Keep only last 1000 processed message IDs to prevent memory growth
        if len(processed_messages) > 1000:
            processed_messages.clear()
    
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