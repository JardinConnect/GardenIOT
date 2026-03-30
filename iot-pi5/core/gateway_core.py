"""
Cœur du système Gateway - Classe principale
"""
import time
import json
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from models.states import SystemState, NormalState, PairingState, MaintenanceState
from models.messages import LoRaMessage, MqttMessage, MessageType
from core.event_bus import EventBus
from core.message_queu import MessageQueue

class GatewayCore:
    """
    Classe principale du système Gateway
    Coordonne tous les composants et gère le flux principal
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialise le système Gateway"""
        self.config = config
        self.running = False
        
        # Composants
        self.lora_comm = None
        self.mqtt_comm = None
        self.child_repo = None
        self.message_router = None
        self.event_bus = EventBus()
        self.message_queue = None
        
        # État du système
        self.current_state = None
        self.states = {
            SystemState.NORMAL: NormalState(self),
            SystemState.PAIRING: PairingState(self, duration=config.get("pairing_duration", 30)),
            SystemState.MAINTENANCE: MaintenanceState(self)
        }
        
        # Statistiques
        self.stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "errors": 0,
            "uptime": 0
        }

        self.pending_messages = {}  # {esp_uid: [message1, message2, ...]
        self.lora_thread = None
        self.lora_running = False

    
    def initialize_components(self, lora_comm, mqtt_comm, child_repo, message_router):
        """Initialise les composants du système"""
        self.lora_comm = lora_comm
        self.mqtt_comm = mqtt_comm
        self.child_repo = child_repo
        self.message_router = message_router
        
        # Initialiser les composants
        self.lora_comm.initialize()
        self.mqtt_comm.initialize()
        self.child_repo.initialize()
        self.message_queue = MessageQueue(self)

        # Wire LoRa and MQTT callbacks to MessageRouter
        self.mqtt_comm.set_message_callback(self.message_router.route_from_mqtt)
        self.lora_comm.set_message_callback(self.message_router.route_from_lora)

        # Subscribe to domain events published by MessageRouter
        self.event_bus.subscribe("device.data.received",    self._on_data_received)
        self.event_bus.subscribe("device.cycle.done",       self._on_cycle_done)
        self.event_bus.subscribe("device.outbound.ack",     self._on_outbound_ack)
        self.event_bus.subscribe("device.pairing.request",  self._on_pairing_request)
        self.event_bus.subscribe("device.pairing.ack",      self._on_pairing_ack)
        self.event_bus.subscribe("device.unpaired",         self._on_unpaired)
        self.event_bus.subscribe("device.alert.triggered",  self._on_alert_triggered)
        self.event_bus.subscribe("device.alert.config.ack", self._on_alert_config_ack)
    
    # ------------------------------------------------------------------
    # Domain event handlers
    # ------------------------------------------------------------------

    def _on_data_received(self, payload: dict):
        """Forward sensor data to MQTT."""
        self.mqtt_comm.publish("garden/analytics", {
            "uid": payload["uid"],
            "timestamp": payload["timestamp"],
            "sensors": payload["sensors"],
        }, qos=1)

    def _on_cycle_done(self, payload: dict):
        """
        Decide ACK state (L or S), send ACK to ESP32, and trigger outbound
        cycle if the gateway has queued messages for that device.
        """
        uid = payload["uid"]
        ack_status = payload["ack_status"]
        has_messages = self.message_queue.has_pending(uid)
        ack_state = 'L' if (ack_status == 'OK' and has_messages) else 'S'

        time.sleep(0.15)  # Let ESP32 radio transition from TX to RX before ACK arrives
        self.lora_comm.send_ack(uid, ack_status, ack_state)
        print(f"[GatewayCore] ACK → {uid}: {ack_status};{ack_state}")

        if ack_state == 'L':
            self.event_bus.publish("device.outbound.start", uid)

    def _on_outbound_ack(self, payload: dict):
        """Log the result of the gateway → ESP32 send cycle."""
        uid = payload["uid"]
        status = "successful" if payload["success"] else "failed"
        print(f"[GatewayCore] Outbound cycle {status} for {uid}")

    def _on_pairing_request(self, payload: dict):
        """Legacy: handle pairing request from ESP32 (kept for backward compat)."""
        uid = payload["uid"]
        print(f"[GatewayCore] Pairing request from {uid} (ignored - Pi5 initiates pairing)")

    def _on_pairing_ack(self, payload: dict):
        """ESP32 confirmed pairing - register child and return to NORMAL."""
        from models.states import PairingState as _PS

        uid = payload["uid"]

        if not isinstance(self.current_state, _PS):
            print(f"[GatewayCore] Pairing ACK from {uid} ignored - not in pairing mode")
            return

        success = self.child_repo.add_child(uid)
        if success:
            print(f"[GatewayCore] New device paired: {uid}")
        else:
            print(f"[GatewayCore] Device already known: {uid}")

        self.mqtt_comm.publish(
            "garden/pairing/result",
            {"uid": uid, "status": "ok", "parent_id": self.child_repo.get_parent_id()},
            qos=1,
        )

        self.set_state(SystemState.NORMAL)

    def _on_unpaired(self, payload: dict):
        """Remove device from repo and notify MQTT."""
        uid = payload["uid"]
        if self.child_repo.remove_child(uid):
            print(f"[GatewayCore] Device unpaired: {uid}")
            self.mqtt_comm.publish(
                "garden/pairing/unpair",
                {"uid": uid, "action": "unpaired"},
                qos=0,
            )

    def _on_alert_triggered(self, payload: dict):
        """Forward parsed alert trigger to MQTT."""
        self.mqtt_comm.publish("garden/alerts/trigger", payload["alert"], qos=1)

    def _on_alert_config_ack(self, payload: dict):
        """Forward alert config acknowledgement to MQTT."""
        uid = payload["uid"]
        self.mqtt_comm.publish(
            f"garden/alerts/ack/{uid}",
            {"uid": uid, "status": "received",
             "data": payload["data"], "timestamp": payload["timestamp"]},
            qos=0,
        )

    def get_instant_analytics(self):
        """Broadcast IA command to all children using parent_id."""
        self._lora_command_burst("IA")

    def update_device_settings(self, settings: dict, target_uid: str = None):
        """Send SET command to a specific child or all children."""
        data_str = "SET:" + ";".join(f"{k}={v}" for k, v in settings.items())
        if target_uid:
            self._lora_command_burst(data_str, target_uid=target_uid)
        else:
            children = self.child_repo.get_all_children()
            for c in children:
                uid = c["id"] if isinstance(c, dict) else c
                self._lora_command_burst(data_str, target_uid=uid)

    def _lora_command_burst(self, data: str, target_uid: str = None):
        """Send a LoRa COMMAND burst in a daemon thread.
        - target_uid provided: sends with that specific child UID (targeted)
        - target_uid is None:  sends with parent_id (broadcast to all)
        """
        import threading

        uid = target_uid if target_uid else self.child_repo.get_parent_id()

        def _burst():
            from models.messages import LoRaMessage, MessageType
            from datetime import datetime
            import time

            BURST_INTERVAL = 0.5
            BURST_DURATION = 18.0

            frame = LoRaMessage(
                message_type=MessageType.COMMAND,
                timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                uid=uid,
                data=data,
            ).to_lora_format()

            end = time.time() + BURST_DURATION
            count = 0
            while time.time() < end:
                self.lora_comm.send(frame)
                count += 1
                time.sleep(BURST_INTERVAL)

            print(f"[GatewayCore] Burst done: {data} -> {uid} ({count} sends over {BURST_DURATION}s)")

        threading.Thread(target=_burst, daemon=True).start()
        print(f"[GatewayCore] Burst started: {data} -> {uid}")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        """Start the gateway system."""
        print("[GatewayCore] Starting gateway system...")
        
        self.set_state(SystemState.NORMAL)
        self.running = True
        self.stats["uptime"] = time.time()
        self._start_lora_thread()
        print("[GatewayCore] System ready")
        self.main_loop()
    
    def _start_lora_thread(self):
        """Start the dedicated LoRa receiver thread."""
        import threading
        self.lora_running = True
        self.lora_thread = threading.Thread(
            target=self._lora_receiver_loop,
            name="LoRaReceiver",
            daemon=True
        )
        self.lora_thread.start()
        print("[GatewayCore] LoRa receiver thread started")

    def _lora_receiver_loop(self):
        """Blocking loop that continuously reads LoRa frames and triggers callbacks."""
        print("[GatewayCore] LoRa thread: running")
        try:
            while self.lora_running and self.running:
                try:
                    self.lora_comm.receive()
                except Exception as e:
                    print(f"[GatewayCore] LoRa thread error: {e}")
                    time.sleep(1)
        except Exception as e:
            print(f"[GatewayCore] LoRa thread fatal error: {e}")
        print("[GatewayCore] LoRa thread: stopped")

    def main_loop(self):
        """Main loop: handles system state and MQTT health. LoRa is handled by a dedicated thread."""
        start_time = time.time()
        try:
            while self.running:
                if self.current_state:
                    self.current_state.handle()
                self.process_mqtt_messages()
                self.stats["uptime"] = time.time() - start_time
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.shutdown("Keyboard interrupt")
        except Exception as e:
            self.shutdown(f"Fatal error: {e}", True)
    

    def process_mqtt_messages(self):
        """Check MQTT connection health and reconnect if needed."""
        try:
            if not self.mqtt_comm.is_connected():
                print("[GatewayCore] MQTT connection lost - reconnecting...")
                self.mqtt_comm.reconnect()
        except Exception as e:
            print(f"[GatewayCore] MQTT error: {e}")
            self.stats["errors"] += 1
    
    def set_state(self, state: SystemState):
        """Transition to a new system state."""
        if self.current_state:
            self.current_state.exit()
        self.current_state = self.states[state]
        self.current_state.enter()

    def trigger_pairing_mode(self):
        """Activate pairing mode."""
        if self.current_state and isinstance(self.current_state, PairingState):
            print("[GatewayCore] Pairing mode already active")
            return
        print("[GatewayCore] Activating pairing mode")
        self.set_state(SystemState.PAIRING)

    def handle_button_press(self, duration: float):
        """Handle physical button press."""
        if duration >= 15:
            print("[GatewayCore] Full child reset triggered by button")
            self.child_repo.remove_all_children()
        elif duration >= 3:
            print("[GatewayCore] Pairing mode triggered by button")
            self.trigger_pairing_mode()
    
    def shutdown(self, reason: str, error: bool = False):
        """Graceful shutdown."""
        print(f"[GatewayCore] Shutting down: {reason}")
        if error:
            import traceback
            traceback.print_exc()

        self.lora_running = False
        if self.lora_thread:
            self.lora_thread.join(timeout=5)
            if self.lora_thread.is_alive():
                print("[GatewayCore] Warning: LoRa thread did not stop cleanly")

        if self.mqtt_comm:
            self.mqtt_comm.disconnect()
        if self.lora_comm:
            self.lora_comm.shutdown()

        print("[GatewayCore] System stopped")
        self.running = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Return a copy of the current statistics."""
        return self.stats.copy()

    def get_system_info(self) -> Dict[str, Any]:
        """Return current system information."""
        return {
            "state": self.current_state.__class__.__name__ if self.current_state else "unknown",
            "children_count": len(self.child_repo.get_all_children()) if self.child_repo else 0,
            "uptime": self.stats.get("uptime", 0),
            "messages_received": self.stats.get("messages_received", 0),
            "messages_sent": self.stats.get("messages_sent", 0)
        }
