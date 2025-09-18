#!/usr/bin/env python3

import time
import board
import busio
import digitalio
import adafruit_rfm9x
import json
import logging
from datetime import datetime
from threading import Thread, Event
import queue

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bidirectional_comm.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BidirectionalLoRa:
    def __init__(self, freq=915.0, power=23):
        # Configure SPI connection
        spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

        # Configure CS and Reset pins
        cs = digitalio.DigitalInOut(board.CE1)
        reset = digitalio.DigitalInOut(board.D25)

        # Initialize RFM9x LoRa module
        self.rfm9x = adafruit_rfm9x.RFM9x(
            spi, cs, reset,
            frequency=freq,
            preamble_length=8,
            high_power=True
        )

        self.rfm9x.tx_power = power
        self.rfm9x.signal_bandwidth = 125000
        self.rfm9x.coding_rate = 5
        self.rfm9x.spreading_factor = 7
        self.rfm9x.enable_crc = True

        # Message queues
        self.send_queue = queue.Queue()
        self.receive_queue = queue.Queue()

        # Control flags
        self.running = Event()
        self.running.set()

        # Message counter for tracking
        self.msg_counter = 0
        self.received_counter = 0

        logger.info(f"LoRa initialized - Freq: {freq}MHz, Power: {power}dBm")

    def send_message(self, message_type, data):
        """Add message to send queue"""
        self.msg_counter += 1
        message = {
            "id": self.msg_counter,
            "type": message_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.send_queue.put(message)
        logger.info(f"Queued message #{self.msg_counter}: {message_type}")
        return self.msg_counter

    def receive_message(self, timeout=1.0):
        """Check for incoming messages"""
        packet = self.rfm9x.receive(timeout=timeout)
        if packet:
            try:
                # Decode message
                message_str = packet.decode('utf-8')
                message = json.loads(message_str)

                # Get RSSI
                rssi = self.rfm9x.last_rssi
                message['rssi'] = rssi

                self.received_counter += 1
                logger.info(f"Received message #{self.received_counter}: {message.get('type', 'unknown')} (RSSI: {rssi})")

                # Send ACK if requested
                if message.get('require_ack', False):
                    self._send_ack(message.get('id', 0))

                return message
            except Exception as e:
                logger.error(f"Failed to decode message: {e}")
                return None
        return None

    def _send_ack(self, msg_id):
        """Send acknowledgment for received message"""
        ack = {
            "type": "ACK",
            "ack_id": msg_id,
            "timestamp": datetime.now().isoformat()
        }
        ack_bytes = json.dumps(ack).encode('utf-8')
        self.rfm9x.send(ack_bytes)
        logger.debug(f"Sent ACK for message #{msg_id}")

    def alternate_communication(self, interval=2.0):
        """Alternate between sending and receiving"""
        mode = "receive"  # Start with receive mode

        while self.running.is_set():
            if mode == "receive":
                logger.debug("Mode: RECEIVE")
                # Receive mode for interval seconds
                start_time = time.time()
                while time.time() - start_time < interval:
                    message = self.receive_message(timeout=0.5)
                    if message:
                        self.receive_queue.put(message)
                mode = "send"

            else:  # mode == "send"
                logger.debug("Mode: SEND")
                # Send all queued messages
                messages_sent = 0
                while not self.send_queue.empty() and messages_sent < 3:
                    try:
                        message = self.send_queue.get_nowait()
                        message_bytes = json.dumps(message).encode('utf-8')
                        self.rfm9x.send(message_bytes)
                        logger.info(f"Sent message #{message['id']}: {message['type']}")
                        messages_sent += 1
                        time.sleep(0.5)  # Small delay between messages
                    except queue.Empty:
                        break
                    except Exception as e:
                        logger.error(f"Failed to send message: {e}")

                # If no messages to send, just wait
                if messages_sent == 0:
                    time.sleep(interval)

                mode = "receive"

    def start(self):
        """Start the bidirectional communication thread"""
        self.comm_thread = Thread(target=self.alternate_communication, daemon=True)
        self.comm_thread.start()
        logger.info("Bidirectional communication started")

    def stop(self):
        """Stop the communication thread"""
        self.running.clear()
        if hasattr(self, 'comm_thread'):
            self.comm_thread.join(timeout=5)
        logger.info("Bidirectional communication stopped")

    def get_received_messages(self):
        """Get all received messages from queue"""
        messages = []
        while not self.receive_queue.empty():
            try:
                messages.append(self.receive_queue.get_nowait())
            except queue.Empty:
                break
        return messages

def main():
    """Main function for testing"""
    lora = BidirectionalLoRa(freq=915.0, power=23)

    try:
        # Start communication thread
        lora.start()

        # Example: Send test messages periodically
        test_counter = 0
        while True:
            # Send a test message every 10 seconds
            test_counter += 1
            lora.send_message("sensor_data", {
                "temperature": 22.5 + test_counter * 0.1,
                "humidity": 45 + test_counter * 0.5,
                "sensor_id": "pi5_sensor"
            })

            # Check for received messages
            messages = lora.get_received_messages()
            for msg in messages:
                print(f"Received: {json.dumps(msg, indent=2)}")

            time.sleep(10)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        lora.stop()

if __name__ == "__main__":
    main()