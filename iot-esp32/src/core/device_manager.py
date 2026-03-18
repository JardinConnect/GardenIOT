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
        
        # 7. Cycle management
        self.cycle_active = False
        self.ack_received = False
        
        # Subscribe to ACK events
        self.event_bus.subscribe('ack.received', self._on_ack_received)
        
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
        Run one complete cycle: read sensors -> send data -> listen for ACK/messages.
        Listens continuously for 10s or until ACK is received (whichever comes first).
        """
        print("\n" + "="*50)
        print("[DeviceManager.run_cycle] NEW ENTRY - Starting ACTIVE cycle")

        # 1. Read sensors
        print("[DeviceManager.run_cycle] Reading sensors...")
        sensor_data = self.sensors.read_all_sensors()
        print(f"[DeviceManager.run_cycle] Sensor data: {sensor_data}")

        # 2. Create payload
        payload = self.create_payload(sensor_data, message_type="D")
        if not payload or payload == "NO_DATA":
            print("[DeviceManager.run_cycle] No valid data to send")
            return

        # 3. Send data (simple send, no complex ACK logic in protocol)
        print("[DeviceManager.run_cycle] Sending data...")
        send_success = self.communication.send(payload, expect_ack=False)
        if not send_success:
            print("[DeviceManager.run_cycle] Failed to send message")
            return

        # 4. Listen continuously for ACK or other messages (10s timeout)
        print("[DeviceManager.run_cycle] Waiting for ACK and listening for messages...")
        self._listen_continuously(duration_ms=10000)
        
        if self.ack_received:
            print("[DeviceManager.run_cycle] ACK received - cycle completed successfully")
        else:
            print("[DeviceManager.run_cycle] No ACK received within timeout")

        print("[DeviceManager.run_cycle] EXIT - Cycle completed")

    def create_payload(self, sensor_data, message_type="D"):
        """
        Create a generic payload with all required data.
        Args:
            sensor_data: Raw sensor data from SensorManager
            message_type: Type of message (e.g., "D" for data)
        Returns:
            dict: {
                "type": "D",
                "uid": "device_uid",
                "timestamp": 1234567890,
                "data": {"1TA": 25, "1HA": 45, ...}
            }
        """
        if not sensor_data:
            return None

        # Get timestamp from RTC (fallback to time if unavailable)
        timestamp = self._get_timestamp()  # Méthode à ajouter

        # Fusionner les données de tous les capteurs
        merged_data = {}
        for sensor_data in sensor_data.values():
            merged_data.update(sensor_data)

        # Arrondir les valeurs et convertir en int
        formatted_data = {}
        for key, value in merged_data.items():
            try:
                formatted_data[key] = int(round(float(value)))
            except (ValueError, TypeError):
                continue

        return {
            "type": message_type,
            "timestamp": timestamp,
            "data": formatted_data
        }

    
    def _listen_continuously(self, duration_ms=10000):
        """
        Écoute les messages en continu pendant une durée donnée ou jusqu'à réception d'ACK
        """
        print(f"[DeviceManager._listen_continuously] Starting continuous listen for {duration_ms}ms")
        self.cycle_active = True
        self.ack_received = False
        
        start_time = time.ticks_ms()
        
        while self.cycle_active and (time.ticks_diff(time.ticks_ms(), start_time) < duration_ms):
            try:
                # Écouter les messages avec un timeout court pour permettre une vérification fréquente
                message = self.communication.receive(timeout_ms=500)
                
                if message:
                    print(f"[DeviceManager._listen_continuously] Message received: {message}")
                    self._handle_incoming_message(message)
                
                # Vérifier si on a reçu un ACK pour sortir de la boucle
                if self.ack_received:
                    print("[DeviceManager._listen_continuously] ACK received, stopping listen")
                    break
                    
            except Exception as e:
                print(f"[DeviceManager._listen_continuously] Error: {e}")
                time.sleep(0.1)
        
        print("[DeviceManager._listen_continuously] Listen completed")
    
    def _handle_incoming_message(self, message):
        print("[DeviceManager._handle_incoming_message] ENTRY")
        
        if not message:
            print("[DeviceManager._handle_incoming_message] Empty message received")
            return
        
        msg_type = message.get('type')
        device_uid = message.get('uid')
        data = message.get('datas', '')
        
        print(f"[DeviceManager._handle_incoming_message] Message for {device_uid}: {msg_type} - {data}")
        
        # Vérification 1: Le message est-il pour nous? (pour les ACK)
        if msg_type in ['ACK', 'PA']:
            # Format attendu pour ACK: B|ACK|timestamp|gateway_uid|device_uid|E
            # Donc le champ 'uid' devrait être notre UID
            if device_uid != self.uid:
                print(f"[DeviceManager._handle_incoming_message] ACK not for us (expected {self.uid}, got {device_uid})")
                return
            
            print("[DeviceManager._handle_incoming_message] ACK received - data sent successfully")
            # Publier l'événement ACK pour notifier que le cycle peut se terminer
            self.event_bus.publish('ack.received', message)
            print("[DeviceManager._handle_incoming_message] EXIT")
            return
        
        # Vérification 2: Le message vient-il d'une source autorisée?
        if not self._check_uid_device(device_uid):
            print(f"[DeviceManager._handle_incoming_message] Untrusted sender: {device_uid}")
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
    
    def _check_uid_device(self, uid):
        """
        Vérifie si le destinataire est valide.
        
        Args:
            uid: UID du destinataire
            
        Returns:
            True si le destinataire est valide, False sinon
        """
        print(f"[DeviceManager._check_uid_device] Checking recipient: {uid}")
        
        # Le gateway parent est toujours autorisé
        device_uid = self.config.get('device.uid')
        if device_uid and uid == device_uid:
            print(f"[DeviceManager._check_uid_device] Recipient is parent gateway: {uid}")
            return True
        
        # Autres règles de confiance peuvent être ajoutées ici
        # Par exemple: liste blanche d'UIDs, etc.
        
        print(f"[DeviceManager._check_uid_device] Recipient not valid: {uid}")
        return False

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
    
    def _on_ack_received(self, message):
        """Callback appelé quand un ACK est reçu"""
        print("[DeviceManager._on_ack_received] ACK received!")
        self.ack_received = True
        self.cycle_active = False
    
    def _needs_i2c(self):
        sensors_config = self.config.get('sensors', [])
        return any(s.get('bus') == 'i2c' or s.get('type') in ['bh1750', 'bmp280']
                   for s in sensors_config if s.get('enabled', False))