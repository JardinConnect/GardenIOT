"""
Communication LoRa - Gestion de la radio LoRa
"""
import time
import board
import busio
import digitalio
import adafruit_rfm9x
from typing import Optional


class LoRaCommunication:
    """
    Gère la communication LoRa avec les devices enfants
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.rfm9x = None
        self.timeout = 0.1  # Timeout par défaut
        self.initialized = False
    
    def initialize(self):
        """Initialise la radio LoRa"""
        try:
            print("📡 Initialisation LoRa...")
            
            # Configuration des broches
            CS = digitalio.DigitalInOut(self.config.get("cs_pin", board.D5))
            RESET = digitalio.DigitalInOut(self.config.get("reset_pin", board.D25))
            
            # Initialisation SPI
            spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
            
            # Initialisation radio
            self.rfm9x = adafruit_rfm9x.RFM9x(
                spi, CS, RESET, 
                frequency=self.config.get("frequency", 433.1)
            )
            
            # Configuration radio
            self.rfm9x.signal_bandwidth = self.config.get("bandwidth", 500000)
            self.rfm9x.spreading_factor = self.config.get("spreading_factor", 10)
            self.rfm9x.coding_rate = self.config.get("coding_rate", 5)
            self.rfm9x.preamble_length = self.config.get("preamble_length", 8)
            self.rfm9x.enable_crc = self.config.get("enable_crc", False)
            
            # Configuration spécifique
            if hasattr(self.rfm9x, '_write_u8'):
                self.rfm9x._write_u8(0x39, 0x12)
            
            # Passer en mode écoute
            self.rfm9x.idle()
            time.sleep(0.01)
            self.rfm9x.listen()
            time.sleep(0.01)
            
            self.initialized = True
            print("✅ LoRa initialisé avec succès")
            
        except Exception as e:
            print(f"❌ Échec initialisation LoRa: {e}")
            self.initialized = False
            raise
    
    def set_timeout(self, timeout: float):
        """Définit le timeout de réception"""
        self.timeout = timeout
    
    def receive(self) -> Optional[str]:
        """Reçoit un message LoRa"""
        if not self.initialized or not self.rfm9x:
            return None
        
        try:
            packet = self.rfm9x.receive(timeout=self.timeout)
            if packet:
                message = str(packet, 'utf-8', 'ignore').strip()
                return message if message else None
        except Exception as e:
            print(f"⚠️ Erreur réception LoRa: {e}")
        
        return None
    
    def send(self, message: str, retries: int = 3) -> bool:
        """Envoie un message LoRa"""
        if not self.initialized or not self.rfm9x:
            return False
        
        try:
            message_bytes = message.encode('utf-8')
            
            for attempt in range(retries):
                self.rfm9x.send(message_bytes)
                time.sleep(0.05)  # Petit délai entre les tentatives
                
                # Vérifier si l'envoi a réussi (pas de vrai ACK hardware)
                if attempt == retries - 1:
                    print(f"📤 Message LoRa envoyé (tentative {attempt + 1}/{retries}): {message[:50]}...")
                
                return True
                
        except Exception as e:
            print(f"❌ Échec envoi LoRa: {e}")
            return False
        
        return False
    
    def send_with_ack(self, message: str, target_uid: str, timeout: float = 2.0) -> bool:
        """Envoie un message avec attente d'ACK"""
        if not self.send(message):
            return False
        
        # Attendre un ACK (implémentation simplifiée)
        start_time = time.time()
        while time.time() - start_time < timeout:
            ack = self.receive()
            if ack and f"|PA|{target_uid}" in ack:
                print(f"✅ ACK reçu de {target_uid}")
                return True
            time.sleep(0.1)
        
        print(f"⏰ Timeout ACK pour {target_uid}")
        return False
    
    def shutdown(self):
        """Arrête proprement la radio LoRa"""
        if self.rfm9x:
            try:
                self.rfm9x.idle()
                print("📡 Radio LoRa arrêtée")
            except:
                pass
        self.initialized = False
    
    def is_initialized(self) -> bool:
        """Retourne True si la radio est initialisée"""
        return self.initialized
