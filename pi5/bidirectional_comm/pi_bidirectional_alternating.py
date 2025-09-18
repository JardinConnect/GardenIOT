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
rfm9x.tx_power = 23

print("Pi Bidirectional - Alternating Protocol")
print("Protocol: Arduino sends first, Pi receives")
print("Then: Pi sends back, Arduino receives")
print("\nWaiting for Arduino message...")

message_count = 0
receive_mode = True

while True:
    if receive_mode:
        # RECEIVE MODE - Wait for Arduino message
        print("\n--- LISTENING for Arduino ---")
        received = False
        timeout_start = time.time()

        # Listen for up to 30 seconds for Arduino message
        while time.time() - timeout_start < 30:
            packet = rfm9x.receive(timeout=1.0)
            if packet:
                try:
                    message = packet.decode('utf-8', errors='ignore').strip()
                    if message.startswith('XXXX'):
                        message = message[4:]

                    rssi = rfm9x.last_rssi
                    print(f"Received from Arduino: {message} (RSSI: {rssi})")
                    received = True
                    break
                except Exception as e:
                    print(f"Error decoding: {e}")

        if not received:
            print("No message from Arduino - continuing to listen...")
            continue

        # Switch to send mode
        receive_mode = False
        print("\n--- SENDING REPLY ---")

    else:
        # SEND MODE - Reply to Arduino
        message_count += 1
        reply = f"XXXXPi5 Reply #{message_count}"

        # Send reply
        rfm9x.send(reply.encode('utf-8'))
        print(f"Sent reply: {reply[4:]}")

        # Small delay, then switch back to receive mode
        time.sleep(2)
        receive_mode = True

    time.sleep(0.1)