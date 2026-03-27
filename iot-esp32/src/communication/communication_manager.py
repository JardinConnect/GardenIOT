"""
Communication Manager - Strategy Pattern implementation.
Manages communication protocols with fallback support.
"""
import time


class CommunicationManager:
    """
    Communication manager using Strategy Pattern.
    Allows changing protocols at runtime with automatic fallback.
    """

    def __init__(self, primary_strategy=None, fallback_strategy=None, event_bus=None, rtc=None, config=None):
        self._strategy = primary_strategy
        self._fallback = fallback_strategy
        self._event_bus = event_bus
        self._rtc = rtc
        self._message_queue = []
        self._config = config
        self.last_send_time = None
        self._force_send = False
        self._waiting_for_ack = False
        self._send_attempts = 0
        self._data_count = 0
        self._ack_status = None
        self._ack_state = None
        self._ack_wait_ms = config.get('communication.ack_wait_ms', 2000) if config else 2000
        self._gateway_receive_timeout_ms = config.get('communication.gateway_receive_timeout_ms', 10000) if config else 10000
        self._device_uid = config.get('device.uid') if config else None
        name = primary_strategy.name if primary_strategy else 'None'
        print(f"[CommunicationManager] Primary: {name}")

        if self._event_bus:
            self._event_bus.subscribe('alert.triggered', self._on_alert_triggered)
            self._event_bus.subscribe('sensor.data.ready', self._on_sensor_data_ready)
            self._event_bus.subscribe('cycle.communication.send', self._cycle_communication_send)

    def set_strategy(self, strategy):
        print(f"[CommunicationManager] Switching to: {strategy.name}")
        self._strategy = strategy

    def set_fallback(self, fallback_strategy):
        self._fallback = fallback_strategy
        print(f"[CommunicationManager] Fallback set: {fallback_strategy.name}")

#==================================================
# Native methods
#==================================================

    def send(self, data, expect_ack=False):
        """
        Send data using active strategy with fallback support.
        
        Args:
            data: dict avec 'type' et 'data'
            expect_ack: attendre un ACK
            
        Returns:
            bool: True si envoyé avec succès
        """
        if not self._strategy:
            print("[CommunicationManager] No strategy configured")
            return False
        
        try:
            success = self._strategy.send(data, expect_ack=expect_ack)
            
            if success:
                return True
            
            if self._fallback:
                print(f"[CommunicationManager] Primary failed, fallback: {self._fallback.name}")
                return self._fallback.send(data, expect_ack=expect_ack)
            
            return False
        
        except Exception as e:
            print(f"[CommunicationManager] Send error: {e}")
            
            if self._fallback:
                try:
                    return self._fallback.send(data, expect_ack=expect_ack)
                except Exception as e2:
                    print(f"[CommunicationManager] Fallback error: {e2}")
            
            return False

    def receive(self, timeout_ms=None):
        """
        Receive data using active strategy.
        
        Args:
            timeout_ms: timeout en millisecondes
            
        Returns:
            dict: message parsé ou None
        """
        if not self._strategy:
            print("[CommunicationManager] No strategy configured")
            return None
        
        try:
            return self._strategy.receive(timeout_ms=timeout_ms)
        except Exception as e:
            print(f"[CommunicationManager] Receive error: {e}")
            return None

    def disconnect(self):
        """Déconnecte tous les protocoles."""
        if self._strategy:
            try:
                self._strategy.disconnect()
            except Exception as e:
                print(f"[CommunicationManager] Disconnect error: {e}")
        
        if self._fallback:
            try:
                self._fallback.disconnect()
            except Exception as e:
                print(f"[CommunicationManager] Fallback disconnect error: {e}")

    #==================================================
    # Specific sending methods
    #==================================================

    def _send_ack(self, status, type='ACK'):
        """Envoie un ACK à la gateway (utilisé lors de la réception de messages gateway)."""
        ack_msg = {
            'type': type,
            'data': {'status': status},
            'timestamp': self._get_current_timestamp()
        }
        print(f"[CommunicationManager] Sending {type}: {status}")
        self.send(ack_msg)

    #==================================================
    # Cycle methods listening
    #==================================================

    def _handle_incoming(self, message):
        """Dispatcher unique: ACK → attributs de classe, autre type → event bus."""
        if not message or not self._check_my_uid(message.get('uid')):
            return

        msg_type = message.get('type')
        print(f"[CommunicationManager] Incoming: type={msg_type}")

        if msg_type == 'ACK':
            data = message.get('data', '')
            parts = data.split(';') if isinstance(data, str) else []
            self._ack_status = parts[0] if parts else 'OK'
            self._ack_state = parts[1] if len(parts) > 1 else None
            print(f"[CommunicationManager] ACK: status={self._ack_status}, state={self._ack_state}")
            if self._ack_state == 'L':
                print("[CommunicationManager] Gateway has messages, starting receive cycle")
                self._receive_gateway_messages()
        else:
            self._event_bus.publish('message.received.{t}'.format(t=msg_type), message)

    def _receive_gateway_messages(self):
        """
        Reçoit tous les messages envoyés par la gateway.
        Attend le message de status (type S) avec le compte, compare, envoie ACK.
        """
        print("[CommunicationManager] Receiving gateway messages...")
        received_messages = []
        gateway_count = None

        start_time = time.ticks_ms()
        timeout_ms = self._gateway_receive_timeout_ms

        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            try:
                message = self.receive(timeout_ms=2000)
                if not message:
                    continue

                if not self._check_my_uid(message.get('uid')):
                    continue

                msg_type = message.get('type')

                if msg_type == 'S':
                    data = message.get('data', '')
                    parts = data.split(';') if isinstance(data, str) else []
                    try:
                        gateway_count = int(parts[1]) if len(parts) > 1 else 0
                    except (ValueError, IndexError):
                        gateway_count = 0
                    print(f"[CommunicationManager] Gateway status: {gateway_count} messages sent, got {len(received_messages)}")
                    break
                else:
                    received_messages.append(message)

            except Exception as e:
                print(f"[CommunicationManager] Receive error: {e}")

        received_count = len(received_messages)
        if gateway_count is None:
            print("[CommunicationManager] Timeout waiting for gateway status")
            self._send_ack('KO')
        elif received_count == gateway_count:
            print(f"[CommunicationManager] All {received_count} gateway messages received, ACK OK")
            self._send_ack('OK')
        else:
            print(f"[CommunicationManager] Count mismatch: expected {gateway_count}, got {received_count}, ACK FAIL")
            self._send_ack('KO')

        for message in received_messages:
            self._handle_incoming(message)

   #==================================================
   # Cycle methods Send
   #==================================================

    def _cycle_communication_send(self, _=None):
        """Cycle complet: send + attente ACK (via attribut) + retry max 3."""
        if not self._message_queue or self._waiting_for_ack:
            return

        self._data_count = len(self._message_queue)
        print(f"[CommunicationManager] Starting send cycle: {self._data_count} messages")

        for attempt in range(3):
            self._send_attempts = attempt
            self._waiting_for_ack = True
            self._ack_status = None

            self._do_send_cycle()

            start = time.ticks_ms()
            while self._ack_status is None and time.ticks_diff(time.ticks_ms(), start) < self._ack_wait_ms:
                message = self.receive(timeout_ms=500)
                if message:
                    self._handle_incoming(message)

            if self._ack_status == 'OK':
                self._message_queue = []
                self.last_send_time = time.time()
                self._reset_cycle_state()
                return

            print(f"[CommunicationManager] No ACK or FAIL (attempt {attempt + 1}/3)")
            self._waiting_for_ack = False

        print("[CommunicationManager] Max retries reached, aborting")
        self._event_bus.publish('communication.send_failed', {'count': self._data_count})
        self._reset_cycle_state()

    def _do_send_cycle(self):
        """Envoie les messages de la queue puis un status séparé (non stocké en queue)."""
        print(f"[CommunicationManager] Send attempt {self._send_attempts + 1}/3 - {self._data_count} messages")
        try:
            for message_payload in self._message_queue:
                self.send(message_payload)
                time.sleep(0.05)
            status_msg = self._build_status_message("O", self._data_count)
            self.send(status_msg)
            print(f"[CommunicationManager] Sent {self._data_count} messages + status, waiting for ACK")
        except Exception as e:
            print(f"[CommunicationManager] Error during send cycle: {e}")

    def _reset_cycle_state(self):
        """Réinitialise tous les attributs du cycle d'envoi."""
        self._waiting_for_ack = False
        self._ack_status = None
        self._ack_state = None
        self._data_count = 0
        self._send_attempts = 0


    #==================================================
    # Callback methods
    #==================================================

    def _on_alert_triggered(self, queue_alert_data):
        """Callback avec gestion d'erreurs améliorée"""
        try:
            for alert_data in queue_alert_data:
                message = self._build_alert_message(alert_data)
                self._message_queue.append(message)
            self._event_bus.publish('cycle.communication.send')

        except Exception as e:
            print(f"[CommManager] Critical error processing alert: {e}")
            return False

    def _on_sensor_data_ready(self, event_payload):
        """Handle sensor data ready event - add to message queue."""
        try:
            # Add to queue
            message_data = {
                'type': 'D',
                'data': event_payload.get('data'),
                'timestamp': event_payload.get('timestamp')
            }
            self._message_queue.append(message_data)
            print(f"[CommunicationManager] Message queued: {len(self._message_queue)}")

            timestamp = event_payload.get('timestamp')
            
            # Check if we should send now based on configuration
            send_message = self._check_send_conditions(timestamp)
            if send_message:
                self._event_bus.publish('cycle.communication.send')
            
        except Exception as e:
            print(f"[CommunicationManager] Error handling sensor data: {e}")

    #==================================================
    # Build message methods
    #==================================================

    def _build_status_message(self, status, count=None):
        """Prepare a status update message to be sent to the gateway."""
        payload = {
            'type': 'S',
            'data': {
                'status': status,
                'count': count if count is not None else len(self._message_queue),
            },
            'timestamp': self._get_current_timestamp()
        }
        return payload

    def _build_alert_message(self, alert_data):
        """Construire un message d'alerte standardisé"""
        threshold = alert_data.get('threshold', {})
        data = {
                'identifier': alert_data.get('identifier', ''),
                'value': alert_data.get('value'),
                'alert_id': threshold.get('id'),
                'level': alert_data.get('level', 'C')
            }
        return {
            'type': 'T',  # Type Trigger Alerte
            'data': data,
            'timestamp': alert_data.get('timestamp', self._get_current_timestamp())
        }

    #==================================================
    # Helper methods
    #==================================================

    def _check_my_uid(self, uid):
        """Vérifie si l'UID correspond au notre ou à notre parent (gateway)."""
        if not uid:
            return False
        if self._device_uid and uid == self._device_uid:
            return True
        parent_id = self._config.get('device.parent_id') if self._config else None
        if parent_id and uid == parent_id:
            return True
        return False

    def _check_send_conditions(self, timestamp):
        """Check if we should send queued messages based on configuration."""
        if self._force_send:
            print("[CommunicationManager] Force send active - bypassing interval check")
            self._force_send = False
            return True

        if not self._config:
            return
        
        send_interval = self._config.get('device.send_interval', 60)  # seconds

        now = time.time()
        if self.last_send_time is None or (now - self.last_send_time) >= send_interval:
            print(f"[CommunicationManager] Time to send messages (last sent: {self.last_send_time}, now: {now})")
            return True
        return False

    def _get_current_timestamp(self):
        """Get current timestamp from RTC or fallback to time.localtime."""
        if self._rtc:
            try:
                dt = self._rtc.datetime()
                return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
                    dt[0], dt[1], dt[2], dt[4], dt[5], dt[6]
                )
            except Exception as e:
                print(f"[CommunicationManager] RTC error: {e}")
        
        # Fallback to time.localtime
        import time
        t = time.localtime()
        return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
            t[0], t[1], t[2], t[3], t[4], t[5]
        )

    def get_stats(self):
        """Get statistics from all strategies."""
        stats = {}
        
        if self._strategy:
            stats['primary'] = {
                'protocol': self._strategy.name,
                'stats': self._strategy.get_stats()
            }
        
        if self._fallback:
            stats['fallback'] = {
                'protocol': self._fallback.name,
                'stats': self._fallback.get_stats()
            }
        
        stats['queue'] = {
            'messages_pending': len(self._message_queue)
        }
        
        return stats
