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
            except Exception as e:
                log(f"Send error: {e}")
                self._stats['errors'] += 1
                if attempt < self._max_retries:
                    time.sleep(0.5)
                continue
            
            # Si on n'attend pas d'ACK, c'est terminé
            if not expect_ack:
                self._lora.recv()  # Remettre en mode écoute
                log("Message sent (no ACK expected)")
                return True
            
            # Attendre l'ACK
            if self._wait_for_ack():
                log("ACK received successfully")
                self._lora.recv()  # Remettre en mode écoute
                return True
            else:
                log(f"No ACK received, retrying ({attempt}/{self._max_retries})")
                if attempt < self._max_retries:
                    time.sleep(0.5)
        
        # Toutes les tentatives ont échoué
        self._stats['ack_fail'] += 1
        log("Failed: no ACK after all attempts")
        self._lora.recv()  # Remettre en mode écoute
        return False
    
    def receive(self, timeout_ms=None):
        """
        Écoute un message LoRa en utilisant le polling direct.
        
        Args:
            timeout_ms: Timeout en millisecondes (None pour utiliser la config)
            
        Returns:
            Dictionnaire avec les champs du message ou None si timeout
        """
        timeout = (timeout_ms / 1000) if timeout_ms else self._listen_timeout
        log(f"Listening for messages (timeout: {timeout}s)")
        
        # Initialiser le mode réception
        self._lora._write(0x01, 0x81)  # Standby
        self._lora._write(0x12, 0xFF)  # Clear IRQ
        self._lora.recv()  # RX mode
        
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            # Lire le registre IRQ pour détecter les paquets
            irq_flags = self._lora._read(0x12)
            
            if irq_flags & 0x40:  # RxDone - Message reçu
                self._lora._write(0x12, 0xFF)  # Clear IRQ
                
                try:
                    # Lire le payload
                    raw_payload = self._lora._read_payload()
                    
                    if raw_payload:
                        # Décoder et parser le message
                        msg_str = self._decode_payload(raw_payload)
                        if msg_str:
                            frame = self._extract_frame(msg_str)
                            if frame:
                                message = self._parse_message(frame)
                                if message:
                                    self._stats['received'] += 1
                                    log(f"Message received: {frame}")
                                    self._lora.recv()  # Relancer l'écoute
                                    return message
                except Exception as e:
                    log(f"Receive error: {e}")
                
                # Relancer l'écoute après erreur
                self._lora.recv()
            elif irq_flags & 0x20:  # CRC Error
                log("CRC Error detected")
                self._lora._write(0x12, 0xFF)  # Clear IRQ
                self._lora.recv()  # Relancer l'écoute
            
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
    
    def _build_message(self, message):
        """
        Construit la trame LoRa.
        Format: B|TYPE|TIMESTAMP|UID|DATAS|E
        """
        msg_type = message.get('type', 'D')
        datas = message.get('datas', '')
        timestamp = self._get_timestamp()
        
        return f"B|{msg_type}|{timestamp}|{self._uid}|{datas}|E"
    
    def _get_timestamp(self):
        """Récupère le timestamp depuis le RTC ou fallback."""
        if self._rtc:
            try:
                dt = self._rtc.datetime()
                return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
                    dt[0], dt[1], dt[2], dt[4], dt[5], dt[6]
                )
            except:
                pass
        
        t = time.localtime()
        return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
            t[0], t[1], t[2], t[3], t[4], t[5]
        )
    
    def _wait_for_ack(self):
        """Attend un ACK pendant le timeout configuré."""
        log("Waiting for ACK response from Pi5...")
        timeout = self._ack_timeout / 1000  # Convert ms to seconds
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            remaining_time = timeout - (time.time() - start_time)
            log(f"Listening for ACK... {remaining_time:.1f}s remaining")
            
            # Check for incoming messages using polling
            received_message = self.receive(2000)  # 2 second timeout
            
            if received_message:
                msg_type = received_message.get('type', 'UNKNOWN')
                log(f"Received message type: {msg_type}")
                
                # Check if it's an ACK message (accept both 'ACK' and 'PA')
                if msg_type in ['ACK', 'PA']:
                    log("ACK received from Pi5!")
                    self._stats['ack_ok'] += 1
                    return True
                else:
                    log(f"Received non-ACK message: {received_message}")
            
            # Small delay to prevent busy waiting
            time.sleep(0.5)
        
        log("No ACK received within timeout")
        return False
    
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
        Format: B|TYPE|TIMESTAMP|UID|DATAS|E
        
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
            valid_types = ['D', 'ACK', 'PA', 'U', 'A', 'C']  # Types de messages connus
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
                'datas': parts[4] if len(parts) > 5 else ''
            }
        except Exception as e:
            log(f"Message parse error: {e}")
            return None