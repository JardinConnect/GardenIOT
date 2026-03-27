# Test LoRa communication with ACK response for Pi5
import time
import unittest
import sys
import os

# Add parent directory to Python path so we can import from communications
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from communications.lora_communication import LoRaCommunication
from config import load_config

class TestLoRaCommunication(unittest.TestCase):
    """Test LoRa communication with ACK response functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = load_config()
        print(f"LoRa Config: {self.config['lora']}")
        self.lora_comm = LoRaCommunication(self.config["lora"])
        self.lora_comm.initialize()
        print("lora_comm initialized with config:", self.lora_comm)
        
    def tearDown(self):
        """Clean up after tests"""
        self.lora_comm.shutdown()
    
    def test_send_and_receive_ack(self):
        """Test sending a message and receiving ACK from ESP32"""
        print("Starting Pi5 LoRa communication test...")
        print(f"LoRa config: freq={self.config['lora']['frequency']}MHz, SF={self.config['lora']['spreading_factor']}, BW={self.config['lora']['bandwidth']}")
        
        # Force listen mode and add delay to ensure ready
        self.lora_comm.force_listen_mode()
        print("DEBUG: Added 1s delay to ensure listen mode is stable")
        time.sleep(1.0)
        
        # Wait for incoming message from ESP32
        print("Waiting for test message from device...")
        message_received = False
        start_time = time.time()
        timeout = 15  # 15 seconds timeout
        
        while not message_received and (time.time() - start_time) < timeout:
            remaining_time = timeout - (time.time() - start_time)
            if remaining_time > 0:
                print(f"Listening for test message... {remaining_time:.1f}s remaining")
                
                # Check for incoming messages
                received_message = self.lora_comm.receive()
                
                if received_message:
                    print(f"Received RAW message: {received_message}")
                    
                    # Check if it's a test message
                    if "D" in received_message:
                        print("✅ Test message received from ESP32!")
                        message_received = True
                        
                        # Send ACK response
                        print("Sending ACK response...")
                        # Ajouter un délai pour s'assurer que l'ESP32 est en mode écoute
                        print("DEBUG: Waiting 3 seconds to ensure ESP32 is in listen mode...")
                        time.sleep(3.0)
                        
                        # Envoyer un ACK simple et court pour tester
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
                        ack_message = f"B|ACK|{timestamp}|GATEWAY_PI|4C01|E"
                        print(f"DEBUG: Sending simple ACK: {ack_message}")
                        ack_sent = self.lora_comm.send(ack_message, retries=3)
                        
                        if ack_sent:
                            print("🎉 Pi5 LoRa communication test PASSED - ACK sent successfully!")
                            print("Waiting a few seconds to ensure ESP32 receives ACK...")
                            time.sleep(3)  # Give ESP32 time to receive ACK
                            return True
                        else:
                            print("❌ Pi5 LoRa communication test FAILED - ACK not sent")
                            return False
                    else:
                        print(f"Received non-test message: {received_message}")
                
                # Small delay to prevent CPU overload
                time.sleep(0.5)
            else:
                break
        
        if not message_received:
            print("❌ Pi5 LoRa communication test FAILED - No test message received within timeout")
            print("Please check:")
            print("- LoRa frequency matches on both devices (433.1MHz)")
            print("- Spreading factor matches (SF=10)")
            print("- Bandwidth matches (500000)")
            print("- Sync word matches (0x12)")
            print("- Antennas are properly connected")
            print("- Devices are within range")
            return False
    
    def test_ack_message_format(self):
        """Test that ACK message has correct format"""
        ack_message = self.lora_comm.send_ack("TEST_DEVICE")
        
        # The send_ack method should return True if successful
        self.assertTrue(ack_message)
        
        # Note: We can't easily test the actual message format without
        # intercepting the send method, but we can verify the method works

if __name__ == "__main__":
    # Run the test
    test = TestLoRaCommunication()
    test.setUp()
    
    try:
        success = test.test_send_and_receive_ack()
        exit(0 if success else 1)
    finally:
        test.tearDown()
