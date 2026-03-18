"""
Cœur du système Gateway - Classe principale
"""
import time
import json
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from models.states import SystemState, NormalState, PairingState, MaintenanceState
from models.messages import LoRaMessage, MqttMessage, MessageType
from core.event_bus import EventBus
from core.message_queu import MessageQueue

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
        self.event_bus = EventBus()
        self.message_queue = None
        
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

        self.pending_messages = {}  # {esp_uid: [message1, message2, ...]
        self.lora_thread = None
        self.lora_running = False

    
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
        self.message_queue = MessageQueue(self)

        # Lier le callback MQTT et LoRa au MessageRouter
        self.mqtt_comm.set_message_callback(self.message_router.route_from_mqtt)
        self.lora_comm.set_message_callback(self.message_router.route_from_lora)

        # S'abonner aux événements
        # self.event_bus.subscribe("esp32.available", self._on_esp_available)
    
    def start(self):
        """Démarre le système Gateway"""
        print("🚀 Démarrage du système Gateway...")
        
        # Passer en état normal
        self.set_state(SystemState.NORMAL)
        
        self.running = True
        self.stats["uptime"] = time.time()
        
        # Démarrer le thread LoRa
        self._start_lora_thread()
        
        print(" Système prêt")
        
        # Boucle principale
        self.main_loop()
    
    def _start_lora_thread(self):
        """Démarre un thread dédié pour la réception LoRa"""
        import threading
        self.lora_running = True
        self.lora_thread = threading.Thread(
            target=self._lora_receiver_loop,
            name="LoRaReceiver",
            daemon=True
        )
        self.lora_thread.start()
        print("📡 Thread LoRa démarré")
    
    def _lora_receiver_loop(self):
        """Boucle dédiée à la réception des messages LoRa"""
        print("📡 Thread LoRa: démarré")
        try:
            while self.lora_running and self.running:
                try:
                    # Appeler receive() qui a déjà un timeout interne de 2 secondes
                    # et déclenchera le callback si message reçu
                    self.lora_comm.receive()
                    # Pas besoin de sleep ici car receive() est bloquant avec timeout
                except Exception as e:
                    print(f"📡 Thread LoRa: erreur {e}")
                    time.sleep(1)  # Attendre avant de réessayer en cas d'erreur
        except Exception as e:
            print(f"📡 Thread LoRa: erreur fatale {e}")
        print("📡 Thread LoRa: arrêté")

    def main_loop(self):
        """
        Boucle principale du système Gateway
        
        Cycle de traitement:
        1. Gère l'état courant (Normal/Pairing/Maintenance)
        2. Vérifie la connexion MQTT
        3. Met à jour les statistiques
        
        La réception LoRa est gérée par un thread dédié
        """
        start_time = time.time()
        try:
            while self.running:
                # 1. Gérer les états
                if self.current_state:
                    self.current_state.handle()

                # 2. Vérifier MQTT (déjà géré par callbacks)
                self.process_mqtt_messages()
                
                # 3. Mettre à jour les statistiques
                self.stats["uptime"] = time.time() - start_time
                
                # Petit délai pour éviter de saturer le CPU
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.shutdown("Arrêt demandé par l'utilisateur")
        except Exception as e:
            self.shutdown(f"Erreur fatale: {e}", True)
    

    # def process_lora_messages(self):
    #     """Traite les messages LoRa entrants"""
    #     try:
    #         message = self.lora_comm.receive()
            
    #         if not message:
    #             return
            
    #         self.stats["messages_received"] += 1
            
    #         # Parser le message
    #         lora_msg = LoRaMessage.from_lora_format(message)
            
    #         if not lora_msg:
    #             self.stats["errors"] += 1
    #             return

    #          # Publier un événement "ESP32 disponible"
    #         self.event_bus.publish("esp32.available", lora_msg.uid)
            
    #         # Envoyer ACK immédiatement (sauf pour les ACK entrants)
    #         if lora_msg.message_type != MessageType.ACK:
    #             gateway_uid = self.config.get("gateway_uid", "GATEWAY_PI")
    #             self.lora_comm.send_ack(lora_msg.uid, gateway_uid)
            
    #         # Router le message vers MQTT (sauf pour les ACK)
    #         if lora_msg.message_type != MessageType.ACK:
    #             self.message_router.route_from_lora(lora_msg)
                
    #     except Exception as e:
    #         self.stats["errors"] += 1
    
    # def _send_ack(self, target_uid: str):
    #     """Envoie un ACK à un device ESP32"""
    #     from datetime import datetime
    #     timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        
    #     # Format attendu par l'ESP32: B|ACK|timestamp|gateway_uid|TO:device_uid|E
    #     gateway_uid = self.config.get("gateway_uid", "GATEWAY_PI")
    #     ack_message = f"B|ACK|{timestamp}|{gateway_uid}|TO:{target_uid}|E"
        
    #     self.lora_comm.send(ack_message, retries=1)
    #     print(f"📤 ACK envoyé à {target_uid}")

    
    def process_mqtt_messages(self):
        """Traite les messages MQTT entrants"""
        try:
            # Le MQTT est géré par callbacks, mais on peut vérifier l'état de la connexion
            if not self.mqtt_comm.is_connected():
                print(" Connexion MQTT perdue, tentative de reconnexion...")
                self.mqtt_comm.reconnect()
        
        except Exception as e:
            print(f" Erreur traitement MQTT: {e}")
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
        
        # Arrêter le thread LoRa
        self.lora_running = False
        if self.lora_thread:
            self.lora_thread.join(timeout=5)
            if self.lora_thread.is_alive():
                print("⚠️  Thread LoRa n'a pas pu s'arrêter proprement")
        
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
