"""
Device Manager - Complete Façade Implementation
Simple orchestration layer for the entire IoT system following the documented data flow.
"""

from config.config_manager import ConfigManager
from core.hardware_manager import HardwareManager
from core.sensor_manager import SensorManager
from core.communication_manager import CommunicationManager
from core.event_bus import EventBus
from core.state_manager import StateManager
from core.states import BootState
from managers.alert_manager import AlertManager
from communication.lora_protocol import LoRaProtocol
from communication.wifi_protocol import WiFiProtocol
import time
import gc


class DeviceManager:
    """
    Façade providing simple interface to the entire IoT system.
    Orchestrates specialized managers without implementing details.
    """
    
    def __init__(self, config_path="config/config.json"):
        """
        Initialize the device manager.
        
        Args:
            config_path: path to configuration JSON file
        """
        # Load configuration (Singleton)
        self.config = ConfigManager.get_instance()
        self.config.load(config_path)
        
        # System identity
        self.uid = self.config.get('device.uid', 'ESP32-001')
        
        # Specialized managers (initialized in initialize())
        self.hardware = None
        self.sensors = None
        self.communication = None
        self.alerts = None
        self.event_bus = None
        
        # State Pattern
        self._state = None
        self._running = False
        
        print(f"[DeviceManager] Initialized for device: {self.uid}")
    
    def set_state(self, new_state):
        """
        Transition to a new state (State Pattern).
        Calls exit() on current state and enter() on new state.
        
        Args:
            new_state: DeviceState instance
        """
        if self._state:
            self._state.exit(self)
        
        old_name = self._state.name if self._state else "NONE"
        self._state = new_state
        self._state.enter(self)
        
        print(f"[DeviceManager] State: {old_name} → {self._state.name}")
    
    def run(self):
        """
        Main entry point. Starts the state machine from BootState.
        Loops forever, delegating behavior to the current state.
        """
        print("="*60)
        print("           ESP32 IoT Device - Starting")
        print("="*60)
        
        self._running = True
        self.set_state(BootState())
        
        while self._running:
            try:
                self._state.handle(self)
            
            except KeyboardInterrupt:
                print("\n[DeviceManager] Stopped by user")
                self._running = False
            
            except Exception as e:
                print(f"[DeviceManager] Unhandled error in {self._state.name}: {e}")
                from core.states import ErrorState
                self.set_state(ErrorState(error=e, origin=self._state.name))
    
    def stop(self):
        """Stop the state machine loop"""
        self._running = False
        print("[DeviceManager] Stopping...")
    
    def get_state(self):
        """Get current state name"""
        return self._state.name if self._state else "NONE"
    
    def initialize(self):
        """
        Initialize all system components.
        Call this once at startup.
        """
        print("[DeviceManager] Starting initialization...")
        
        # 1. Event Bus (Observer Pattern) - created first so others can subscribe
        self.event_bus = EventBus()
        
        # 2. Hardware Manager - initializes I2C, SPI, LoRa hardware
        self.hardware = HardwareManager(self.config)
        
        if self._needs_i2c():
            self.hardware.init_i2c()
        
        lora_hw = self.hardware.init_lora_hardware()
        rtc = self.hardware.init_rtc()
        
        # 3. Alert Manager (Observer) - subscribes to events BEFORE sensors start reading
        self.alerts = AlertManager(self.config, self.event_bus)
        
        # 4. Sensor Manager (Factory Pattern) - creates and manages sensors
        self.sensors = SensorManager(self.config, self.hardware, self.event_bus)
        self.sensors.initialize_sensors()
        
        # 5. Communication Manager (Strategy Pattern) - LoRa protocol
        lora_protocol = LoRaProtocol(
            lora=lora_hw,
            uid=self.uid,
            rtc=rtc,
            config=self.config.get('lora', {})
        )
        lora_protocol.connect()
        
        self.communication = CommunicationManager(primary_strategy=lora_protocol)
        
        print(f"[DeviceManager] ✓ All components initialized")
    
    def read_all_sensors(self):
        """
        Read all sensors (delegates to SensorManager).
        SensorManager publishes 'sensor.data' events → AlertManager reacts.
        
        Returns:
            dict: {sensor_name: sensor_data}
        """
        return self.sensors.read_all_sensors()
    
    def send_sensor_data(self, expect_ack=True):
        """
        Read sensors and send data via active communication protocol.
        
        Args:
            expect_ack: wait for acknowledgment
            
        Returns:
            bool: True if sent successfully
        """
        sensor_data = self.read_all_sensors()
        
        if not sensor_data:
            print("[DeviceManager] No sensor data to send")
            return False
        
        payload = self._format_sensor_data(sensor_data)
        
        message = {
            'type': 'D',
            'datas': payload
        }
        
        success = self.communication.send(message, expect_ack=expect_ack)
        
        if success:
            print(f"[DeviceManager] ✓ Data sent: {payload}")
        else:
            print(f"[DeviceManager] ✗ Failed to send data")
        
        return success
    
    def listen_for_messages(self, timeout_ms=5000):
        """
        Listen for incoming messages (delegates to CommunicationManager).
        
        Returns:
            dict or None: received message
        """
        return self.communication.receive(timeout_ms=timeout_ms)
    
    def run_cycle(self):
        """
        Run one full cycle: read sensors → send data → listen for commands.
        Can be used standalone (without State Pattern) for testing.
        """
        print("\n" + "="*50)
        print("[DeviceManager] Starting cycle...")
        
        self.send_sensor_data(expect_ack=True)
        
        timeout = self.config.get('device.listen_timeout', 5000)
        message = self.listen_for_messages(timeout_ms=timeout)
        
        if message:
            self._handle_incoming_message(message)
        
        interval = self.config.get('device.send_interval', 60)
        print(f"[DeviceManager] Sleeping {interval}s until next cycle...")
        time.sleep(interval)
    
    def get_stats(self):
        """Get statistics from all system components"""
        return {
            'device': {
                'uid': self.uid,
                'state': self.get_state(),
                'sensors_count': len(self.sensors.get_all_sensors()) if self.sensors else 0,
                'uptime': time.ticks_ms() // 1000
            },
            'communication': self.communication.get_stats() if self.communication else {},
            'alerts': self.alerts.get_active_alerts() if self.alerts else [],
            'events': {
                'registered': self.event_bus.list_events() if self.event_bus else [],
                'subscribers_total': self.event_bus.get_subscribers_count() if self.event_bus else 0
            }
        }
    
    # ═══════════════════════════════════════════════════════════════
    # PRIVATE METHODS
    # ═══════════════════════════════════════════════════════════════
    
    def _needs_i2c(self):
        """Check if any sensor requires I2C"""
        sensors_config = self.config.get('sensors', [])
        return any(s.get('bus') == 'i2c' or s.get('type') == 'bh1750' 
                   for s in sensors_config if s.get('enabled', False))
    
    def _format_sensor_data(self, sensor_data):
        """
        Format sensor data for transmission.
        Uses SensorData DTO compact format for LoRa communication.
        """
        # sensor_data is now a dict of {sensor_name: SensorData.to_dict()}
        compact_parts = []
        
        for sensor_name, sensor_dict in sensor_data.items():
            # Create SensorData DTO from dict
            from models.sensor_data import SensorData
            dto = SensorData(sensor_dict['sensor'], sensor_dict['type'])
            
            # Add readings from dict
            for reading in sensor_dict.get('readings', []):
                dto.add_reading(reading['metric'], reading['value'], reading['unit'])
            
            # Use compact format for LoRa
            compact_data = dto.to_compact()
            
            # Format as "code:value,code:value,..."
            parts = []
            for code, value in compact_data.items():
                if code not in ['s', 't']:  # Skip sensor name and timestamp
                    parts.append(f"{code}:{value}")
            
            if parts:
                compact_parts.extend(parts)
        
        return ",".join(compact_parts)
    
    def _get_sensor_config(self, sensor_name):
        """Get config for a specific sensor by name"""
        sensors = self.config.get('sensors', [])
        for s in sensors:
            if s.get('name') == sensor_name:
                return s
        return {}
    
    def _handle_incoming_message(self, message):
        """Handle received LoRa message by publishing to EventBus"""
        msg_type = message.get('type')
        from_uid = message.get('uid')
        data = message.get('datas', '')
        
        print(f"[DeviceManager] Message from {from_uid}: {msg_type} - {data}")
        
        # Publish to EventBus so any subscriber can react
        self.event_bus.publish('message.received', message)