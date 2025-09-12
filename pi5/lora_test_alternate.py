"""
Pi5 LoRa Alternative Config Test
Test avec configuration alternative pour éviter l'offset
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

# Alternative configuration to match nano
rfm9x.tx_power = 14              
rfm9x.spreading_factor = 8       # SF8
rfm9x.signal_bandwidth = 125000  # 125kHz
rfm9x.coding_rate = 8            # 4/8
rfm9x.preamble_length = 12       # 12 symbols
rfm9x.sync_word = 0x34           # Different sync word

print("=== Pi5 Alternative Config Test ===")
print("Configuration:")
print(f"  SF: {rfm9x.spreading_factor}, CR: 4/{rfm9x.coding_rate}")
print(f"  Preamble: {rfm9x.preamble_length}, Sync: 0x{rfm9x.sync_word:02X}")
print("Listening...")
print("===================================")

# Main loop
while True:
    try:
        packet = rfm9x.receive(timeout=1.0)
        
        if packet is not None:
            raw_message = packet.decode("utf-8", errors="ignore").strip()
            rssi = rfm9x.last_rssi
            
            print(f"📡 Raw packet: {packet}")
            print(f"📡 Decoded: '{raw_message}'")
            print(f"   RSSI: {rssi} dBm, Length: {len(raw_message)}")
            
            # Check if message is complete
            if raw_message.startswith("TEST"):
                print("   ✓ Complete message received!")
            else:
                print(f"   ⚠ Possibly truncated (expected TEST...)")
            
            print("---")
                    
    except KeyboardInterrupt:
        print("\n🛑 Test stopped")
        break
    except Exception as e:
        print(f"❌ Error: {e}")
        time.sleep(1)