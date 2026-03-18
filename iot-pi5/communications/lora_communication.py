"""
Communication LoRa - Gestion de la radio LoRa via adafruit_rfm9x
"""
from typing import Optional
import time
import board
import busio
import digitalio
import adafruit_rfm9x
from models.messages import LoRaMessage


class LoRaCommunication:
    """
    Gère la communication LoRa avec les devices enfants
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.rfm9x = None
        self._timeout = config.get("listen_timeout", 5.0)
        self._anti_doublon_sec = 3.0
        self._last_msg = ""
        self._last_msg_time = 0

        self.message_callback = None  # Callback pour les messages entrants
        
        # Stats
        self.stats = {
            "received": 0,
            "sent": 0,
            "errors": 0
        }
    

    def initialize(self):
        """Initialise le module LoRa RFM9x"""
        print(">>> [DEBUG] Appel de LoRaCommunication.initialize()")
        try:
            CS = digitalio.DigitalInOut(board.D5)
            RESET = digitalio.DigitalInOut(board.D25)
            spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
            
            self.rfm9x = adafruit_rfm9x.RFM9x(
                spi, CS, RESET,
                self.config.get("frequency", 433.1)
            )
            # Configurer un buffer de réception plus grand
            self.rfm9x.signal_bandwidth = self.config.get("bandwidth", 500000)
            self.rfm9x.spreading_factor = self.config.get("spreading_factor", 10)
            self.rfm9x.coding_rate = self.config.get("coding_rate", 5)
            self.rfm9x.preamble_length = self.config.get("preamble_length", 8)
            self.rfm9x.enable_crc = self.config.get("crc", False)
            
            # Sync word - convertir en int si string
            sync_word = self.config.get("sync_word", 0x12)
            if isinstance(sync_word, str):
                sync_word = int(sync_word, 16)  # Base 16 pour hexadécimal
            elif not isinstance(sync_word, int):
                sync_word = int(sync_word)  # Convertir d'autres types
            
            # Écrire le sync word
            self.rfm9x._write_u8(0x39, sync_word)
            
            # Mode écoute
            self.rfm9x.idle()
            time.sleep(0.01)
            self.rfm9x.listen()
            time.sleep(0.01)
            
            print("📡 LoRa initialisé avec succès")
            
        except Exception as e:
            print(f"Erreur init LoRa: {e}")
            self.rfm9x = None

    def set_message_callback(self, callback):
        """Définit un callback pour les messages LoRa entrants."""
        self.message_callback = callback

    
    def set_timeout(self, timeout: float):
        self._timeout = timeout
    
    def force_listen_mode(self):
        """Force le module en mode écoute."""
        if self.rfm9x:
            try:
                self.rfm9x.idle()
                time.sleep(0.01)
                self.rfm9x.listen()
                time.sleep(0.01)
                print("DEBUG: Forced listen mode")
            except Exception as e:
                print(f"Erreur forçage mode écoute: {e}")

    def receive(self):
        """Reçoit un message et appelle le callback."""
        message = self._receive_raw()
        if message and self.message_callback:
            self.message_callback(message)
        return message
    
    def _receive_raw(self) -> Optional[str]:
        """
        Écoute et reçoit un message LoRa.
        
        Returns:
            str: message brut (format B|...|E) ou None
        """
        print("[LoRaCommunication.receive] ENTRY - Waiting for message...")
        
        if not self.rfm9x:
            print("[LoRaCommunication.receive] ERROR - LoRa not initialized")
            return None
        
        try:
            # Recevoir avec timeout
            packet = self.rfm9x.receive(timeout=2.0)
            
            if not packet:
                print("[LoRaCommunication.receive] EXIT - No packet received (timeout)")
                return None
            
            # Convertir en string
            msg_str = str(packet, 'utf-8', 'ignore').strip()
            print(f"[LoRaCommunication.receive] Raw message: {msg_str}")
            
            # Vérification anti-doublon
            current_time = time.time()
            if msg_str == self._last_msg and (current_time - self._last_msg_time) < self._anti_doublon_sec:
                print(f"[LoRaCommunication.receive] Anti-doublon: duplicate message ignored")
                return None
            
            self._last_msg = msg_str
            self._last_msg_time = current_time
            
            # Validation du format de base
            if not msg_str.startswith("B|") or not msg_str.endswith("|E"):
                print(f"[LoRaCommunication.receive] Invalid format: missing B| or |E")
                return None
            
            # Parser avec LoRaMessage
            lora_msg = LoRaMessage.from_lora_format(msg_str)
            if lora_msg:
                print(f"[LoRaCommunication.receive] Valid message received: {msg_str}")
                self.stats["received"] += 1
                print("[LoRaCommunication.receive] EXIT - Message returned")
                return msg_str
            else:
                print(f"[LoRaCommunication.receive] Invalid LoRa message format")
                self.stats["errors"] += 1
                return None
            
        except Exception as e:
            print(f"[LoRaCommunication.receive] ERROR: {e}")
            self.stats["errors"] += 1
            print("[LoRaCommunication.receive] EXIT - Error")
            return None
    
    def send(self, message: str, retries: int = 3) -> bool:
        """
        Envoie un message LoRa.
        
        Args:
            message: message au format B|...|E
            retries: nombre de tentatives
        """
        if not self.rfm9x:
            print(f"LoRa non initialisé, message ignoré: {message}")
            return False
        
        try:
            payload = message.encode('utf-8')
            
            for i in range(retries):
                self.rfm9x.send(payload)
                time.sleep(0.15)
            
            self.stats["sent"] += 1
            print(f"LoRa envoyé: {message}")
            
            # Remettre en écoute
            self.rfm9x.idle()
            time.sleep(0.01)
            self.rfm9x.listen()
            
            return True
            
        except Exception as e:
            print(f"Erreur envoi LoRa: {e}")
            self.stats["errors"] += 1
            return False
    
    def send_ack(self, target_uid: str, gateway_uid: str = "GATEWAY_PI") -> bool:
        """
        Envoie un ACK à un device ESP32.
        
        Format: B|ACK|TIMESTAMP|GATEWAY_UID|TARGET_UID|E
        
        Args:
            target_uid: UID du device cible (ESP32)
            gateway_uid: UID du gateway (par défaut: GATEWAY_PI)
            
        Returns:
            True si l'ACK a été envoyé avec succès, False sinon
        """
        print(f"[LoRaCommunication.send_ack] ENTRY - Sending ACK to {target_uid}")
        
        if not self.rfm9x:
            print("[LoRaCommunication.send_ack] ERROR - LoRa not initialized")
            return False
        
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            ack_message = f"B|ACK|{timestamp}|{target_uid}|E"
            
            print(f"[LoRaCommunication.send_ack] ACK message: {ack_message}")
            
            # Envoyer avec 3 tentatives
            result = self.send(ack_message, retries=3)
            
            if result:
                print(f"[LoRaCommunication.send_ack] SUCCESS - ACK sent to {target_uid}")
                self.stats["sent"] += 1
            else:
                print(f"[LoRaCommunication.send_ack] FAILED - Could not send ACK to {target_uid}")
            
            print("[LoRaCommunication.send_ack] EXIT")
            return result
            
        except Exception as e:
            print(f"[LoRaCommunication.send_ack] ERROR: {e}")
            self.stats["errors"] += 1
            return False
    
    def shutdown(self):
        if self.rfm9x:
            try:
                self.rfm9x.idle()
            except:
                pass
        print("📡 LoRa arrêté")
    
