"""
Protocole de communication LoRa avec système d'acknowledge.
Implémente le Strategy Pattern pour la communication.
"""

import time
from communication.base_protocol import CommunicationProtocol


def log(message):
    """Affiche un message avec l'heure courante (HH:MM:SS)"""
    t = time.localtime()
    timestamp = "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])
    print(f"[{timestamp}] {message}")


class LoRaProtocol(CommunicationProtocol):
    """
    Stratégie de communication via LoRa avec gestion des ACK.
    Format des messages : B|type|timestamp|uid|datas|E
    """

    def __init__(self, lora, uid, rtc=None, config=None):
        super().__init__("LoRa")
        self.lora = lora
        self.uid = uid
        self.rtc = rtc
        
        # Configuration
        config = config or {}
        self.frequency = config.get('frequency', 433.1)
        self.spreading_factor = config.get('spreading_factor', 10)
        self.bandwidth = config.get('bandwidth', 500000)
        
        # Paramètres ACK
        self.ack_enabled = config.get('ack_enabled', True)
        self.ack_timeout_ms = config.get('ack_timeout_ms', 2000)
        self.max_retries = config.get('max_retries', 3)
        self.listen_timeout_ms = config.get('listen_timeout_ms', 3000)
        
        # Compteurs de stats
        self.stats = {
            'sent': 0,
            'received': 0,
            'ack_received': 0,
            'ack_timeout': 0,
            'retries': 0
        }
        
        self._connected = bool(lora)

    def connect(self):
        """Établir la connexion LoRa"""
        if self.lora:
            self._connected = True
            log(f"[{self.name}] Connected at {self.frequency}MHz, SF={self.spreading_factor}")
        else:
            raise RuntimeError("LoRa module not initialized")

    def disconnect(self):
        """Fermer la connexion"""
        self._connected = False
        self.lora = None

    def send(self, data, expect_ack=None, retries=None):
        """
        Envoie des données via LoRa avec gestion d'ACK.
        
        Args:
            data: dict ou string à envoyer
            expect_ack: bool, force l'attente d'ACK (None = utilise self.ack_enabled)
            retries: nombre de tentatives (None = utilise self.max_retries)
            
        Returns:
            bool: True si envoyé avec succès (et ACK reçu si activé)
        """
        if not self._connected:
            self.connect()
        
        # Build message in standard format
        if isinstance(data, dict):
            msg_type = data.get('type', 'D')
            payload_data = data.get('datas', '')
        else:
            msg_type = 'D'
            payload_data = str(data)
        
        message = self._build_message(msg_type, payload_data)
        
        # Décider si on attend un ACK
        wait_ack = expect_ack if expect_ack is not None else self.ack_enabled
        max_attempts = retries if retries is not None else self.max_retries
        
        # Send with retry logic
        for attempt in range(1, max_attempts + 1):
            # Send the message
            self._send_burst(message)
            self.stats['sent'] += 1
            
            if not wait_ack:
                return True  # No ACK requested, consider as success
            
            # Wait for ACK
            log(f"Waiting for ACK (attempt {attempt}/{max_attempts})...")
            ack = self._wait_for_ack(timeout_ms=self.ack_timeout_ms)
            
            if ack:
                self.stats['ack_received'] += 1
                log(f"ACK reçu")
                return True
            
            # No ACK received
            self.stats['ack_timeout'] += 1
            if attempt < max_attempts:
                self.stats['retries'] += 1
                log(f"ACK timeout, retrying {attempt}/{max_attempts}...")
                time.sleep_ms(200)  # Small delay before retry
        
        log(f"Failed after {max_attempts} attempts (no ACK)")
        return False

    def send_ack(self, to_uid):
        """Send ACK to a specific device"""
        message = self._build_message("ACK", f"TO:{to_uid}")
        self._send_burst(message)
        log(f"ACK sent to {to_uid}")

    def receive(self, timeout_ms=None):
        """
        Écoute et reçoit un message LoRa.
        
        Args:
            timeout_ms: timeout en ms (None = utilise self.listen_timeout_ms)
            
        Returns:
            dict ou None: message parsé ou None si timeout
        """
        timeout = timeout_ms if timeout_ms is not None else self.listen_timeout_ms
        message = self._listen(timeout_ms=timeout)
        
        if message:
            self.stats['received'] += 1
            
            # Auto-reply with ACK if not already an ACK
            if self.ack_enabled and message.get('type') not in ['ACK', 'NACK']:
                self.send_ack(message.get('uid'))
        
        return message

    def is_connected(self):
        """Vérifier l'état de la connexion"""
        return self._connected

    def get_stats(self):
        """Return communication statistics"""
        return self.stats.copy()

    # ═══════════════════════════════════════════════════════════════
    # PRIVATE METHODS (prefixed with _)
    # ═══════════════════════════════════════════════════════════════

    def _build_message(self, msg_type, data=""):
        """Build a message in format: B|type|timestamp|uid|data|E"""
        timestamp = self._get_timestamp()
        return f"B|{msg_type}|{timestamp}|{self.uid}|{data}|E"

    def _send_burst(self, message, burst_count=3):
        """Send message multiple times with padding to avoid packet loss"""
        padded_message = "XXXX" + message
        payload = padded_message.encode('utf-8')
        
        for i in range(burst_count):
            self.lora.send(payload)
            time.sleep_ms(100)
        
        if len(message) < 100:
            log(f" {message}")

    def _wait_for_ack(self, timeout_ms=2000):
        """
        Wait for ACK message specifically.
        
        Returns:
            dict or None: received ACK message or None if timeout
        """
        start = time.ticks_ms()
        
        # Initialisation RX
        self.lora._write(0x01, 0x81)
        self.lora._write(0x12, 0xFF)
        self.lora.recv()
        
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            irq = self.lora._read(0x12)
            
            if (irq & 0x40):  # RxDone
                self.lora._write(0x12, 0xFF)  # Clear IRQ
                
                try:
                    raw = self.lora._read_payload()
                    
                    if raw:
                        idx = raw.find(b'B|')
                        
                        if idx != -1:
                            clean_bytes = raw[idx:]
                            msg_str = clean_bytes.decode('utf-8', 'ignore').strip()
                            parsed = self._parse_message(msg_str)
                            
                            if parsed and parsed.get('type') == 'ACK':
                                # Vérifier que c'est pour nous
                                if f"TO:{self.uid}" in parsed.get('datas', ''):
                                    return parsed
                
                except Exception as e:
                    log(f"Error reading ACK: {e}")
                
                # Resume listening
                self.lora.recv()
            
            time.sleep_ms(10)
        
        return None

    def _listen(self, timeout_ms=3000):
        """
        Listen for LoRa messages (robust version).
        
        Returns:
            dict or None: parsed message for this device or None if timeout
        """
        log("Entering listen mode...")
        
        # Initialisation RX
        self.lora._write(0x01, 0x81)
        self.lora._write(0x12, 0xFF)
        self.lora.recv()
        
        start = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            irq = self.lora._read(0x12)
            
            if (irq & 0x40):  # RxDone
                self.lora._write(0x12, 0xFF)  # Clear IRQ
                
                try:
                    raw = self.lora._read_payload()
                    
                    if raw:
                        # Look for "B|" in raw bytes
                        idx = raw.find(b'B|')
                        
                        if idx != -1:
                            clean_bytes = raw[idx:]
                            
                            try:
                                msg_str = clean_bytes.decode('utf-8', 'ignore').strip()
                                parsed = self._parse_message(msg_str)
                                
                                if parsed:
                                    # Check if message is for us
                                    target_uid = parsed.get('uid')
                                    
                                    # Direct message for us
                                    if target_uid == self.uid:
                                        return parsed
                                    
                                    # Broadcast message
                                    if target_uid in ['', 'BROADCAST', 'ALL']:
                                        return parsed
                                    
                            except Exception as e:
                                log(f"Decoding error: {e}")
                        else:
                            log(f"⚠ Ignored (no 'B|' found)")
                
                except Exception as e:
                    log(f"RX read error: {e}")
                
                # Resume listening
                self.lora.recv()
            
            time.sleep_ms(10)
        
        return None

    def _parse_message(self, msg):
        """
        Parse a message in format: B|type|timestamp|uid|data|E
        
        Returns:
            dict or None: {'type': '...', 'timestamp': '...', 'uid': '...', 'datas': '...'}
        """
        msg = msg.strip()
        
        # Check structure
        if "B|" not in msg or "|E" not in msg:
            return None
        
        try:
            start_idx = msg.index("B|")
            end_idx = msg.rindex("|E") + 2
            clean_content = msg[start_idx:end_idx]
            
            # Remove B| and |E markers
            inner = clean_content[2:-2]
            parts = inner.split("|")
            
            if len(parts) < 3:
                return None
            
            # Reconstruct data (may contain | characters)
            data_str = "|".join(parts[3:]) if len(parts) > 3 else ""
            
            return {
                "type": parts[0],
                "timestamp": parts[1] if len(parts) > 1 else "",
                "uid": parts[2] if len(parts) > 2 else "",
                "datas": data_str
            }
        except Exception as e:
            log(f"Parsing error: {e}")
            return None

    def _get_timestamp(self):
        """Generate ISO 8601 timestamp"""
        # External RTC (DS3231)
        if self.rtc:
            try:
                dt = self.rtc.datetime()
                return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
                    dt[0], dt[1], dt[2], dt[4], dt[5], dt[6]
                )
            except:
                pass
        
        # Internal ESP32 RTC
        try:
            t = time.localtime()
            return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
                t[0], t[1], t[2], t[3], t[4], t[5]
            )
        except:
            # Fallback
            ms = time.ticks_ms() // 1000
            return f"BOOT+{ms}s"