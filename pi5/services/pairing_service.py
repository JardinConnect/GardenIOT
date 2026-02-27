"""Gestionnaire du mode Pairing (100% Logiciel/MQTT)"""

import time
from config import DUREE_PAIRING_SEC

class PairingService:
    """Gère l'état d'ouverture du réseau LoRa"""
    
    def __init__(self):
        self.pairing_mode = False
        self.pairing_end_time = 0
    
    def start_pairing(self) -> dict | None:
        """Déclenche le mode pairing suite à un ordre MQTT"""
        if not self.pairing_mode:
            print(f"\n🌐 MODE PAIRING ({DUREE_PAIRING_SEC}s)")
            self.pairing_mode = True
            self.pairing_end_time = time.time() + DUREE_PAIRING_SEC
            
            return {
                "event": "pairing_start",
                "duration": DUREE_PAIRING_SEC
            }
        return None
        
    def check_timeout(self) -> dict | None:
        """Vérifie si le temps imparti est écoulé (à appeler dans la boucle principale)"""
        if self.pairing_mode and time.time() > self.pairing_end_time:
            print("🔒 Fin de la fenêtre de Pairing (Timeout)")
            self.pairing_mode = False
            return {"event": "pairing_end"}
            
        return None
    
    def is_pairing_active(self) -> bool:
        """Retourne True si le mode pairing est ouvert"""
        return self.pairing_mode
