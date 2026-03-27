"""
Protocole de communication LoRa simplifié.
Implémente le Strategy Pattern pour la communication.
"""
from communication.base_protocol import CommunicationProtocol
import time
import machine

def log(msg):
    print(f"[LoRa] {msg}")


class LoRaProtocol(CommunicationProtocol):
    
    def __init__(self, lora, uid, rtc=None, config=None):
        self._lora = lora
        self._uid = uid
        self._rtc = rtc
        self._config = config or {}
        self.name = "LoRa"
        
        self._ack_timeout = self._config.get('ack_timeout_ms', 3000)
        self._max_retries = self._config.get('max_retries', 3)
        self._listen_timeout = self._config.get('listen_timeout_ms', 4000)

        # Buffer pour stocker les messages reçus via callback
        self._rx_buffer = None
        
        # Configurer le callback de réception
        self._lora.on_recv(self._on_receive)

        self._stats = {
            'sent': 0,
            'received': 0,
            'ack_ok': 0,
            'ack_fail': 0,
            'errors': 0
        }
    
    # ===========================================================
    # PUBLIC METHODS
    # ===========================================================
    
    def send(self, message, expect_ack=False):
        """
        Envoie un message LoRa. Retente si pas d'ACK.
        
        Args:
            message: Dictionnaire avec 'type', 'datas', etc.
            expect_ack: Si True, attend un ACK du gateway
            
        Returns:
            True si succès (envoi + ACK si attendu), False sinon
        """
        log(f"Preparing to send message: {message}")
        
        # Construire le message
        built_message = self._build_message(message)
        # TODO: Supprimer si possible l'ajout du padding
        # Ajouter un padding de 4 bytes au début du message
        padded_message = "XXXX" + built_message
        frame = padded_message.encode('utf-8')
        
        log(f"Built message: {built_message}")
        
        # Essayer plusieurs fois
        for attempt in range(1, self._max_retries + 1):
            log(f"Send attempt {attempt}/{self._max_retries}")
            
            try:
                # Envoyer via le hardware LoRa
                self._lora.send(frame)
                self._stats['sent'] += 1
                log("Message sent successfully")
                return True
            except Exception as e:
                log(f"Send error: {e}")
                self._stats['errors'] += 1
                if attempt < self._max_retries:
                    time.sleep(0.5)
                continue

        return False
    
    def receive(self, timeout_ms=None):
        """
        Écoute un message LoRa en utilisant le polling direct.
        
        Args:
            timeout_ms: Timeout en millisecondes (None pour utiliser la config)
            
        Returns:
            Dictionnaire avec les champs du message ou None si timeout
        """
        timeout_ms_actual = timeout_ms if timeout_ms else int(self._listen_timeout * 1000)
        log(f"Listening for messages (timeout: {timeout_ms_actual}ms)")

        # A packet may have been buffered by the interrupt handler while the caller
        # was busy processing the previous message (e.g. _handle_incoming for 'A').
        # Check before entering Standby so we don't lose it.
        if self._rx_buffer is not None:
            raw_payload = self._rx_buffer
            self._rx_buffer = None
            msg = self._process_raw_payload(raw_payload)
            if msg:
                return msg

        # Check if a packet arrived while the CPU was in lightsleep.
        # The radio keeps running during lightsleep and sets the RxDone IRQ flag,
        # but the GPIO interrupt can't fire while the CPU is halted.
        # We must read the FIFO BEFORE clearing IRQ flags.
        irq_pre = self._lora._read(0x12)
        if irq_pre & 0x40:  # RxDone - packet received during lightsleep
            self._lora._write(0x01, 0x81)  # Standby to safely read FIFO
            self._lora._write(0x12, 0xFF)  # Clear IRQ
            try:
                raw_payload = self._lora._read_payload()
                msg = self._process_raw_payload(raw_payload)
                if msg:
                    self._lora.recv()  # Back to RX
                    return msg
            except Exception as e:
                log(f"Pre-check receive error: {e}")

        # Initialiser le mode réception
        self._lora._write(0x01, 0x81)  # Standby
        self._lora._write(0x12, 0xFF)  # Clear IRQ
        self._lora.recv()  # RX mode
        
        start_time = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms_actual:
            # Check if interrupt handler buffered a packet during sleep_ms(10)
            if self._rx_buffer is not None:
                raw_payload = self._rx_buffer
                self._rx_buffer = None
                msg = self._process_raw_payload(raw_payload)
                if msg:
                    self._lora.recv()
                    return msg
                self._lora.recv()
                continue

            # Fallback: poll IRQ register (fires when interrupt didn't steal the packet)
            irq_flags = self._lora._read(0x12)
            
            if irq_flags & 0x40:  # RxDone - Message reçu
                self._lora._write(0x12, 0xFF)  # Clear IRQ
                
                try:
                    raw_payload = self._lora._read_payload()
                    msg = self._process_raw_payload(raw_payload)
                    if msg:
                        self._lora.recv()
                        return msg
                except Exception as e:
                    log(f"Receive error: {e}")
                
                self._lora.recv()
            elif irq_flags & 0x20:  # CRC Error
                log("CRC Error detected")
                self._lora._write(0x12, 0xFF)  # Clear IRQ
                self._lora.recv()
            
            time.sleep_ms(10)
        
        log("No message received within timeout")
        return None
    
    def disconnect(self):
        log("Deconnecte")
        self._lora.sleep()
    
    def get_stats(self):
        return self._stats.copy()
    
    # ===========================================================
    # PRIVATE METHODS
    # ===========================================================
    
    def _on_receive(self, payload):
        """Callback appelé par la lib LoRa quand un message arrive."""
        self._rx_buffer = payload

    def _process_raw_payload(self, raw_payload):
        """Decode, extract frame and parse a raw bytes payload. Returns message dict or None."""
        if not raw_payload:
            log("DIAG: _process_raw_payload got empty payload")
            return None
        try:
            msg_str = self._decode_payload(raw_payload)
            if not msg_str:
                log("DIAG: _decode_payload returned None")
                return None
            frame = self._extract_frame(msg_str)
            if not frame:
                log(f"DIAG: _extract_frame failed for msg: {msg_str}")
                return None
            message = self._parse_message(frame)
            if not message:
                log(f"DIAG: _parse_message failed for frame: {frame}")
                return None
            self._stats['received'] += 1
            log(f"Message received: {frame}")
            return message
        except Exception as e:
            log(f"DIAG: _process_raw_payload error: {e}")
            return None
    
    def _decode_payload(self, payload):
        """Décode les bytes en string avec nettoyage des headers pourris."""
        if not payload:
            log("DEBUG: Empty payload")
            return None
        
        try:
            if isinstance(payload, (bytes, bytearray)):
                # Nettoyer les headers pourris (FF FF 00 00) au début
                clean_payload = self._clean_payload(payload)
                log(f"DEBUG: Cleaned payload: {clean_payload}")
                
                # Essayer UTF-8 avec ignore des erreurs
                try:
                    decoded = clean_payload.decode('utf-8', 'ignore').strip()
                    log(f"DEBUG: UTF-8 decode successful: {decoded}")
                    return decoded
                except Exception as e1:
                    log(f"DEBUG: UTF-8 decode failed: {e1}")
                    
                # Essayer latin-1 qui accepte tous les bytes
                try:
                    decoded = clean_payload.decode('latin-1').strip()
                    log(f"DEBUG: Latin-1 decode: {decoded}")
                    return decoded
                except Exception as e2:
                    log(f"DEBUG: Latin-1 decode failed: {e2}")
            
            # Si ce n'est pas des bytes, essayer de convertir en string
            return str(payload).strip()
        except Exception as e:
            log(f"Erreur decodage final: {e}")
            return None
    
    def _clean_payload(self, payload):
        """Nettoie les headers pourris (FF FF 00 00) au début du payload."""
        if not payload or len(payload) < 4:
            return payload
        
        # Vérifier si les 4 premiers bytes sont FF FF 00 00
        if payload[0] == 0xFF and payload[1] == 0xFF and payload[2] == 0x00 and payload[3] == 0x00:
            log("DEBUG: Removing corrupt header (FF FF 00 00)")
            return payload[4:]  # Retourner le payload sans les 4 premiers bytes
        
        return payload

    def _build_message(self, payload):
        """
        Format payload for LoRa transmission.
        Input: {"type": "D", "uid": "ESP32-001", "timestamp": 1234567890, "data": {"1TA": 25, "1HA": 45}}
        Format: B|TYPE|TIMESTAMP|UID|DATA|E
        """
        if not payload:
            return None

        # Extraire les données
        msg_type = payload.get("type", "D")
        uid = self._uid
        timestamp = payload.get("timestamp", "")
        data = payload.get("data", {})

        # Formater les données en chaîne LoRa
        if isinstance(data, dict):
            if msg_type == 'D':
                data_str = ";".join([f"{k}{v}" for k, v in data.items()])
            elif msg_type == 'S':
                # Explicit order: status;count - dict.values() order is not guaranteed in MicroPython
                data_str = "{};{}".format(data.get('status', 'O'), data.get('count', 0))
            elif msg_type == 'T':
                data_str = "{};{};{};{}".format(data.get('alert_id', 'O'), data.get('level', 'C'), data.get('identifier', ''), data.get('value', 0))
            else:
                data_str = ";".join([str(v) for v in data.values()])
        else:
            data_str = str(data)

        # Construire le message LoRa
        return f"B|{msg_type}|{timestamp}|{uid}|{data_str}|E"
    
    def _extract_frame(self, raw):
        """Extrait la trame B|...|E du message brut."""
        idx = raw.find('B|')
        if idx == -1:
            return None
        
        clean = raw[idx:]
        end_idx = clean.find('|E')
        if end_idx == -1:
            return None
        
        return clean[:end_idx + 2]
    
    def _parse_message(self, frame):
        """
        Parse une trame LoRa et valide le format de base.
        Format: B|TYPE|TIMESTAMP|UID|DATA|E
        
        Args:
            frame: Trame brute au format B|...|E
            
        Returns:
            Dictionnaire avec les champs du message ou None si invalide
        """
        try:
            parts = frame.split('|')
            
            # Validation du format de base
            if len(parts) < 5 or parts[0] != 'B' or parts[-1] != 'E':
                log("Invalid message format - missing B| or |E")
                return None
            
            # Validation du type de message
            msg_type = parts[1]
            valid_types = ['D', 'ACK', 'PA', 'P', 'U', 'A', 'C', 'S', 'T']  # Types de messages connus
            if msg_type not in valid_types:
                log(f"Unknown message type: {msg_type}")
                return None
            
            # Validation de l'UID (ne doit pas être vide)
            uid = parts[3]
            if not uid or len(uid.strip()) == 0:
                log("Invalid message - empty UID")
                return None
            
            return {
                'type': msg_type,
                'timestamp': parts[2],
                'uid': uid,
                'data': parts[4] if len(parts) > 5 else ''
            }
        except Exception as e:
            log(f"Message parse error: {e}")
            return None