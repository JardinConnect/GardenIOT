#!/usr/bin/env python3
"""
Main entry point - Uses DeviceManager façade.
This is the complete implementation using the Façade Pattern.
"""

import sys
sys.path.append('/src')  # Ajoute /src au chemin de recherche
sys.path.append('/src/models')


from core.device_manager import DeviceManager

def main():
    """
    Main application using the Façade Pattern.
    All complexity is hidden behind the DeviceManager interface.
    """
    print("="*60)
    print("           ESP32 IoT Device - Main Application")
    print("="*60)
    
    # Create device manager (Façade)
    device = DeviceManager(config_path="/src/config/config.json")    
    
    # Initialize all components
    device.initialize()
    
    # Run the state machine (Boot → Pairing → Active ⇄ Sleep)
    device.run()

def test_mode():
    """
    Test mode: run individual cycles without full state machine.
    Useful for debugging and testing components.
    """
    print("="*60)
    print("           ESP32 IoT Device - Test Mode")
    print("="*60)
    
    # Create device manager (Façade)
    device = DeviceManager(config_path="/src/config/config.json")
    
    # Initialize all components
    device.initialize()
    
    # Run cycles indefinitely
    while True:
        try:
            device.run_cycle()
        except KeyboardInterrupt:
            print("\n[Main] Test mode stopped by user")
            break
        except Exception as e:
            print(f"[Main] Error in test cycle: {e}")
            # Continue to next cycle

if __name__ == "__main__":
    # Choose mode: "normal" or "test"
    MODE = "normal"  # Change to "test" for test mode
    
    if MODE == "test":
        test_mode()
    else:
        main()
