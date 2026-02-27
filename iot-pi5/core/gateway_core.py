"""
Cœur du système Gateway - Classe principale
"""
import time
import json
from typing import Optional, Dict, Any
from ..models.states import SystemState, NormalState, PairingState, MaintenanceState
from ..models.messages import LoRaMessage, MqttMessage, MessageType


class GatewayCore:
    """
    Classe principale du système Gateway
    Coordonne tous les composants et gère le flux principal
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialise le système Gateway"""
        self.config = config
        self.running = False
        
        # Composants
        self.lora_comm = None
        self.mqtt_comm = None
        self.child_repo = None
        self.message_router = None
        
        # État du système
        self.current_state = None
        self.states = {
            SystemState.NORMAL: NormalState(self),
            SystemState.PAIRING: PairingState(self, duration=config.get("pairing_duration", 30)),
            SystemState.MAINTENANCE: MaintenanceState(self)
        }
        
        # Statistiques
        self.stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "errors": 0,
            "uptime": 0
        }
    
    def initialize_components(self, lora_comm, mqtt_comm, child_repo, message_router):
        """Initialise les composants du système"""
        self.lora_comm = lora_comm
        self.mqtt_comm = mqtt_comm
        self.child_repo = child_repo
        self.message_router = message_router
        
        # Initialiser les composants
        self.lora_comm.initialize()
        self.mqtt_comm.initialize()
        self.child_repo.initialize()
    
    def start(self):
        """Démarre le système Gateway"""
        print("🚀 Démarrage du système Gateway...")
        
        # Passer en état normal
        self.set_state(SystemState.NORMAL)
        
        self.running = True
        self.stats["uptime"] = time.time()
        
        print("✅ Système prêt")
        
        # Boucle principale
        self.main_loop()
    
    def main_loop(self):
        """Boucle principale du système"""
        try:
            while self.running:
                # 1. Gérer l'état courant
                self.current_state.handle()
                
                # 2. Vérifier les messages LoRa
                self.process_lora_messages()
                
                # 3. Vérifier les messages MQTT
                self.process_mqtt_messages()
                
                # 4. Mettre à jour les statistiques
                self.stats["uptime"] = time.time() - self.stats["uptime"]
                
                # Petit délai pour éviter de saturer le CPU
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            self.shutdown("Arrêt demandé par l'utilisateur")
        except Exception as e:
            self.shutdown(f"Erreur fatale: {e}", True)
    
    def process_lora_messages(self):
        """Traite les messages LoRa entrants"""
        try:
            message = self.lora_comm.receive()
            if message:
                self.stats["messages_received"] += 1
                
                # Parser le message
                lora_msg = LoRaMessage.from_lora_format(message)
                if lora_msg:
                    print(f"📡 LoRa reçu: {lora_msg.message_type.value} de {lora_msg.uid}")
                    
                    # Router le message
                    self.message_router.route_from_lora(lora_msg)
                else:
                    print(f"⚠️ Message LoRa invalide: {message}")
                    self.stats["errors"] += 1
        
        except Exception as e:
            print(f"❌ Erreur traitement LoRa: {e}")
            self.stats["errors"] += 1
    
    def process_mqtt_messages(self):
        """Traite les messages MQTT entrants"""
        try:
            # Le MQTT est géré par callbacks, mais on peut vérifier l'état de la connexion
            if not self.mqtt_comm.is_connected():
                print("⚠️ Connexion MQTT perdue, tentative de reconnexion...")
                self.mqtt_comm.reconnect()
        
        except Exception as e:
            print(f"❌ Erreur traitement MQTT: {e}")
            self.stats["errors"] += 1
    
    def set_state(self, state: SystemState):
        """Change l'état du système"""
        if self.current_state:
            self.current_state.exit()
        
        self.current_state = self.states[state]
        self.current_state.enter()
    
    def trigger_pairing_mode(self):
        """Active le mode pairing"""
        if self.current_state and isinstance(self.current_state, PairingState):
            print("ℹ️ Mode pairing déjà actif")
            return
        
        print("🔗 Activation du mode pairing...")
        self.set_state(SystemState.PAIRING)
    
    def handle_button_press(self, duration: float):
        """Gère l'appui sur le bouton physique"""
        if duration >= 15:
            print("🗑️ Reset complet des enfants")
            self.child_repo.remove_all_children()
        elif duration >= 3:
            print("🔗 Activation pairing par bouton")
            self.trigger_pairing_mode()
    
    def shutdown(self, reason: str, error: bool = False):
        """Arrêt propre du système"""
        print(f"\n🛑 {reason}")
        
        if error:
            import traceback
            traceback.print_exc()
        
        # Arrêter les composants
        if self.mqtt_comm:
            self.mqtt_comm.disconnect()
        
        if self.lora_comm:
            self.lora_comm.shutdown()
        
        print("👋 Système arrêté")
        self.running = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du système"""
        return self.stats.copy()
    
    def get_system_info(self) -> Dict[str, Any]:
        """Retourne les informations système"""
        return {
            "state": self.current_state.__class__.__name__ if self.current_state else "unknown",
            "children_count": len(self.child_repo.get_all_children()) if self.child_repo else 0,
            "uptime": self.stats.get("uptime", 0),
            "messages_received": self.stats.get("messages_received", 0),
            "messages_sent": self.stats.get("messages_sent", 0)
        }
