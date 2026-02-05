import json
import os
import time

class PairingManager:
    """Gestionnaire du pairing"""
    
    def __init__(self, lora, uid):
        self.lora = lora
        self.uid = uid
        self.parent_id = self._charger()
    
    def est_connecte(self):
        return self.parent_id is not None
    
    def _charger(self):
        """Charge l'ID du parent depuis config.json"""
        try:
            with open('config.json', 'r') as f:
                return json.load(f).get('parent_id')
        except:
            return None
    
    def _sauvegarder(self):
        """Sauvegarde l'ID du parent"""
        try:
            with open('config.json', 'w') as f:
                json.dump({'parent_id': self.parent_id}, f)
            print(f"Parent sauvegardé: {self.parent_id}")
        except:
            pass
    
    def _effacer(self):
        """Efface la config"""
        try:
            os.remove('config.json')
            self.parent_id = None
        except:
            pass
    
    def lancer_pairing(self, construire_msg, parser_msg, timeout_ms=5000):
        """
        Lance le pairing avec la parent
        """
        print("\nPAIRING...")
        
        msg = construire_msg("P", "")
        self._envoyer(msg)
        
        self._ecouter()
        
        print(f"Écoute...")
        start = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            if (self.lora._read(0x12) & 0x40):
                self.lora._write(0x12, 0xFF)
                
                try:
                    raw = self.lora._read_payload()
                    msg_str = raw.decode('utf-8', 'ignore').strip()
                    parsed = parser_msg(msg_str)
                    
                    if parsed and parsed.get("type") == "PA":
                        self.parent_id = parsed.get("uid")
                        print(f"Connecté: {self.parent_id}")
                        self._sauvegarder()
                        return True
                except:
                    pass
                
                self.lora.recv()
            
            time.sleep_ms(10)
        
        return False
    
    def lancer_unpairing(self, construire_msg):
        """
        Lance l'unpair avec la gateway
        
        Args:
            construire_msg: Fonction(type, datas) -> message string
        """
        print("\n👋 UNPAIR...")
        msg = construire_msg("U", "")
        self._envoyer(msg)
        self._effacer()
    
    def verifier_unpair(self, parsed_msg):
        """
        Vérifie si un message est un ordre UNPAIR pour cet ESP32
        
        Args:
            parsed_msg: Message parsé (dict)
        
        Returns:
            bool: True si ordre UNPAIR pour cet ESP32
        """
        if not parsed_msg or parsed_msg.get("type") != "U":
            return False
        
        target = parsed_msg.get("datas", "")
        return target == "" or target == self.uid
    
    def _envoyer(self, message):
        """Envoie un message en rafale (3x)"""
        payload = message.encode('utf-8')
        print(f"📤", end="")
        for i in range(3):
            self.lora.send(payload)
            time.sleep(0.1)
            print(".", end="")
        print(" OK")
    
    def _ecouter(self):
        """Prépare le module LoRa pour écouter"""
        self.lora._write(0x01, 0x81)  # Standby
        time.sleep(0.01)
        self.lora._write(0x12, 0xFF)  # Clear IRQ
        self.lora.recv()  # RX mode