"""
Main entry point - Example usage of DeviceManager façade.
This demonstrates how the entire system is orchestrated.
"""

from core.device_manager import DeviceManager
import time


def main():
    """
    Main application with State Pattern.
    BootState → PairingState → ActiveState ⇄ SleepState
    """
    device = DeviceManager(config_path="config/config.json")
    
    # run() starts the state machine: BOOT → PAIRING → ACTIVE ⇄ SLEEP
    # Everything is handled by states, including error recovery
    device.run()


def test_sensors_only():
    """
    Test mode: only read sensors without LoRa communication.
    Useful for debugging sensors.
    """
    print("="*60)
    print("           Sensor Test Mode")
    print("="*60)
    
    device = DeviceManager(config_path="config/config.json")
    device.initialize()
    
    while True:
        try:
            print("\n--- Reading Sensors ---")
            data = device.read_all_sensors()
            
            for sensor_name, metrics in data.items():
                print(f"\n{sensor_name}:")
                for metric, value in metrics.items():
                    print(f"  {metric}: {value}")
            
            time.sleep(10)
        
        except KeyboardInterrupt:
            break


def test_lora_only():
    """
    Test mode: test LoRa communication only.
    """
    print("="*60)
    print("           LoRa Test Mode")
    print("="*60)
    
    device = DeviceManager(config_path="config/config.json")
    device.initialize()
    
    # Test send
    test_message = {
        'type': 'TEST',
        'datas': 'Hello from ESP32'
    }
    
    print("\nSending test message...")
    success = device.protocol.send(test_message, expect_ack=True)
    
    if success:
        print("Message sent successfully (ACK received)")
    else:
        print("Message send failed (no ACK)")
    
    # Test receive
    print("\nListening for messages (10s)...")
    message = device.listen_for_messages(timeout_ms=10000)
    
    if message:
        print(f"Message received: {message}")
    else:
        print("No message received")
    
    # Show stats
    print("\nLoRa Statistics:")
    stats = device.protocol.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


# Entry point
if __name__ == "__main__":
    # Choose mode
    MODE = "normal"  # Options: "normal", "sensors", "lora"
    
    if MODE == "sensors":
        test_sensors_only()
    elif MODE == "lora":
        test_lora_only()
    else:
        main()
