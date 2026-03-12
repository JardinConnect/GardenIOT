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
        print(f"[DeviceManager] Configuration loaded {self.config.get('lora')}")
        self.uid = self.config.get('device.uid', 'ESP32-001')
        
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
        self._lora_hw = self.hardware.init_lora_hardware()
        print(f"[DeviceManager] LORA hardware {self._lora_hw} initialized")
        self._rtc = self.hardware.init_rtc()
    
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
        Run one complete cycle: read sensors -> send data -> listen for ACK.
        Simplified version based on working test.
        """
        print("\n" + "="*50)
        print("[DeviceManager.run_cycle] NEW ENTRY - Starting ACTIVE cycle")

        # 1. Read sensors
        print("[DeviceManager.run_cycle] Reading sensors...")
        sensor_data = self.sensors.read_all_sensors()
        print(f"[DeviceManager.run_cycle] Sensor data: {sensor_data}")

        # 2. Format data
        payload = self._format_sensor_data(sensor_data)
        if not payload or payload == "NO_DATA":
            print("[DeviceManager.run_cycle] No valid data to send")
            return

        # 3. Prepare message
        message = {'type': 'D', 'datas': payload}
        print(f"[DeviceManager.run_cycle] Sending message ack test: {message}")

        # SEND WITH ACK
        send_success = self.communication.send(message, expect_ack=True)
        if not send_success:
            print("[DeviceManager.run_cycle] Failed to send message")
            return

        # 5. Listen for other messages
        print("[DeviceManager.run_cycle] Listening for messages...")
        self._listen_for_messages()

        print("[DeviceManager.run_cycle] EXIT - Cycle completed")

    def _format_sensor_data(self, sensor_data):
        """
        Format sensor data to compact string.
        Format: 1TA32;1TS25;1HA45;1HS40;1L200;1B97
        
        Structure per value: {index}{code}{value}
        - index: 1
        - code: TA, TS, HA, HS, L, etc.
        - value: integer (rounded)
        """
        print("[DeviceManager._format_sensor_data] ENTRY")
        formatted_parts = []

        for sensor_name, readings in sensor_data.items():
            try:
                sensor_codes = self.config.get_sensor_codes(sensor_name)
                
                if not sensor_codes:
                    print(f"[DeviceManager._format_sensor_data] No codes for sensor '{sensor_name}', skipping")
                    continue

                # Extract data from readings
                if isinstance(readings, dict):
                    data = readings.get('data', readings)
                    # Handle nested format from SensorData.to_dict()
                    if 'readings' in data:
                        # Format: {'readings': [{'metric': 'temperature', 'value': 25.3}]}
                        values = {}
                        for r in data['readings']:
                            values[r['metric']] = r['value']
                        data = values
                    elif 'readings' in readings:  # Alternative format
                        values = {}
                        for r in readings['readings']:
                            values[r['metric']] = r['value']
                        data = values
                else:
                    continue

                for metric, value in data.items():
                    if metric in sensor_codes:
                        code = sensor_codes[metric]
                        # Round to integer, prefix with priority "1"
                        try:
                            int_value = int(round(float(value)))
                            formatted_parts.append(f"1{code}{int_value}")
                            print(f"[DeviceManager._format_sensor_data] Formatted {sensor_name}.{metric}: {code}{int_value}")
                        except (ValueError, TypeError) as e:
                            print(f"[DeviceManager._format_sensor_data] Invalid value for {sensor_name}.{metric}: {value} ({e})")

            except Exception as e:
                print(f"[DeviceManager._format_sensor_data] Format error for '{sensor_name}': {e}")

        if not formatted_parts:
            print("[DeviceManager._format_sensor_data] No valid sensor data to format")
            return "NO_DATA"
        
        result = ";".join(formatted_parts)
        print(f"[DeviceManager._format_sensor_data] EXIT - Formatted payload: {result}")
        return result

    
    def _listen_for_messages(self):
        print("[DeviceManager._listen_for_messages] ENTRY")
        try:
            timeout = self.config.get('device.listen_timeout', 5000)
            print(f"[DeviceManager._listen_for_messages] Waiting for messages (timeout: {timeout}ms)")
            message = self.communication.receive(timeout_ms=timeout)
            
            if message:
                print(f"[DeviceManager._listen_for_messages] Message received: {message}")
                self._handle_incoming_message(message)
            else:
                print("[DeviceManager._listen_for_messages] No message received")
        except Exception as e:
            print(f"[DeviceManager._listen_for_messages] Error: {e}")
        print("[DeviceManager._listen_for_messages] EXIT")
    
    def _handle_incoming_message(self, message):
        print("[DeviceManager._handle_incoming_message] ENTRY")
        
        if not message:
            print("[DeviceManager._handle_incoming_message] Empty message received")
            return
        
        msg_type = message.get('type')
        from_uid = message.get('uid')
        data = message.get('datas', '')
        
        print(f"[DeviceManager._handle_incoming_message] Message from {from_uid}: {msg_type} - {data}")
        
        # Vérification 1: Le message est-il pour nous? (pour les ACK)
        if msg_type in ['ACK', 'PA']:
            # Format attendu pour ACK: B|ACK|timestamp|gateway_uid|device_uid|E
            # Donc le champ 'uid' devrait être notre UID
            if from_uid != self.uid:
                print(f"[DeviceManager._handle_incoming_message] ACK not for us (expected {self.uid}, got {from_uid})")
                return
            
            print("[DeviceManager._handle_incoming_message] ACK received - data sent successfully")
            # Pas besoin de publier sur EventBus pour les ACK
            print("[DeviceManager._handle_incoming_message] EXIT")
            return
        
        # Vérification 2: Le message vient-il d'une source autorisée?
        if not self._is_trusted_sender(from_uid):
            print(f"[DeviceManager._handle_incoming_message] Untrusted sender: {from_uid}")
            return
        
        # Publier sur EventBus (Observer pattern)
        self.event_bus.publish('message.received', message)
        print("[DeviceManager._handle_incoming_message] Published to EventBus")
        
        # Traiter selon le type de message
        if msg_type == 'U':  # Unpair
            print("[DeviceManager._handle_incoming_message] Handling unpair request")
            self._handle_unpair_request()
            
        elif msg_type == 'A':  # Alert config
            print("[DeviceManager._handle_incoming_message] Handling alert config")
            self.alerts.handle_config_message(message)
            
        elif msg_type == 'C':  # Command
            print("[DeviceManager._handle_incoming_message] Handling command")
            self._handle_command_message(message)
            
        elif msg_type == 'D':  # Data (ne devrait pas arriver ici normalement)
            print("[DeviceManager._handle_incoming_message] Received data message (unexpected)")
            
        else:
            print(f"[DeviceManager._handle_incoming_message] Unknown message type: {msg_type}")
            self.event_bus.publish('message.unknown', message)
        
        print("[DeviceManager._handle_incoming_message] EXIT")
    
    def _is_trusted_sender(self, sender_uid):
        """
        Vérifie si l'expéditeur est autorisé à nous envoyer des messages.
        
        Args:
            sender_uid: UID de l'expéditeur
            
        Returns:
            True si l'expéditeur est autorisé, False sinon
        """
        print(f"[DeviceManager._is_trusted_sender] Checking sender: {sender_uid}")
        
        # Le gateway parent est toujours autorisé
        parent_id = self.config.get('device.parent_id')
        if parent_id and sender_uid == parent_id:
            print(f"[DeviceManager._is_trusted_sender] Sender is parent gateway: {sender_uid}")
            return True
        
        # Le gateway par défaut (GATEWAY_PI) est aussi autorisé
        if sender_uid == "GATEWAY_PI":
            print(f"[DeviceManager._is_trusted_sender] Sender is default gateway: {sender_uid}")
            return True
        
        # Autres règles de confiance peuvent être ajoutées ici
        # Par exemple: liste blanche d'UIDs, etc.
        
        print(f"[DeviceManager._is_trusted_sender] Sender not trusted: {sender_uid}")
        return False
    
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