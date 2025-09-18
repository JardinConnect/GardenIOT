#!/usr/bin/env python3
"""
Raspberry Pi 5 - LoRa SX1278 Bidirectional Communication

Wiring for Raspberry Pi 5 to SX1278:
SX1278    ->  Raspberry Pi 5 (GPIO)
VCC       ->  3.3V (Pin 1)
GND       ->  GND (Pin 6)
MISO      ->  GPIO 9 (Pin 21)
MOSI      ->  GPIO 10 (Pin 19)
SCK       ->  GPIO 11 (Pin 23)
NSS       ->  GPIO 8 (Pin 24)
RST       ->  GPIO 4 (Pin 7)
DIO0      ->  GPIO 17 (Pin 11)

Install required libraries:
pip install pyLoRa RPi.GPIO spidev
"""

import time
import struct
import RPi.GPIO as GPIO
from pyLoRa import LoRa, ModemConfig, Board

# Configure GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Create custom board configuration for Raspberry Pi 5
class RaspberryPi5(Board):
    # Pin configuration
    DIO0 = 17   # GPIO 17
    DIO1 = None
    DIO2 = None
    DIO3 = None
    LED  = None
    RESET = 4   # GPIO 4
    SWITCH = None
    
    # SPI configuration
    SPI_BUS = 0
    SPI_CS = 0  # CE0 (GPIO 8)
    
    def setup(self):
        """Setup GPIO pins"""
        super().setup()
        if self.RESET is not None:
            GPIO.setup(self.RESET, GPIO.OUT)
            GPIO.output(self.RESET, GPIO.HIGH)
        if self.DIO0 is not None:
            GPIO.setup(self.DIO0, GPIO.IN)
    
    def reset(self):
        """Reset the module"""
        if self.RESET is not None:
            GPIO.output(self.RESET, GPIO.LOW)
            time.sleep(0.01)
            GPIO.output(self.RESET, GPIO.HIGH)
            time.sleep(0.01)

class LoRaBidirectional:
    def __init__(self):
        # Communication parameters
        self.local_address = 0xBB     # Raspberry Pi address
        self.destination = 0xAA       # Arduino address
        self.msg_count = 0
        self.last_send_time = 0
        self.interval = 2  # Send every 5 seconds
        
        # Initialize LoRa
        self.board = RaspberryPi5()
        self.lora = LoRa(self.board)
        
        # Configure LoRa parameters
        self.lora.set_mode(LoRa.MODE_SLEEP)
        self.lora.set_freq(433.0)  # 433 MHz
        
        # Modem configuration (SF7, BW125, CR4/5, Preamble 8)
        self.lora.set_modem_config(ModemConfig.Bw125Cr45Sf128)
        self.lora.set_spreading_factor(7)
        self.lora.set_signal_bandwidth(125000)
        self.lora.set_coding_rate(5)
        self.lora.set_preamble_length(8)
        self.lora.set_sync_word(0x12)
        self.lora.set_tx_power(17)
        
        # Set to receive mode
        self.lora.set_mode(LoRa.MODE_RXCONT)
        
        print("LoRa Bidirectional Communication Initialized")
        print(f"Local address: 0x{self.local_address:02X}")
        print(f"Frequency: {self.lora.get_freq()} MHz")
        print(f"Spreading Factor: {self.lora.get_spreading_factor()}")
        print(f"Bandwidth: {self.lora.get_signal_bandwidth()} Hz")
        print()
    
    def send_message(self, message):
        """Send a message via LoRa"""
        # Prepare packet
        packet = struct.pack('BBB', self.destination, self.local_address, self.msg_count)
        packet += struct.pack('B', len(message))
        packet += message.encode()
        
        # Send packet
        self.lora.set_mode(LoRa.MODE_STDBY)
        time.sleep(0.01)
        self.lora.send_packet(packet)
        self.lora.set_mode(LoRa.MODE_RXCONT)
        
        self.msg_count = (self.msg_count + 1) % 256
        print(f"Sent: {message}")
    
    def receive_message(self):
        """Check for and process received messages"""
        if self.lora.packet_available():
            # Receive packet
            packet = self.lora.receive_packet()
            
            if len(packet) < 4:
                print("Error: Packet too short")
                return
            
            # Parse header
            recipient = packet[0]
            sender = packet[1]
            msg_id = packet[2]
            msg_length = packet[3]
            
            # Extract message
            if len(packet) < 4 + msg_length:
                print("Error: Message length mismatch")
                return
            
            message = packet[4:4+msg_length].decode('utf-8', errors='ignore')
            
            # Check if message is for this device
            if recipient != self.local_address and recipient != 0xFF:
                print("Message not for this device")
                return
            
            # Print message details
            print(f"Received from: 0x{sender:02X}")
            print(f"Sent to: 0x{recipient:02X}")
            print(f"Message ID: {msg_id}")
            print(f"Message: {message}")
            print(f"RSSI: {self.lora.get_last_packet_rssi()} dBm")
            print(f"SNR: {self.lora.get_last_packet_snr()} dB")
            print()
            
            # Auto-reply example
            if "Hello from Arduino" in message:
                reply = f"Reply from Pi to msg #{msg_id}"
                time.sleep(0.5)  # Small delay to avoid collision
                self.send_message(reply)
    
    def run(self):
        """Main loop"""
        print("Starting main loop...")
        print("Type messages to send, or 'quit' to exit")
        print()
        
        try:
            while True:
                # Check for received messages
                self.receive_message()
                
                # Send periodic messages
                current_time = time.time()
                if current_time - self.last_send_time > self.interval:
                    message = f"Hello from Pi #{self.msg_count}"
                    self.send_message(message)
                    self.last_send_time = current_time
                
                # Small delay to prevent CPU overload
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.cleanup()
    
    def run_interactive(self):
        """Interactive mode - allows manual message sending"""
        import threading
        
        def receive_loop():
            while self.running:
                self.receive_message()
                time.sleep(0.1)
        
        self.running = True
        receive_thread = threading.Thread(target=receive_loop)
        receive_thread.start()
        
        print("Interactive mode - type messages to send, 'quit' to exit")
        
        try:
            while True:
                user_input = input()
                if user_input.lower() == 'quit':
                    break
                elif user_input:
                    self.send_message(user_input)
        finally:
            self.running = False
            receive_thread.join()
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.lora.set_mode(LoRa.MODE_SLEEP)
        GPIO.cleanup()
        print("Cleanup complete")

if __name__ == "__main__":
    lora_comm = LoRaBidirectional()
    
    # Choose mode: automatic periodic sending or interactive
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        lora_comm.run_interactive()
    else:
        lora_comm.run()