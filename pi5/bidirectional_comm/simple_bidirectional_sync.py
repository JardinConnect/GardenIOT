#!/usr/bin/env python3

import time
import board
import busio
import digitalio
import adafruit_rfm9x

# Setup LoRa
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = digitalio.DigitalInOut(board.D5)
reset = digitalio.DigitalInOut(board.D25)

rfm9x = adafruit_rfm9x.RFM9x(spi, cs, reset, frequency=433.0)
rfm9x.tx_power = 14
rfm9x.spreading_factor = 7
rfm9x.signal_bandwidth = 125000

# Try to set sync word (default is 0x12 for LoRa)
# Note: adafruit library might not expose this directly
# but we can try to match Arduino's default

print("LoRa Bidirectional Communication Started")
print(f"Configuration:")
print(f"  Frequency: {rfm9x.frequency_mhz} MHz")
print(f"  TX Power: {rfm9x.tx_power} dBm")
print(f"  SF: {rfm9x.spreading_factor}")
print(f"  BW: {rfm9x.signal_bandwidth} Hz")
print("Alternating: Receive (10s) -> Send -> Receive (10s) -> Send...")

message_count = 0

while True:
    # RECEIVE MODE - Listen for 10 seconds
    print("\n--- RECEIVE MODE (10s) ---")
    start_time = time.time()
    packets_received = 0

    while time.time() - start_time < 10.0:
        packet = rfm9x.receive(timeout=0.5)
        if packet:
            packets_received += 1
            try:
                message = packet.decode('utf-8')
                rssi = rfm9x.last_rssi
                snr = rfm9x.last_snr
                print(f"[{packets_received}] Received: {message}")
                print(f"    RSSI: {rssi} dBm, SNR: {snr} dB")
            except:
                print(f"[{packets_received}] Received binary: {packet.hex()}")

    if packets_received == 0:
        print("No packets received in this window")

    # SEND MODE - Send one message
    print("\n--- SEND MODE ---")
    message_count += 1
    message = f"Pi5 Msg #{message_count}"

    # Send the message
    rfm9x.send(message.encode('utf-8'))
    print(f"Sent: {message}")

    # Small delay before switching back to receive
    time.sleep(0.5)