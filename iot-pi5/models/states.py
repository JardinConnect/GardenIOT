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
    """État de mode appariement"""
    
    def __init__(self, gateway_core, duration=30):
        super().__init__(gateway_core)
        self.duration = duration
        self.end_time = 0
    
    def handle(self):
        """Gère la temporisation du mode pairing"""
        import time
        if time.time() > self.end_time:
            self.gateway.set_state(SystemState.NORMAL)
    
    def enter(self):
        """Active le mode pairing"""
        import time
        print(f"🔗 Mode PAIRING activé ({self.duration}s)")
        self.end_time = time.time() + self.duration
        self.gateway.lora_comm.set_timeout(3.0)  # Timeout plus long pour pairing
        
        # Notifier via MQTT
        self.gateway.mqtt_comm.publish(
            topic="garden/system/state",
            payload={"state": "pairing", "duration": self.duration},
            qos=0
        )
    
    def exit(self):
        """Désactive le mode pairing"""
        print("🔗 Mode PAIRING désactivé")
        
        # Notifier via MQTT
        self.gateway.mqtt_comm.publish(
            topic="garden/system/state",
            payload={"state": "normal"},
            qos=0
        )


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
