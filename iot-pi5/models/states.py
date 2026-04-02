"""
États du système et gestion des états
"""
from abc import ABC, abstractmethod
from enum import Enum


class SystemState(Enum):
    """États possibles du système"""
    NORMAL = "normal"          # Fonctionnement normal
    PAIRING = "pairing"         # Mode appariement actif
    MAINTENANCE = "maintenance" # Mode maintenance
    EMERGENCY = "emergency"     # Mode urgence


class State(ABC):
    """Interface de base pour les états"""
    
    def __init__(self, gateway_core):
        self.gateway = gateway_core
    
    @abstractmethod
    def handle(self):
        """Gère la logique spécifique à l'état"""
        pass
    
    @abstractmethod
    def enter(self):
        """Actions à effectuer lors de l'entrée dans l'état"""
        pass
    
    @abstractmethod
    def exit(self):
        """Actions à effectuer lors de la sortie de l'état"""
        pass


class NormalState(State):
    """État de fonctionnement normal"""
    
    def handle(self):
        """Logique normale - écoute LoRa et MQTT"""
        # La logique principale est gérée par le GatewayCore
        pass
    
    def enter(self):
        """Active le mode normal"""
        print("🔄 Système en mode NORMAL")
        self.gateway.lora_comm.set_timeout(3.0)  # Timeout normal
    
    def exit(self):
        """Quitte le mode normal"""
        pass


class PairingState(State):
    """
    État de mode appariement.
    
    Flow:
    1. Broadcast un message P toutes les 2s via LoRa (uid=parent_id)
    2. ESP32 reçoit le P, extrait parent_id, génère son propre UID (machine.unique_id)
    3. ESP32 renvoie un PA avec son UID
    4. Pi5 reçoit le PA → enregistre le child → retour en NORMAL
    5. Timeout après {duration}s si aucun PA reçu
    """
    
    BROADCAST_INTERVAL = 2.0  # secondes entre chaque broadcast
    
    def __init__(self, gateway_core, duration=30, ack_id=None):
        super().__init__(gateway_core)
        self.duration = duration
        self.ack_id = ack_id
        self.end_time = 0
        self._last_broadcast = 0
    
    def handle(self):
        """Broadcast P message périodiquement et vérifie le timeout."""
        import time
        now = time.time()
        
        if now > self.end_time:
            print("[PairingState] Timeout - aucun device pairé")
            self.gateway.set_state(SystemState.NORMAL)
            return
        
        if now - self._last_broadcast >= self.BROADCAST_INTERVAL:
            self._broadcast_pairing()
            self._last_broadcast = now
    
    def enter(self):
        """Active le mode pairing."""
        import time
        self.end_time = time.time() + self.duration
        self._last_broadcast = 0
        print(f"[PairingState] Mode PAIRING activé ({self.duration}s)")
    
    def exit(self):
        """Désactive le mode pairing."""
        print("[PairingState] Mode PAIRING désactivé")
    
    def _broadcast_pairing(self):
        """Envoie un message P via LoRa: B|P|timestamp|parent_id||E"""
        from models.messages import LoRaMessage, MessageType
        from datetime import datetime
        
        parent_id = self.gateway.child_repo.get_parent_id()
        msg = LoRaMessage(
            message_type=MessageType.PAIRING,
            timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            uid=parent_id,
            data="",
        )
        self.gateway.lora_comm.send(msg.to_lora_format())
        remaining = int(self.end_time - __import__('time').time())
        print(f"[PairingState] Broadcast P → parent_id={parent_id} ({remaining}s left)")


class MaintenanceState(State):
    """État de maintenance"""
    
    def handle(self):
        """Logique de maintenance"""
        # Peut être utilisé pour des mises à jour, etc.
        pass
    
    def enter(self):
        """Active le mode maintenance"""
        print("🛠️ Mode MAINTENANCE activé")
        
        self.gateway.mqtt_comm.publish(
            topic="garden/system/state",
            payload={"state": "maintenance"},
            qos=0
        )
    
    def exit(self):
        """Désactive le mode maintenance"""
        print("🛠️ Mode MAINTENANCE désactivé")
        
        self.gateway.mqtt_comm.publish(
            topic="garden/system/state",
            payload={"state": "normal"},
            qos=0
        )
