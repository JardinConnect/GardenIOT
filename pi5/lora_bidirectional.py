"""
Raspberry Pi5 LoRa Bidirectional Test
Version: Full Duplex Communication Test

Features:
- Sends periodic messages to Arduino Nano
- Listens continuously for messages from Nano
- No ACK logic - pure bidirectional testing  
- SX1278 @ 433 MHz via RFM9x module
"""

import time
import board
import busio
import digitalio
import adafruit_rfm9x
import logging
from datetime import datetime
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('lora_bidirectional.log'),
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

# Configuration matching Arduino Nano exactly
rfm9x.tx_power = 14              # Same as nano
rfm9x.spreading_factor = 7       # SF7
rfm9x.signal_bandwidth = 125000  # 125kHz
rfm9x.coding_rate = 5            # 4/5
rfm9x.preamble_length = 8        # 8 symbols
rfm9x.sync_word = 0x12           # Default

# Node info
NODE_ID = "pi5"
msg_count = 0
send_interval = 7  # Send every 7 seconds (different from nano to avoid collisions)

class LoRaBidirectional:
    def __init__(self):
        self.running = True
        self.last_send_time = time.time()
        
        logger.info("=================================")
        logger.info("Raspberry Pi5 LoRa Bidirectional")
        logger.info("=================================")
        logger.info(f"Node ID: {NODE_ID}")
        logger.info("✅ LoRa configured:")
        logger.info(f"   Freq: 433MHz, Power: {rfm9x.tx_power}dBm")
        logger.info(f"   SF: {rfm9x.spreading_factor}, BW: {rfm9x.signal_bandwidth}Hz")
        logger.info(f"   CR: 4/{rfm9x.coding_rate}, Preamble: {rfm9x.preamble_length}")
        logger.info("=================================")
        logger.info("🔄 Starting bidirectional test...")
        logger.info("")
    
    def send_message(self, message_type="PI5_MSG", data=""):
        """Send a message to the Arduino"""
        global msg_count
        msg_count += 1
        
        current_time = int(time.time() * 1000)  # Milliseconds like Arduino
        
        if message_type == "PI5_MSG":
            # Format: PI5_MSG|count|nodeId|timestamp  
            message = f"{message_type}|{msg_count}|{NODE_ID}|{current_time}"
        elif message_type == "SENSOR_REQ":
            # Request sensor data
            message = f"SENSOR_REQ|{NODE_ID}|{current_time}"
        elif message_type == "PING":
            # Ping message
            message = f"PING|{NODE_ID}|{current_time}"
        else:
            message = f"{message_type}|{NODE_ID}|{data}|{current_time}"
        
        logger.info(f"📤 TX: {message}")
        
        try:
            # Send message
            rfm9x.send(message.encode('utf-8'))
            logger.info("   ✅ Sent successfully")
            
            self.last_send_time = time.time()
            
        except Exception as e:
            logger.error(f"   ❌ Send failed: {e}")
    
    def parse_nano_message(self, message):
        """Parse different types of messages from Arduino"""
        try:
            if message.startswith("NANO_MSG|"):
                # NANO_MSG|count|nodeId|timestamp
                parts = message.split("|")
                if len(parts) >= 4:
                    msg_num = parts[1]
                    node_id = parts[2] 
                    timestamp = parts[3]
                    
                    logger.info(f"   📊 Regular message #{msg_num} from {node_id} at {timestamp}")
                    return True
                    
            elif message.startswith("HEARTBEAT|"):
                # HEARTBEAT|nodeId|timestamp
                parts = message.split("|")
                if len(parts) >= 3:
                    node_id = parts[1]
                    timestamp = parts[2]
                    
                    logger.info(f"   💓 Heartbeat from {node_id} at {timestamp}")
                    return True
                    
            elif message.startswith("SENSOR|"):
                # SENSOR|nodeId|T:25.5|H:60.2
                parts = message.split("|")
                if len(parts) >= 4:
                    node_id = parts[1]
                    temp_data = parts[2]  # T:25.5
                    hum_data = parts[3]   # H:60.2
                    
                    logger.info(f"   🌡️ Sensor data from {node_id}: {temp_data}, {hum_data}")
                    return True
                    
        except Exception as e:
            logger.error(f"   ⚠️ Error parsing message: {e}")
        
        return False
    
    def listen_for_messages(self):
        """Continuously listen for incoming messages"""
        packet = rfm9x.receive(timeout=0.5)  # 500ms timeout
        
        if packet is not None:
            try:
                # Decode message
                raw_message = packet.decode("utf-8", errors="ignore").strip()
                rssi = rfm9x.last_rssi
                snr = rfm9x.last_snr
                
                if len(raw_message) > 0:
                    logger.info(f"📥 RX: {raw_message}")
                    logger.info(f"   📶 RSSI: {rssi} dBm, SNR: {snr} dB")
                    
                    # Parse the message
                    if self.parse_nano_message(raw_message):
                        logger.info("   ✅ Valid nano message received!")
                    else:
                        logger.info("   ⚠️ Unknown message format")
                    
                    logger.info("")
                    
            except Exception as e:
                logger.error(f"❌ Error processing received message: {e}")
    
    def run_sender_thread(self):
        """Thread function for sending periodic messages"""
        while self.running:
            try:
                current_time = time.time()
                
                # Send periodic messages
                if current_time - self.last_send_time >= send_interval:
                    self.send_message("PI5_MSG")
                    logger.info("")
                
                # Send special messages occasionally
                if msg_count % 5 == 0 and msg_count > 0:
                    time.sleep(1)  # Small delay
                    self.send_message("PING", "connectivity_test")
                    logger.info("")
                
                time.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                logger.error(f"❌ Error in sender thread: {e}")
                time.sleep(1)
    
    def run(self):
        """Main execution function"""
        # Start sender thread
        sender_thread = threading.Thread(target=self.run_sender_thread, daemon=True)
        sender_thread.start()
        
        logger.info("🎯 Threads started - listening for messages...")
        logger.info("   📤 Sending messages every 7 seconds")
        logger.info("   📥 Listening continuously")
        logger.info("")
        
        # Main loop - listen for messages
        try:
            while self.running:
                self.listen_for_messages()
                time.sleep(0.01)  # Minimal delay
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Bidirectional test stopped by user")
            self.running = False
        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}")
            self.running = False

# Additional utility functions
def send_sensor_request():
    """Send a sensor data request to the nano"""
    try:
        message = f"GET_SENSORS|{NODE_ID}|{int(time.time() * 1000)}"
        logger.info(f"📤 Sensor request: {message}")
        rfm9x.send(message.encode('utf-8'))
        logger.info("   ✅ Sensor request sent")
    except Exception as e:
        logger.error(f"   ❌ Failed to send sensor request: {e}")

def send_command(command, value=""):
    """Send a command to the nano"""
    try:
        current_time = int(time.time() * 1000)
        message = f"CMD|{command}|{value}|{NODE_ID}|{current_time}"
        logger.info(f"📤 Command: {message}")
        rfm9x.send(message.encode('utf-8'))
        logger.info(f"   ✅ Command '{command}' sent")
    except Exception as e:
        logger.error(f"   ❌ Failed to send command: {e}")

if __name__ == "__main__":
    # Create and run the bidirectional communication
    lora_comm = LoRaBidirectional()
    lora_comm.run()