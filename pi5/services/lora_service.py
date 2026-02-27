# handlers/lora_handler.py
"""Gestionnaire LoRa"""

import time
import board
import busio
import digitalio
import adafruit_rfm9x
from config import *

class LoRaService:
    """Gère la communication LoRa"""
    
    def __init__(self):
        self._setup_hardware()
        self._last_msg = ""
        self._last_msg_time = 0
    
    def _setup_hardware(self):
        """Configure le module LoRa"""
        CS = digitalio.DigitalInOut(board.D5)
        RESET = digitalio.DigitalInOut(board.D25)
        spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
        
        self.rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, LORA_FREQUENCY)
        self.rfm9x.signal_bandwidth = LORA_SIGNAL_BANDWIDTH
        self.rfm9x.spreading_factor = LORA_SPREADING_FACTOR
        self.rfm9x.coding_rate = LORA_CODING_RATE
        self.rfm9x.preamble_length = LORA_PREAMBLE_LENGTH
        self.rfm9x.enable_crc = LORA_ENABLE_CRC
        self.rfm9x._write_u8(0x39, 0x12)
        
        # Passage en mode écoute
        print("Passage en mode écoute..")
        self.rfm9x.idle()
        time.sleep(0.01)
        self.rfm9x.listen()
        time.sleep(0.01)
    
    def receive(self, timeout: float = TIMEOUT_RX_NORMAL) -> str | None:
        """ Reception d'un message LoRa """
        try:
            packet = self.rfm9x.receive(timeout=timeout)
            
            if packet:
                msg = str(packet, 'utf-8', 'ignore').strip()
                
                # On ne retourne pas le message si on vient de le recevoir
                if msg == self._last_msg and (time.time() - self._last_msg_time) < ANTI_DOUBLON_SEC:
                    return None
                
                self._last_msg = msg
                self._last_msg_time = time.time()
                
                return msg
                
        except Exception as e:
            print(f"[LoRa] Erreur réception: {e}")
        
        return None
    
    def send(self, message: str, retry: int = 3, delay: float = 0.15):
        """ Envoie un message LoRa """
        try:
            payload = message.encode('utf-8')
            print(f"Envoi Message: {message}")
            
            for i in range(retry):
                self.rfm9x.send(payload)
                time.sleep(delay)
                if (i + 1) % 3 == 0:
                    print(".", end="")
            
        except Exception as e:
            print(f"Erreur envoi message LoRa: {e}")
    
    def send_ack_burst(self, message: str, duration: float = 2.0):
        """
        Envoie un message en rafale pendant la periode de pairing
        pour que l'esp32 récupère bien l'id du parent
        """
        try:
            payload = message.encode('utf-8')
            start = time.time()
            count = 0
            
            while time.time() - start < duration:
                self.rfm9x.send(payload)
                time.sleep(0.15)
                count += 1
                if count % 3 == 0:
                    print(".", end="")
            
            
        except Exception as e:
            print(f"Erreur envoi du message LoRa en rafale: {e}")
