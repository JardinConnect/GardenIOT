"""
Simple LoRa test - just send short ACK messages
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

# Initialize LoRa
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 433.0)
rfm9x.tx_power = 14  # Match nano power

print("📡 Simple LoRa Test Ready")
print("📡 Waiting for packets...")

while True:
    try:
        packet = rfm9x.receive(timeout=1.0)
        
        if packet is not None:
            message = packet.decode("utf-8", errors="ignore").strip()
            rssi = rfm9x.last_rssi
            
            print(f"📡 RX: {message} (RSSI: {rssi})")
            
            # Send simple ACK for any data message
            if message.startswith("B|1|"):
                # Extract message parts
                parts = message[2:-2].split("|")  # Remove B| and |E
                if len(parts) >= 4:
                    msg_id = parts[3] if len(parts) > 4 else "1"
                    
                    # Send short ACK
                    ack = f"XXXXB|2|{int(time.time())}|pi5|{msg_id}||E"
                    print(f"📤 TX: {ack}")
                    
                    rfm9x.send(ack.encode('utf-8'))
                    time.sleep(0.1)  # Small delay after sending
                    
    except KeyboardInterrupt:
        print("🛑 Test stopped")
        break
    except Exception as e:
        print(f"❌ Error: {e}")