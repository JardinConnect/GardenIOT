#!/usr/bin/env python3

import time
import board
import busio
import digitalio
import adafruit_rfm9x

# Setup LoRa
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = digitalio.DigitalInOut(board.CE1)
reset = digitalio.DigitalInOut(board.D25)

rfm9x = adafruit_rfm9x.RFM9x(spi, cs, reset, frequency=915.0)
rfm9x.tx_power = 23

print("LoRa Bidirectional Communication Started")
print("Alternating: Receive (2s) -> Send -> Receive (2s) -> Send...")

message_count = 0

while True:
    # RECEIVE MODE - Listen for 2 seconds
    print("\n--- RECEIVE MODE ---")
    start_time = time.time()
    while time.time() - start_time < 2.0:
        packet = rfm9x.receive(timeout=0.5)
        if packet:
            try:
                message = packet.decode('utf-8')
                rssi = rfm9x.last_rssi
                print(f"Received: {message} (RSSI: {rssi})")
            except:
                print("Received invalid packet")

    # SEND MODE - Send one message
    print("--- SEND MODE ---")
    message_count += 1
    message = f"Pi5 Message #{message_count}"
    rfm9x.send(message.encode('utf-8'))
    print(f"Sent: {message}")

    # Small delay before switching back to receive
    time.sleep(0.5)