# main.py
"""Point d'entrée principal du système Garden IoT"""

import time
import gest_noeud
from services import (
    MqttService, 
    LoRaService, 
    PairingService, 
    AlertService,
    MessageRouter
)
from config import *

class GardenIoTSystem:
    
    def __init__(self):
        self._init_services()
        self._connect_mqtt()
    
    
    def _init_services(self):
        """Initialise tous les services"""
        gest_noeud.init()
        self.parent_id = gest_noeud.get_parent_id()
        print(f"Parent ID: {self.parent_id}\n")
    
        
        # Services
        self.mqtt = MqttService()
        self.lora = LoRaService()
        self.pairing_service = PairingService()
        self.alerts = AlertService(self.lora, self.mqtt, gest_noeud)
        self.router = MessageRouter(
            self.lora, 
            self.mqtt, 
            gest_noeud, 
            self.alerts, 
            self.parent_id
        )
        
        # Configuration du callback MQTT
        self.mqtt.set_command_callback(self._handle_mqtt_command)
    
    def _connect_mqtt(self):
        """Connexion au broker MQTT"""
        self.mqtt.connect()
        time.sleep(1)
    
    # ============================================
    # CALLBACKS
    # ============================================
    
    def _handle_mqtt_command(self, topic: str, payload: str):
        """Callback pour les commandes MQTT"""
        if "garden/alert" in topic:
            self.alerts.handle_mqtt_alert_command(payload)
        if "garden/pairing" in topic:
            try:
                data = json.loads(payload)
                if data.get("event") == "pairing_request":
                    pairing_event = self.pairing_service.start_pairing()
                    
                    if pairing_event:
                        self._handle_pairing_event(pairing_event)
                else:
                    print(f"Événement de pairing inconnu: {data.get('event')}")
            except json.JSONDecodeError:
                print(f"Payload non-JSON reçu sur {topic}")
        elif commande == "unpair":
                uid_a_supprimer = data.get("uid")
                
                if uid_a_supprimer:
                    print(f"UNPAIR direct pour {uid_a_supprimer}")
                    
                    msg_unpair = self.router.parser.build_unpair_command(self.parent_id, uid_a_supprimer)
                    

                    self.lora.send_burst(msg_unpair)
    
    def _handle_pairing_event(self, event: dict):
        """Gestion des événements de pairing (Début et Fin)"""
        event_type = event.get("event")
        
        if event_type == "pairing_start":
            self.mqtt.publish_event("pairing", {
                "event": "pairing_start",
                "duration": event.get("duration", 60)
            })
            
        elif event_type == "pairing_end":
            self.mqtt.publish_event("pairing", {
                "event": "pairing_end"
            })
    
    # ============================================
    # BOUCLE PRINCIPALE
    # ============================================
    
    def run(self):
        try:
            while True:
                # 1. Vérifier si le temps de pairing est écoulé (Timeout)
                timeout_event = self.pairing_service.check_timeout()
                if timeout_event:
                    self._handle_pairing_event(timeout_event)
                
                # 2. Recevoir et router les messages LoRa
                timeout_rx = TIMEOUT_RX_PAIRING if self.pairing_service.is_pairing_active() else TIMEOUT_RX_NORMAL
                lora_msg = self.lora.receive(timeout=timeout_rx)
                
                if lora_msg:
                    self.router.route_message(lora_msg, self.pairing_service.is_pairing_active())
                
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            self._shutdown("Arrêt demandé par l'utilisateur")
        except Exception as e:
            self._shutdown(f"Erreur fatale: {e}", show_traceback=True)
    
    def _shutdown(self, reason: str, show_traceback: bool = False):
        """Arrêt propre du système"""
        print("\n\n" + "="*60)
        print(f"{reason}")
        print("="*60)
        
        if show_traceback:
            import traceback
            traceback.print_exc()
        
        self.mqtt.disconnect()

if __name__ == "__main__":
    system = GardenIoTSystem()
    system.run()
