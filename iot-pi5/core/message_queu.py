import threading
import time
from datetime import datetime


class MessageQueue:
    """
    Stores outbound messages (gateway → ESP32) and sends them on demand.

    Responsibilities:
    - Queue messages per ESP32 UID
    - Expose has_pending() so GatewayCore can decide ACK state (L vs S)
    - Subscribe to device.outbound.start: send all queued messages + a STATUS frame
      The LoRa receive thread handles the incoming ACK from ESP32 via MessageRouter.
    """

    def __init__(self, gateway_core):
        self.gateway = gateway_core
        self.pending_messages = {}  # {uid: [message, ...]}
        self._in_flight = {}  # {uid: [message, ...]} sent but not yet ACK'd
        self.lock = threading.Lock()
        gateway_core.event_bus.subscribe("device.outbound.start", self._on_outbound_start)
        gateway_core.event_bus.subscribe("device.outbound.ack", self._on_outbound_ack)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def queue_message(self, esp_uid: str, message):
        """Add a message (LoRa frame string or dict) to the queue for an device."""
        with self.lock:
            if esp_uid not in self.pending_messages:
                self.pending_messages[esp_uid] = []
            self.pending_messages[esp_uid].append(message)
            print(f"[MessageQueue] Message queued for {esp_uid} "
                  f"(total: {len(self.pending_messages[esp_uid])})")

    def has_pending(self, esp_uid: str) -> bool:
        """Return True if there are pending messages for this device."""
        with self.lock:
            return bool(self.pending_messages.get(esp_uid))

    # ------------------------------------------------------------------
    # Event handler
    # ------------------------------------------------------------------

    def _on_outbound_start(self, esp_uid: str):
        """
        Send all queued messages followed by a STATUS frame.
        Triggered by GatewayCore after it sends ACK OK;L to the device.
        The ESP32 is now in receive mode; ACK confirmation comes back through
        the normal LoRa receive loop (handled by MessageRouter → device.outbound.ack).
        """
        with self.lock:
            messages = list(self.pending_messages.pop(esp_uid, []))
            self._in_flight[esp_uid] = messages

        if not messages:
            print(f"[MessageQueue] No messages to send for {esp_uid}")
            return

        count = len(messages)
        print(f"[MessageQueue] Outbound cycle for {esp_uid}: {count} message(s)")

        print(f"[MessageQueue] Waiting 300ms for ESP32 to enter RX mode...")
        time.sleep(0.3)

        for i, message in enumerate(messages):
            print(f"[MessageQueue] Sending message {i+1}/{count}...")
            self._send_message(esp_uid, message)
            print(f"[MessageQueue] Message {i+1}/{count} sent, sleeping 100ms...")
            time.sleep(0.1)

        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        status_frame = f"B|S|{timestamp}|{esp_uid}|O;{count}|E"
        print(f"[MessageQueue] Sending STATUS frame: {status_frame}")
        time.sleep(0.1)
        self.gateway.lora_comm.send(status_frame)
        print(f"[MessageQueue] STATUS sent OK")

    def _on_outbound_ack(self, payload: dict):
        """Clear in-flight messages on ACK OK; re-queue them on ACK KO."""
        uid = payload["uid"]
        success = payload.get("success", False)
        with self.lock:
            failed = self._in_flight.pop(uid, [])
            if success:
                print(f"[MessageQueue] ACK OK from {uid} - {len(failed)} message(s) confirmed")
            elif failed:
                existing = self.pending_messages.get(uid, [])
                self.pending_messages[uid] = failed + existing
                print(f"[MessageQueue] ACK KO from {uid} - {len(failed)} message(s) re-queued")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send_message(self, esp_uid: str, message):
        """Send a single message via LoRa (string frame or dict)."""
        try:
            if isinstance(message, str):
                self.gateway.lora_comm.send(message)
            elif isinstance(message, dict):
                msg_type = message.get("type", "D")
                data = message.get("data", "")
                ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
                lora_frame = f"B|{msg_type}|{ts}|{esp_uid}|{data}|E"
                self.gateway.lora_comm.send(lora_frame)
            else:
                print(f"[MessageQueue] Unsupported message format: {type(message)}")
        except Exception as e:
            print(f"[MessageQueue] Failed to send to {esp_uid}: {e}")