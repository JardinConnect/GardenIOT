#!/usr/bin/env python3
"""
Test script for the complete Façade Pattern implementation.
Tests the DeviceManager façade without hardware dependencies.
"""

import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_facade_initialization():
    """Test DeviceManager façade initialization."""
    print("Testing DeviceManager façade initialization...")
    
    try:
        from core.device_manager_complete import DeviceManager
        
        # Create device manager
        device = DeviceManager(config_path="src/config/config.json")
        
        print(f"  [OK] DeviceManager created successfully")
        print(f"  [OK] Device UID: {device.uid}")
        print(f"  [OK] Config loaded: {device.config is not None}")
        
        # Test initialization
        device.initialize()
        
        print(f"  [OK] All components initialized")
        print(f"  [OK] EventBus: {device.event_bus is not None}")
        print(f"  [OK] Hardware: {device.hardware is not None}")
        print(f"  [OK] Sensors: {device.sensors is not None}")
        print(f"  [OK] Communication: {device.communication is not None}")
        print(f"  [OK] Alerts: {device.alerts is not None}")
        print(f"  [OK] State Manager: {device.state_manager is not None}")
        
        return True
        
    except Exception as e:
        print(f"  [ERROR] Initialization failed: {e}")
        return False

def test_facade_methods():
    """Test DeviceManager façade methods."""
    print("\nTesting DeviceManager façade methods...")
    
    try:
        from core.device_manager_complete import DeviceManager
        
        device = DeviceManager(config_path="src/config/config.json")
        device.initialize()
        
        # Test get_state
        state = device.get_state()
        print(f"  [OK] get_state() returned: {state}")
        
        # Test get_stats
        stats = device.get_stats()
        print(f"  [OK] get_stats() returned: {len(stats)} sections")
        
        # Test stop
        device.stop()
        print(f"  [OK] stop() executed successfully")
        
        return True
        
    except Exception as e:
        print(f"  [ERROR] Method testing failed: {e}")
        return False

def test_state_manager():
    """Test StateManager integration."""
    print("\nTesting StateManager integration...")
    
    try:
        from core.device_manager_complete import DeviceManager
        from core.states import BootState
        
        device = DeviceManager(config_path="src/config/config.json")
        device.initialize()
        
        # Test state management
        initial_state = device.state_manager.get_current_state()
        print(f"  [OK] Initial state: {initial_state}")
        
        # Test state transition
        from core.states import ActiveState
        device.state_manager.set_state(ActiveState())
        new_state = device.state_manager.get_current_state()
        print(f"  [OK] State transition: {initial_state} → {new_state}")
        
        return True
        
    except Exception as e:
        print(f"  [ERROR] State manager testing failed: {e}")
        return False

def test_dto_integration():
    """Test DTO integration in façade."""
    print("\nTesting DTO integration...")
    
    try:
        from models.sensor_data import SensorData, SensorReading
        
        # Create test DTO
        dto = SensorData("test_sensor", "TestType")
        dto.add_reading("temperature", 25.5, "°C")
        dto.add_reading("humidity", 60.0, "%")
        
        print(f"  [OK] DTO created: {dto}")
        print(f"  [OK] Full format: {dto.to_dict()}")
        print(f"  [OK] Compact format: {dto.to_compact()}")
        
        return True
        
    except Exception as e:
        print(f"  [ERROR] DTO integration failed: {e}")
        return False

def main():
    """Run all tests."""
    print("="*60)
    print("           Facade Pattern Implementation Tests")
    print("="*60)
    
    tests = [
        test_facade_initialization,
        test_facade_methods,
        test_state_manager,
        test_dto_integration
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "="*60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"           [SUCCESS] All {total} tests passed!")
    else:
        print(f"           [FAILED] {passed}/{total} tests passed")
    
    print("="*60)

if __name__ == "__main__":
    main()
