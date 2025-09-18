#!/usr/bin/env python3

import time
import board
import busio
import digitalio
import adafruit_rfm9x

# Setup LoRa with exact same config as working lora_x.py
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = digitalio.DigitalInOut(board.D5)
reset = digitalio.DigitalInOut(board.D25)

print("Initializing LoRa...")
rfm9x = adafruit_rfm9x.RFM9x(spi, cs, reset, frequency=433.0)
rfm9x.tx_power = 14
rfm9x.spreading_factor = 7
rfm9x.signal_bandwidth = 125000

print("LoRa Configuration:")
print(f"  Frequency: {rfm9x.frequency_mhz} MHz")
print(f"  TX Power: {rfm9x.tx_power} dBm")
print(f"  Spreading Factor: {rfm9x.spreading_factor}")
print(f"  Signal Bandwidth: {rfm9x.signal_bandwidth} Hz")
print(f"  Coding Rate: {rfm9x.coding_rate}")
print(f"  Preamble Length: {rfm9x.preamble_length}")

print("\n1. Testing simple message...")
test_msg = "Test123"
rfm9x.send(test_msg.encode('utf-8'))
print(f"Sent: {test_msg}")

time.sleep(1)

print("\n2. Testing with XXXX prefix (like nano)...")
test_msg = "XXXXB|1|123456|test|data|E"
rfm9x.send(test_msg.encode('utf-8'))
print(f"Sent: {test_msg}")

time.sleep(1)

print("\n3. Now listening for 10 seconds...")
print("Try sending from Arduino or another device...")

start = time.time()
while time.time() - start < 10:
    packet = rfm9x.receive(timeout=0.5)
    if packet:
        try:
            message = packet.decode('utf-8')
            rssi = rfm9x.last_rssi
            print(f"Received: {message} (RSSI: {rssi})")
        except:
            print(f"Received binary data: {packet.hex()}")

print("\nTest complete.")