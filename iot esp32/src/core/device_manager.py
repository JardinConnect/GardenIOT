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
    Complete Façade providing simple interface to the entire IoT system.
    Follows the documented data flow:
    main.py → DeviceManager → [Config, Sensors, Communication, Alerts]
    """
    
    def __init__(self, config_path="config/config.json"):
        """
        Initialize the device manager with configuration.
        """
        # Load configuration (Singleton)
        self.config = ConfigManager.get_instance()
        self.config.load(config_path)
        
        # System identity
        self.uid = self.config.get('device.uid', 'ESP32-001')
        
        # Component managers (initialized in initialize())
        self.hardware = None
        self.sensors = None
        self.communication = None
        self.alerts = None
        self.event_bus = None
        self.state_manager = None
        
        # Current state
        self._running = False
        
        print(f"[DeviceManager] Initialized for device: {self.uid}")
    
    def initialize(self):
        """
        Initialize all system components following the documented architecture.
        """
        print("[DeviceManager] Starting initialization...")
        
        self._validate_sensor_configurations()

        # 1. Event Bus (Observer Pattern) - First for subscriptions
        self.event_bus = EventBus()
        
        # 2. Hardware Manager - Low-level hardware initialization
        self.hardware = HardwareManager(self.config)
        self._initialize_hardware()
        
        # 3. Alert Manager (Observer) - Subscribe before sensors start
        self.alerts = AlertManager(self.config, self.event_bus)
        
        # 4. Sensor Manager (Factory + Template Method)
        self.sensors = SensorManager(self.config, self.hardware, self.event_bus)
        self.sensors.initialize_sensors()
        
        # 5. Communication Manager (Strategy Pattern)
        self._initialize_communication()
        
        # 6. State Manager (State Pattern)
        self.state_manager = StateManager(self)
        
        # Memory cleanup
        gc.collect()
        
        print(f"[DeviceManager] ✓ All components initialized")
    
    def _validate_sensor_configurations(self):
        """Validate sensor configurations - now much simpler!"""
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

            # Get list of metrics from codes keys
            metrics = list(codes.keys())
            print(f"[DeviceManager] ✓ Sensor '{sensor_name}' has metrics: {metrics}")

    def _initialize_hardware(self):
        """Initialize hardware components based on configuration."""
        if self._needs_i2c():
            self.hardware.init_i2c()
        
        lora_hw = self.hardware.init_lora_hardware()
        rtc = self.hardware.init_rtc()
        
        return lora_hw, rtc
    
    def _initialize_communication(self):
        """Initialize communication protocols."""
        comm_config = self.config.get('communication', {})
        comm_type = comm_config.get('type', 'lora')
        
        if comm_type == 'lora':
            lora_hw, rtc = self._initialize_hardware()
            protocol = LoRaProtocol(
                lora=lora_hw,
                uid=self.uid,
                rtc=rtc,
                config=self.config.get('lora', {})
            )
        else:
            protocol = WiFiProtocol(self.config.get('wifi', {}))
        
        # Initialize fallback protocol if configured
        fallback_protocol = None
        if comm_config.get('fallback_enabled', False):
            fallback_type = comm_config.get('fallback_type', 'wifi')
            if fallback_type == 'wifi':
                fallback_protocol = WiFiProtocol(self.config.get('wifi', {}))
        
        self.communication = CommunicationManager(
            primary_strategy=protocol,
            fallback_strategy=fallback_protocol
        )
    
    def run(self):
        """
        Main entry point. Starts the state machine from BootState.
        """
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
        Run one complete cycle: read sensors → process → send data → listen.
        Can be used for testing without full state machine.
        """
        print("\n" + "="*50)
        print("[DeviceManager] Starting cycle...")
        
        # Read all sensors (uses Factory + Template Method patterns)
        sensor_data = self.sensors.read_all_sensors()
        
        # Publish to EventBus (Observer pattern)
        for sensor_name, data in sensor_data.items():
            self.event_bus.publish('sensor.data', {
                'sensor': sensor_name,
                'data': data
            })
        
        # Send data via CommunicationManager (Strategy pattern)
        if sensor_data:
            self._send_sensor_data(sensor_data)
        
        # Listen for incoming messages
        self._listen_for_messages()
        
        # Sleep until next cycle
        self._sleep_until_next_cycle()
    
    def _send_sensor_data(self, sensor_data):
        """Send sensor data using the active communication strategy."""
        try:
            # Format data for transmission
            payload = self._format_sensor_data(sensor_data)
            
            message = {
                'type': 'D',  # Data message
                'uid': self.uid,
                'datas': payload
            }
            
            success = self.communication.send(message)
            
            if success:
                print(f"[DeviceManager] ✓ Data sent successfully")
            else:
                print(f"[DeviceManager] ✗ Failed to send data")
            
            return success
        except Exception as e:
            print(f"[DeviceManager] Error sending data: {e}")
            return False
    
    def _listen_for_messages(self):
        """Listen for incoming LoRa messages."""
        try:
            timeout = self.config.get('device.listen_timeout', 5000)
            message = self.communication.receive(timeout_ms=timeout)
            
            if message:
                self._handle_incoming_message(message)
        except Exception as e:
            print(f"[DeviceManager] Error receiving message: {e}")
    
    def _handle_incoming_message(self, message):
        """Handle received LoRa message by publishing to EventBus."""
        msg_type = message.get('type')
        from_uid = message.get('uid')
        data = message.get('datas', '')
        
        print(f"[DeviceManager] Message from {from_uid}: {msg_type} - {data}")
        
        # Publish to EventBus so any subscriber can react
        self.event_bus.publish('message.received', message)
        
        # Handle specific message types
        if msg_type == 'U':  # Unpair
            self._handle_unpair_request()
        elif msg_type == 'A':  # Alert config
            self.alerts.handle_config_message(message)
        elif msg_type == 'C':  # Command
            self._handle_command_message(message)
    
    def _handle_unpair_request(self):
        """Handle unpairing request."""
        print("[DeviceManager] Unpair request received")
        self.config.set('device.parent_id', None)
        self.config.save()
        # State manager will handle transition to pairing state
    
    def _handle_command_message(self, message):
        """Handle command messages."""
        command = message.get('command', '')
        params = message.get('params', {})
        
        print(f"[DeviceManager] Command received: {command} with params: {params}")
        
        if command == 'REBOOT':
            self._reboot_device()
        elif command == 'RESET_CONFIG':
            self._reset_configuration()
    
    def _format_sensor_data(self, sensor_data):
        """
        Format sensor data - now simpler without metrics array.
        """
        formatted_parts = []

        for sensor_name, metrics in sensor_data.items():
            try:
                # Get sensor codes from ConfigManager
                sensor_codes = self.config.get_sensor_codes(sensor_name)

                # Create DTO
                dto = SensorData(sensor_name, metrics.get('type', 'unknown'))

                # Add readings (metrics come from the actual sensor data)
                for metric, value in metrics.get('data', {}).items():
                    if metric in sensor_codes:  # Only include metrics that have codes
                        unit = metrics.get('units', {}).get(metric, '')
                        dto.add_reading(metric, value, unit)

                # Convert to compact format
                compact_data = dto.to_compact(codes=sensor_codes)

                # Format payload
                for code, value in compact_data.items():
                    if code not in ['s', 't']:
                        formatted_parts.append(f"{code}:{value}")

            except ValueError as e:
                print(f"[DeviceManager] Error: {e}")

        return ",".join(formatted_parts)
    
    def _sleep_until_next_cycle(self):
        """Sleep until next send interval."""
        interval = self.config.get('device.send_interval', 60)
        print(f"[DeviceManager] Sleeping {interval}s until next cycle...")
        time.sleep(interval)
    
    def _reboot_device(self):
        """Reboot the device."""
        print("[DeviceManager] Rebooting device...")
        try:
            import machine
            machine.reset()
        except ImportError:
            print("[DeviceManager] machine.reset() not available")
    
    def _reset_configuration(self):
        """Reset configuration to defaults."""
        print("[DeviceManager] Resetting configuration...")
        # Implementation depends on your requirements
        # Could load default config or wipe specific settings
    
    def get_stats(self):
        """Get system statistics."""
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
        """Get memory usage statistics."""
        try:
            import gc
            return {
                'free': gc.mem_free(),
                'allocated': gc.mem_alloc(),
                'total': gc.mem_free() + gc.mem_alloc()
            }
        except ImportError:
            return {'error': 'Memory stats not available'}
    
    def stop(self):
        """Stop the device gracefully."""
        self._running = False
        if self.communication:
            self.communication.disconnect()
        print("[DeviceManager] Device stopped gracefully")
    
    def _needs_i2c(self):
        """Check if any sensor requires I2C."""
        sensors_config = self.config.get('sensors', [])
        return any(s.get('bus') == 'i2c' or s.get('type') in ['bh1750', 'bmp280']
                   for s in sensors_config if s.get('enabled', False))
