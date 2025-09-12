"""
Pi5 LoRa Bidirectional Test
Simple test to validate communication with matching configuration
"""

import time
import board
import busio
import digitalio
import adafruit_rfm9x

# LoRa pins
CS = digitalio.DigitalInOut(board.D5)
RESET = digitalio.DigitalInOut(board.D25)

# SPI bus
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# Initialize LoRa with EXACT same config as nano
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 433.0)

# Match nano configuration exactly
rfm9x.tx_power = 14              # Same as nano
rfm9x.spreading_factor = 7       # SF7
rfm9x.signal_bandwidth = 125000  # 125kHz
rfm9x.coding_rate = 5            # 4/5
rfm9x.preamble_length = 8        # 8 symbols
rfm9x.sync_word = 0x12           # Default

print("=== Pi5 LoRa Test ===")
print("Config: 433MHz, 14dBm, SF7, 125kHz, CR4/5")
print("Listening for nano messages...")
print("===================")

def send_ack(msg_id, target_node):
    """Send simple ACK back to nano"""
    try:
        ack_msg = f"ACK|{msg_id}|{target_node}"
        print(f"📤 TX: {ack_msg}")
        
        # Send ACK
        rfm9x.send(ack_msg.encode('utf-8'))
        print("  -> ACK sent")
        
    except Exception as e:
        print(f"  -> ACK failed: {e}")

def parse_test_message(message):
    """Parse TEST|msgId|nodeId format"""
    try:
        parts = message.strip().split("|")
        if len(parts) >= 3 and parts[0] == "TEST":
            return {
                'type': 'TEST',
                'msg_id': parts[1],
                'node_id': parts[2]
            }
    except:
        pass
    return None

# Main loop
while True:
    try:
        # Listen for packets
        packet = rfm9x.receive(timeout=1.0)
        
        if packet is not None:
            # Show raw bytes first
            print(f"📡 Raw packet ({len(packet)} bytes): {packet}")
            
            # Decode message
            raw_message = packet.decode("utf-8", errors="ignore").strip()
            rssi = rfm9x.last_rssi
            
            print(f"📡 RX: '{raw_message}'")
            print(f"   RSSI: {rssi} dBm")
            print(f"   Length: {len(raw_message)} chars")
            
            # Show each character
            if len(raw_message) > 0:
                chars = [f"'{c}'({ord(c)})" for c in raw_message[:10]]  # First 10 chars
                print(f"   Chars: {' '.join(chars)}")
            
            # Parse message
            parsed = parse_test_message(raw_message)
            
            if parsed:
                print(f"   ✓ Valid TEST message from {parsed['node_id']}")
                print(f"   ✓ Message ID: {parsed['msg_id']}")
                
                # Send ACK back
                send_ack(parsed['msg_id'], parsed['node_id'])
                
            else:
                print(f"   ⚠ Unknown format: {raw_message}")
            
            print("---")
                    
    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user")
        break
    except Exception as e:
        print(f"❌ Error: {e}")
        time.sleep(1)