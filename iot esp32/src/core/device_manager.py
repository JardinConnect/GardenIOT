"""
Device Manager - Complete Facade Implementation
Simple orchestration layer for the entire IoT system following the documented data flow.
"""

from config.config_manager import ConfigManager
from core.hardware_manager import HardwareManager
from core.sensor_manager import SensorManager
from communication.communication_manager import CommunicationManager
from core.event_bus import EventBus
from core.state_manager import StateManager
from core.states import BootState
from managers.alert_manager import AlertManager
from communication.lora_protocol import LoRaProtocol
import time
import gc


class DeviceManager:
    """
    Complete Facade providing simple interface to the entire IoT system.
    """
    
    def __init__(self, config_path="/src/config/config.json"):
        self.config = ConfigManager.get_instance()
        self.config.load(config_path)
        
        self.uid = self.config.get('device.uid', 'ESP32-001')
        
        self.hardware = None
        self.sensors = None
        self.communication = None
        self.alerts = None
        self.event_bus = None
        self.state_manager = None
        self._lora_hw = None
        self._rtc = None
        
        self._running = False
        
        print(f"[DeviceManager] Initialized for device: {self.uid}")
    
    def initialize(self):
        print("[DeviceManager] Starting initialization...")
        
        self._validate_sensor_configurations()

        # 1. Event Bus (Observer Pattern)
        self.event_bus = EventBus()
        
        # 2. Hardware Manager
        self.hardware = HardwareManager(self.config)
        self._initialize_hardware()
        
        # 3. Alert Manager (Observer)
        self.alerts = AlertManager(self.config, self.event_bus)
        
        # 4. Sensor Manager (Factory + Template Method)
        self.sensors = SensorManager(self.config, self.hardware, self.event_bus)
        self.sensors.initialize_sensors()
        
        # 5. Communication Manager (Strategy Pattern)
        self._initialize_communication()
        
        # 6. State Manager (State Pattern)
        self.state_manager = StateManager(self)
        
        gc.collect()
        print(f"[DeviceManager] All components initialized")

    def set_state(self, new_state):
        if self.state_manager:
            self.state_manager.set_state(new_state)
        else:
            print("[DeviceManager] StateManager not initialized")
    
    def _validate_sensor_configurations(self):
        sensors = self.config.get('sensors', [])
        for sensor in sensors:
            if not sensor.get('enabled', False):
                continue
            sensor_name = sensor.get('name', 'unknown')
            codes = sensor.get('codes', {})
            if not codes:
                raise ValueError(
                    f"Sensor '{sensor_name}' is enabled but has no codes defined"
                )
            metrics = list(codes.keys())
            print(f"[DeviceManager] Sensor '{sensor_name}' has metrics: {metrics}")

    def _initialize_hardware(self):
        """Initialize hardware components (called once)."""
        if self._needs_i2c():
            self.hardware.init_i2c()
        
        self._lora_hw = self.hardware.init_lora_hardware()
        self._rtc = self.hardware.init_rtc()
    
    def _initialize_communication(self):
        """Initialize communication protocols (reuses existing hardware)."""
        protocol = LoRaProtocol(
            lora=self._lora_hw,
            uid=self.uid,
            rtc=self._rtc,
            config=self.config.get('lora', {})
        )
        
        self.communication = CommunicationManager(
            primary_strategy=protocol,
            fallback_strategy=None
        )
    
    def run(self):
        print("="*60)
        print("           ESP32 IoT Device - Starting")
        print("="*60)
        
        self._running = True
        self.state_manager.set_state(BootState())
        
        while self._running:
            try:
                self.state_manager.handle()
            except KeyboardInterrupt:
                print("\n[DeviceManager] Stopped by user")
                self._running = False
            except Exception as e:
                print(f"[DeviceManager] Unhandled error: {e}")
                from core.states import ErrorState
                self.state_manager.set_state(ErrorState(error=e))
    
    def run_cycle(self):
        """
        Run one complete cycle: read sensors -> send data -> listen.
        """
        print("\n" + "="*50)
        print("[DeviceManager] Starting cycle...")
        
        # Read all sensors
        sensor_data = self.sensors.read_all_sensors()
        
        # Publish to EventBus (Observer pattern)
        for sensor_name, data in sensor_data.items():
            self.event_bus.publish('sensor.data', {
                'sensor': sensor_name,
                'data': data
            })
        
        # Send data via LoRa
        if sensor_data:
            self._send_sensor_data(sensor_data)
        
        # Listen for incoming messages
        self._listen_for_messages()
    
    def _send_sensor_data(self, sensor_data):
        """Format and send sensor data via LoRa."""
        try:
            payload = self._format_sensor_data(sensor_data)
            
            if not payload:
                print("[DeviceManager] No data to send")
                return False
            
            message = {
                'type': 'D',
                'uid': self.uid,
                'datas': payload
            }
            
            success = self.communication.send(message)
            
            if success:
                print(f"[DeviceManager] Data sent: {payload}")
            else:
                print(f"[DeviceManager] Failed to send data")
            
            return success
        except Exception as e:
            print(f"[DeviceManager] Error sending data: {e}")
            return False
    
    def _format_sensor_data(self, sensor_data):
        """
        Format sensor data to compact string using sensor codes.
        Example output: "TPA:25.3,HMA:60.1,LUX:450"
        """
        formatted_parts = []

        for sensor_name, readings in sensor_data.items():
            try:
                # Get sensor codes from config
                sensor_codes = self.config.get_sensor_codes(sensor_name)
                
                if not sensor_codes:
                    print(f"[DeviceManager] No codes for sensor '{sensor_name}', skipping")
                    continue

                # readings can be: {'data': {'temperature': 25.3}, 'type': 'dht22'}
                # or directly: {'temperature': 25.3, 'humidity': 60}
                data = readings.get('data', readings) if isinstance(readings, dict) else {}

                for metric, value in data.items():
                    if metric in sensor_codes:
                        code = sensor_codes[metric]
                        formatted_parts.append(f"{code}:{value}")

            except Exception as e:
                print(f"[DeviceManager] Format error for '{sensor_name}': {e}")

        return ",".join(formatted_parts)
    
    def _listen_for_messages(self):
        try:
            timeout = self.config.get('device.listen_timeout', 5000)
            message = self.communication.receive(timeout_ms=timeout)
            
            if message:
                self._handle_incoming_message(message)
        except Exception as e:
            print(f"[DeviceManager] Error receiving message: {e}")
    
    def _handle_incoming_message(self, message):
        msg_type = message.get('type')
        from_uid = message.get('uid')
        data = message.get('datas', '')
        
        print(f"[DeviceManager] Message from {from_uid}: {msg_type} - {data}")
        
        self.event_bus.publish('message.received', message)
        
        if msg_type == 'U':
            self._handle_unpair_request()
        elif msg_type == 'A':
            self.alerts.handle_config_message(message)
        elif msg_type == 'C':
            self._handle_command_message(message)
    
    def _handle_unpair_request(self):
        print("[DeviceManager] Unpair request received")
        self.config.set('device.parent_id', None)
        self.config.save()
    
    def _handle_command_message(self, message):
        command = message.get('command', '')
        params = message.get('params', {})
        print(f"[DeviceManager] Command: {command} params: {params}")
        
        if command == 'REBOOT':
            self._reboot_device()
        elif command == 'RESET_CONFIG':
            self._reset_configuration()
    
    def _reboot_device(self):
        print("[DeviceManager] Rebooting...")
        try:
            import machine
            machine.reset()
        except ImportError:
            print("[DeviceManager] machine.reset() not available")
    
    def _reset_configuration(self):
        print("[DeviceManager] Resetting configuration...")
    
    def get_stats(self):
        return {
            'device': {
                'uid': self.uid,
                'state': self.state_manager.get_current_state(),
                'sensors': len(self.sensors.get_all_sensors()),
                'uptime': time.ticks_ms() // 1000
            },
            'communication': self.communication.get_stats(),
            'alerts': self.alerts.get_active_alerts(),
            'memory': self._get_memory_stats()
        }
    
    def _get_memory_stats(self):
        try:
            return {
                'free': gc.mem_free(),
                'allocated': gc.mem_alloc(),
                'total': gc.mem_free() + gc.mem_alloc()
            }
        except Exception:
            return {'error': 'Memory stats not available'}
    
    def stop(self):
        self._running = False
        if self.communication:
            self.communication.disconnect()
        print("[DeviceManager] Device stopped")
    
    def _needs_i2c(self):
        sensors_config = self.config.get('sensors', [])
        return any(s.get('bus') == 'i2c' or s.get('type') in ['bh1750', 'bmp280']
                   for s in sensors_config if s.get('enabled', False))