"""
Message Router - Parses incoming LoRa frames and publishes domain events.
"""
from typing import Dict, Any
from datetime import datetime
from models.messages import LoRaMessage, MqttMessage, MessageType, SensorData, AlertConfig, AlertTrigger


class MessageRouter:
    """
    Parses LoRa frames and dispatches them as domain events on the EventBus.
    Does NOT call other components directly - only publishes events.

    Responsibilities:
    - Parse raw LoRa strings into LoRaMessage objects
    - Track per-device receive session counts (DATA messages before STATUS)
    - Publish domain events: device.data.received, device.cycle.done, device.outbound.ack,
      device.pairing.request, device.unpaired, device.alert.triggered, device.alert.config.ack
    - Route inbound MQTT messages to outbound LoRa (alert config, unpair, commands)
    """

    # Message types that are payload in an ESP32 send cycle and must be counted.
    # Must match what the ESP32 puts in its _message_queue (type 'D' and type 'T').
    _SESSION_PAYLOAD_TYPES = frozenset({
        MessageType.DATA,
        MessageType.ALERT_TRIGGER,
    })

    def __init__(self, gateway_core):
        self.gateway = gateway_core
        self._receive_sessions = {}  # {uid: received_count} - reset after STATUS

    # ------------------------------------------------------------------
    # Public entry points (called by GatewayCore threads)
    # ------------------------------------------------------------------

    def route_from_lora(self, raw_message: str):
        """Parse a raw LoRa frame and dispatch to the appropriate handler."""
        try:
            lora_msg = LoRaMessage.from_lora_format(raw_message)
            if not lora_msg:
                self.gateway.stats["errors"] += 1
                print(f"[MessageRouter] Could not parse LoRa frame: {raw_message}")
                return

            self.gateway.stats["messages_received"] += 1

            # Count all payload message types centrally so the session count matches
            # the ESP32's _data_count (which counts all queue items, not just type 'D').
            if (lora_msg.message_type in self._SESSION_PAYLOAD_TYPES
                    and self.gateway.child_repo.is_child_authorized(lora_msg.uid)):
                self._receive_sessions[lora_msg.uid] = \
                    self._receive_sessions.get(lora_msg.uid, 0) + 1
                print(f"[MessageRouter] Session count for {lora_msg.uid}: "
                      f"{self._receive_sessions[lora_msg.uid]}")

            handler_name = f"_handle_lora_{lora_msg.message_type.name.lower()}"
            handler = getattr(self, handler_name, self._handle_unknown_lora)
            handler(lora_msg)

        except Exception as e:
            self.gateway.stats["errors"] += 1
            print(f"[MessageRouter] Error processing LoRa message: {e}")

    def route_from_mqtt(self, topic: str, payload: str, qos: int = 1):
        """Route an incoming MQTT message to the appropriate outbound handler."""
        try:
            mqtt_message = MqttMessage.from_mqtt(topic, payload, qos)

            if "alerts/config" in topic:
                self._handle_mqtt_alert_config(mqtt_message.payload)
            # elif "pairing/unpair" in topic:
            #     self._handle_mqtt_unpair(mqtt_message.payload)
            elif "pairing/request" in topic:
                self._handle_mqtt_pairing_request(mqtt_message.payload)
            elif "devices/command" in topic:
                self._handle_mqtt_device_command(mqtt_message.payload)
            elif "devices/settings" in topic:
                self._handle_mqtt_device_settings(mqtt_message.payload)
            else:
                print(f"[MessageRouter] Unhandled MQTT topic: {topic}")

        except Exception as e:
            print(f"[MessageRouter] Error routing MQTT message: {e}")

    # ------------------------------------------------------------------
    # Inbound LoRa handlers - publish events only, no direct calls
    # ------------------------------------------------------------------

    def _handle_lora_data(self, message: LoRaMessage):
        """Publish device.data.received. Session count is handled centrally in route_from_lora."""
        uid = message.uid
        if not self.gateway.child_repo.is_child_authorized(uid):
            print(f"[MessageRouter] DATA ignored - unauthorized device: {uid}")
            return

        sensor_data = SensorData.from_lora_data(message.data)
        self.gateway.event_bus.publish("device.data.received", {
            "uid": uid,
            "timestamp": message.timestamp,
            "data": sensor_data.parsed_values,
        })

    def _handle_lora_status(self, message: LoRaMessage):
        """
        Compare declared vs received count and publish device.cycle.done.
        GatewayCore subscribes to device.cycle.done to decide ACK state (L/S) and send ACK.
        """
        uid = message.uid
        if not self.gateway.child_repo.is_child_authorized(uid):
            print(f"[MessageRouter] STATUS ignored - unauthorized device: {uid}")
            self._receive_sessions.pop(uid, None)
            return

        parts = message.data.split(';') if message.data else []
        esp_status = parts[0] if parts else 'F'
        try:
            declared_count = int(parts[1]) if len(parts) > 1 else 0
        except (ValueError, IndexError):
            declared_count = 0

        received_count = self._receive_sessions.pop(uid, 0)
        print(f"[MessageRouter] STATUS from {uid}: esp={esp_status} declared={declared_count} received={received_count}")

        if esp_status == 'O' and received_count == declared_count and declared_count > 0:
            ack_status = 'OK'
        else:
            ack_status = 'KO'
            print(f"[MessageRouter] Count mismatch or ESP32 failure → ack_status=KO")

        self.gateway.event_bus.publish("device.cycle.done", {
            "uid": uid,
            "ack_status": ack_status,
        })

    def _handle_lora_ack(self, message: LoRaMessage):
        """
        Handle ACK sent by ESP32 after receiving the gateway's outbound cycle (L state).
        Publishes device.outbound.ack so GatewayCore can log/react.
        """
        uid = message.uid
        ack_ok = message.data.startswith('OK') if message.data else False
        print(f"[MessageRouter] Outbound ACK from {uid}: {'OK' if ack_ok else 'KO'}")
        self.gateway.event_bus.publish("device.outbound.ack", {
            "uid": uid,
            "success": ack_ok,
        })

    def _handle_lora_pa_ack(self, message: LoRaMessage):
        """ESP32 confirms pairing - publish device.pairing.ack."""
        print(f"[MessageRouter] Pairing ACK from {message.uid}")
        ack_ok = message.data.startswith('OK') if message.data else False

        self.gateway.event_bus.publish("device.pairing.ack", {
            "uid": message.uid,
            "timestamp": message.timestamp,
            "success": ack_ok,
        })

    def _handle_lora_pairing(self, message: LoRaMessage):
        """Publish device.pairing.request - GatewayCore decides whether to accept."""
        print(f"[MessageRouter] Pairing request from {message.uid}")
        self.gateway.event_bus.publish("device.pairing.request", {
            "uid": message.uid,
            "timestamp": message.timestamp,
            "data": message.data,
        })

    # def _handle_lora_unpair(self, message: LoRaMessage):
    #     """Publish device.unpaired - GatewayCore removes device and notifies MQTT."""
    #     print(f"[MessageRouter] Unpair request from {message.uid}")
    #     self.gateway.event_bus.publish("device.unpaired", {"uid": message.uid})

    def _handle_lora_alert_config(self, message: LoRaMessage):
        """Publish device.alert.config.ack - GatewayCore forwards to MQTT."""
        print(f"[MessageRouter] Alert config ACK from {message.uid}")
        self.gateway.event_bus.publish("device.alert.config.ack", {
            "uid": message.uid,
            "data": message.data,
            "timestamp": self._get_current_timestamp(),
        })

    def _handle_lora_alert_trigger(self, message: LoRaMessage):
        """Parse alert trigger and publish device.alert.triggered."""
        print(f"[MessageRouter] Alert triggered from {message.uid}")
        trigger = AlertTrigger.from_lora_data(message.data, message.uid, message.timestamp)
        self.gateway.event_bus.publish("device.alert.triggered", {
            "uid": message.uid,
            "alert": trigger.to_dict(),
        })

    def _handle_unknown_lora(self, message: LoRaMessage):
        print(f"[MessageRouter] Unknown LoRa type: {message.message_type.value} from {message.uid}")

    # ------------------------------------------------------------------
    # Inbound MQTT handlers - outbound path, direct calls are acceptable
    # ------------------------------------------------------------------

    def _handle_mqtt_alert_config(self, payload: dict):
        """Queue alert config for each valid cell."""
        alert_id = payload.get("id", "")
        print(f"[MessageRouter] Alert config received: {alert_id}")

        alert_config = AlertConfig.from_mqtt_payload(payload)
        valid_cells = [c for c in alert_config.cell_ids
                       if self.gateway.child_repo.is_child_authorized(c)]

        if not valid_cells:
            print(f"[MessageRouter] No valid cells for alert {alert_id}")
            return

        alert_config.cell_ids = valid_cells
        for cell_uid in valid_cells:
            lora_message = LoRaMessage(
                message_type=MessageType.ALERT_CONFIG,
                timestamp=self._get_current_timestamp(),
                uid=cell_uid,
                data=alert_config.to_lora_data(),
            )
            self.gateway.message_queue.queue_message(cell_uid, lora_message.to_lora_format())
            print(f"[MessageRouter] Alert {alert_id} queued for {cell_uid}")

    # def _handle_mqtt_unpair(self, payload: dict):
    #     """Send unpair command via LoRa and remove device from repo."""
    #     uid = payload.get("uid", "")
    #     print(f"[MessageRouter] Unpair command for {uid}")
    #     lora_message = LoRaMessage(
    #         message_type=MessageType.UNPAIR,
    #         timestamp=self._get_current_timestamp(),
    #         uid=uid,
    #         data="",
    #     )
    #     self.gateway.lora_comm.send(lora_message.to_lora_format())
    #     self.gateway.child_repo.remove_child(uid)

    def _handle_mqtt_pairing_request(self, payload: dict):
        """Start or stop pairing mode from MQTT.
        Payload: {"event": "start"|"stop", "ack_id": "<session_id>"}
        - ack_id: optional, returned in garden/pairing/ack so the backend can track sessions.
        """
        event = payload.get("event")
        if event == "start":
            ack_id = payload.get("ack_id")
            print(f"[MessageRouter] Pairing start requested via MQTT (ack_id={ack_id})")
            self.gateway.trigger_pairing_mode(ack_id=ack_id)
        elif event == "stop":
            print("[MessageRouter] Pairing stop requested via MQTT")
            from models.states import SystemState
            self.gateway.set_state(SystemState.NORMAL)

    def _handle_mqtt_device_command(self, payload: dict):
        """Handle system commands from MQTT.
        Payload: {"command": "<type>", ...}
        Supported commands:
            - instant_analytics: trigger immediate analytics processing
            - reboot: reboot the gateway
            - factory_reset: reset configuration to defaults
        """
        command = payload.get("command")
        if command == "instant_analytics":
            print("[MessageRouter] Instant analytics command received")
            self.gateway.get_instant_analytics()
        elif command == "reboot":
            print("[MessageRouter] Reboot command received")
            self.gateway.reboot()
        elif command == "factory_reset":
            print("[MessageRouter] Factory reset command received")
            self.gateway.factory_reset()
        else:
            print(f"[MessageRouter] Unknown command: {command}")

    def _handle_mqtt_device_settings(self, payload: dict):
        """Handle device settings update from MQTT.
        Payload: {"uid": "<child_uid>", "send_interval": <int>, "sleep_interval": <int>}
        - uid: optional, target a specific device. If omitted, sends to all children.
        Only known setting keys are forwarded. At least one valid key is required.
        """
        ALLOWED_KEYS = {"send_interval", "sleep_interval"}
        target_uid = payload.get("uid")
        settings = {k: v for k, v in payload.items() if k in ALLOWED_KEYS}

        if not settings:
            print(f"[MessageRouter] No valid settings in payload: {payload}")
            return

        print(f"[MessageRouter] Device settings update: {settings} -> {target_uid or 'all'}")
        self.gateway.update_device_settings(settings, target_uid=target_uid)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_current_timestamp(self) -> str:
        return datetime.now().isoformat()
