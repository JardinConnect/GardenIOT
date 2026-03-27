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
from core.states import BootState, PairingState, ActiveState
from alert.alert_manager import AlertManager
from communication.lora_protocol import LoRaProtocol
from machine import Pin
import esp32
import ubinascii
import machine
import time
import gc


class DeviceManager:
    """
    Complete Facade providing simple interface to the entire IoT system.
    """
    
    def __init__(self, config_path="/src/config/config.json"):
        self.config = ConfigManager.get_instance()
        self.config.load(config_path)
        print(f"[DeviceManager] Configuration loaded {self.config.get('lora')}")
        self.uid = ubinascii.hexlify(machine.unique_id()).decode()
        self.config.set("device.uid", self.uid)
        self.config.save()
        
        self.hardware = None
        self.sensors = None
        self.communication = None
        self.alerts = None
        self.event_bus = None
        self.state_manager = None
        self._lora_hw = None
        self._rtc = None
        self.protocol = None
        
        self._running = False
        self._wake_message = None
        
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
        
        # 7. Subscribe to incoming message events dispatched by CommunicationManager
        self.event_bus.subscribe('communication.send_failed', self._on_send_failed)
        self.event_bus.subscribe('message.received.U', self._handle_unpair_request)
        self.event_bus.subscribe('message.received.S', self._handle_status_message)
        self.event_bus.subscribe('message.received.C', self._handle_command_message)
        
        gc.collect()
        print(f"[DeviceManager] All components initialized")
    
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
        self._lora_hw = self.hardware.init_lora_hardware()
        print(f"[DeviceManager] LORA hardware {self._lora_hw} initialized")
        self._rtc = self.hardware.init_rtc()
        self._btn = self.hardware.init_btn()
        self._pairing_requested = False
        self._last_btn_time = 0
        self._setup_button_irq()

    def _setup_button_irq(self):
        """Configure button interrupt: sets flag only (safe in IRQ context)."""
        def _on_button_press(pin):
            now = time.ticks_ms()
            if time.ticks_diff(now, self._last_btn_time) > 300:
                self._last_btn_time = now
                self._pairing_requested = True

        # IRQ for normal operation (when CPU is awake)
        self._btn.irq(trigger=Pin.IRQ_FALLING, handler=_on_button_press)
        # Wake source for lightsleep (persists across all lightsleep calls)
        esp32.wake_on_ext0(self._btn, esp32.WAKEUP_ALL_LOW)
    
    def _initialize_communication(self):
        """Initialize communication protocols (reuses existing hardware)."""
        print(f"[DeviceManager] Initializing communication protocol... {self.config.get('lora')}")
        protocol = LoRaProtocol(
            lora=self._lora_hw,
            uid=self.uid,
            rtc=self._rtc,
            config=self.config.get('lora', {})
        )

        self.protocol = protocol
        
        self.communication = CommunicationManager(
            primary_strategy=protocol,
            fallback_strategy=None,
            event_bus=self.event_bus,
            rtc=self._rtc,
            config=self.config
        )

    def set_state(self, new_state):
        if self.state_manager:
            self.state_manager.set_state(new_state)
        else:
            print("[DeviceManager] StateManager not initialized")
    
    
    def run(self):
        print("="*60)
        print("           ESP32 IoT Device - Starting")
        print("="*60)
        
        self._running = True
        self.state_manager.set_state(BootState())
        
        while self._running:
            try:
                # Check button flag (set by IRQ, checked here in main context)
                if self._pairing_requested:
                    self._pairing_requested = False
                    if not isinstance(self.state_manager.current_state, PairingState):
                        print("[DeviceManager] Button pressed - switching to pairing")
                        self.state_manager.set_state(PairingState())

                # Dispatch wake message saved by SleepState through normal event bus
                if self._wake_message:
                    msg = self._wake_message
                    self._wake_message = None
                    print(f"[DeviceManager] Dispatching wake message: type={msg.get('type')}")
                    self.communication._handle_incoming(msg)

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
        Run one complete cycle: read sensors and publish data to event bus.
        Communication layer handles message creation and sending based on events.
        """
        print("\n" + "="*50)
        print("[DeviceManager.run_cycle] NEW ENTRY - Starting ACTIVE cycle")

        # 1. Read sensors and publish to event bus
        print("[DeviceManager.run_cycle] Reading sensors...")
        timestamp = self._get_timestamp()
        sensor_data = self.sensors.read_all_sensors(timestamp)
        print(f"[DeviceManager.run_cycle] Sensor data: {sensor_data}")

        # 2. Check for alerts
        alerts_to_send = self.alerts.get_alerts_to_send()
        if alerts_to_send:
            print(f"[DeviceManager.run_cycle] Alerts to send: {alerts_to_send}")
            # Publish alert event (CommunicationManager will handle sending)
            self.event_bus.publish('alert.triggered', alerts_to_send)

        # 3. Publish sensor data event (CommunicationManager will handle sending)
        if sensor_data:
            self.event_bus.publish('sensor.data.ready', {
                'data': sensor_data,
                'timestamp': timestamp,
                'type': 'D'
            })
            print("[DeviceManager.run_cycle] Sensor data published to event bus")
        else:
            print("[DeviceManager.run_cycle] No valid sensor data to publish")

        # 4. Go back to listening
        self.communication.receive(timeout_ms=1)
        print("[DeviceManager.run_cycle] EXIT - Cycle completed")

    def _get_timestamp(self):
        """
        Get current timestamp from RTC (fallback to time.localtime if RTC unavailable).
        Returns:
            str: ISO 8601 timestamp (e.g., "2023-11-15T14:30:00Z")
        """
        if self._rtc:
            try:
                # Lire le RTC (format: (year, month, day, weekday, hour, minute, second, microsecond))
                dt = self._rtc.datetime()
                return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
                    dt[0], dt[1], dt[2], dt[4], dt[5], dt[6]
                )
            except Exception as e:
                print(f"[DeviceManager] RTC error: {e}")

        # Fallback: utiliser time.localtime (moins précis)
        t = time.localtime()
        return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
            t[0], t[1], t[2], t[3], t[4], t[5]
        )
    
    def _handle_unpair_request(self, message=None):
        print("[DeviceManager] Unpair request received")
        self.config.set('device.parent_id', None)
        self.config.save()

    def _handle_status_message(self, message):
        print(f"[DeviceManager] Status message received: {message}")

    def _handle_command_message(self, message):
        command = message.get('data', '')
        params = message.get('params', {})
        print(f"[DeviceManager] Command: {command} params: {params}")
        
        if command == 'REBOOT':
            self._reboot_device()
        elif command == 'IA':
            print("[DeviceManager] Instant analytics requested - forcing send")
            self.communication._force_send = True
            if not isinstance(self.state_manager.current_state, ActiveState):
                self.state_manager.set_state(ActiveState())
        elif command == 'RESET_CONFIG':
            self._reset_configuration()
        else:
            print(f"[DeviceManager] Unknown command: {command}")
    
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

    def _on_send_failed(self, payload):
        """Callback quand l'envoi a échoué après 3 tentatives."""
        count = payload.get('count', 0) if isinstance(payload, dict) else 0
        print(f"[DeviceManager._on_send_failed] Send failed after 3 attempts ({count} messages lost)")

    def _needs_i2c(self):
        sensors_config = self.config.get('sensors', [])
        return any(s.get('bus') == 'i2c' or s.get('type') in ['bh1750', 'bmp280']
                   for s in sensors_config if s.get('enabled', False))