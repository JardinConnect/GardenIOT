# Test LoRa communication with ACK response from Pi5
# Improved version with multiple send attempts and better debugging

import sys
sys.path.append('/src')  # Ajoute /src au chemin de recherche
sys.path.append('/src/models')
import time
from machine import Pin
import network
import ujson
from communication.lora_protocol import LoRaProtocol
from core.hardware_manager import HardwareManager
from communication.communication_manager import CommunicationManager


# Configuration
CONFIG_FILE = "src/config/config.json"

# Load configuration
with open(CONFIG_FILE, "r") as f:
    config = ujson.load(f)

print("=== ESP32 LoRa Communication Test 2 ===")
print(f"Device UID: {config['device']['uid']}")
print(f"LoRa Config: freq={config['lora']['frequency']}MHz, SF={config['lora']['spreading_factor']}, BW={config['lora']['bandwidth']}")

# Initialize hardware manager to get LoRa hardware
hardware_manager = HardwareManager(config)
lora_hw = hardware_manager.init_lora_hardware()

# Get RTC (if available)
rtc = hardware_manager.init_rtc()
print("config =", config["lora"])
# Initialize LoRa protocol with proper parameters
lora_protocol = LoRaProtocol(
    lora=lora_hw,
    uid=config["device"]["uid"],
    rtc=rtc,
    config=config["lora"]
)

# Test function to send message multiple times and wait for ACK
def test_lora_communication():
    print("Starting LoRa communication test...")
    
    max_attempts = 3  # Try sending 3 times
    attempt = 1
    
    while attempt <= max_attempts:
        print(f"\n--- Attempt {attempt}/{max_attempts} ---")
        
        # Send test message (as dictionary format expected by LoRaProtocol)
        test_message = {
            'type': 'D',
            'datas': '1HS24;1TS31'
        }
        print(f"Sending test message: {test_message}")
        print("lora protocol config:", lora_protocol)
        # Send the message (don't wait for ACK here, we'll handle it manually)
        communication = CommunicationManager(
            primary_strategy=lora_protocol,
            fallback_strategy=None
        )
        send_success = communication.send(test_message, expect_ack=False)
        print(f"Message send result: {send_success}")
        
        if not send_success:
            print("Failed to send message")
            attempt += 1
            time.sleep(2)  # Wait before retrying
            continue
        
        # Add delay to ensure we're in receive mode before Pi5 sends ACK
        print("DEBUG: Waiting 2 seconds to ensure in receive mode before ACK...")
        time.sleep(2.0)
        
        # Wait for ACK response
        print("Waiting for ACK response from Pi5...")
        ack_received = False
        start_time = time.time()
        timeout = 8  # 8 seconds timeout per attempt
        
        while not ack_received and (time.time() - start_time) < timeout:
            remaining_time = timeout - (time.time() - start_time)
            print(f"Listening for ACK... {remaining_time:.1f}s remaining")
            
            # Check for incoming messages using polling
            print("DEBUG: Checking for incoming messages using polling...")
            received_message = lora_protocol.receive(2000)  # 2 second timeout
            print(f"DEBUG: lora_protocol.receive() returned: {received_message}")
            
            if received_message:
                print(f"Received message: {received_message}")
                msg_type = received_message.get('type', 'UNKNOWN')
                print(f"Message type: {msg_type}")
                
                # Check if it's an ACK message (accept both 'ACK' and 'PA')
                if msg_type in ['ACK', 'PA']:
                    print("ACK received from Pi5!")
                    print(f"ACK details: {received_message}")
                    ack_received = True
                    break
                else:
                    print(f"Received non-ACK message: {received_message}")
            else:
                print("DEBUG: No message received in this cycle")
            
            # Small delay to prevent busy waiting
            time.sleep(0.5)
        
        if ack_received:
            print("LoRa communication test PASSED - ACK received!")
            return True
        
        attempt += 1
        if attempt <= max_attempts:
            print(f"No ACK received, will retry ({attempt}/{max_attempts})...")
            time.sleep(2)  # Wait before next attempt
    
    print("LoRa communication test FAILED - No ACK received after all attempts")
    return False

if __name__ == "__main__":
    # Run the test
    success = test_lora_communication()
    
    # Clean up
    lora_protocol.disconnect()
    print("[LoRa] Deconnecte")
    
    # MicroPython doesn't have exit(), so we just finish
    # The test result is indicated by the print messages
