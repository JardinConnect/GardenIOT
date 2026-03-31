# main.py
"""Système Garden IoT"""

import time
import gest_noeud
import json
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
            try:
                data = json.loads(payload)
                event_name = data.get("event")
                
                if event_name in ["alert_create", "alert_deleted", "alert_trigger"]:
                    return 

                if event_name in ["alert_config", "alert_sup"]:
                    self.alerts.handle_mqtt_alert_command(payload)
                else:
                    print(f"Alerte inconnue: {event_name}")

            except json.JSONDecodeError:
                print(f"Payload non-JSON reçu sur {topic}")
            except Exception as e:
                print(f"Erreur traitement commande alerte: {e}")
                
        if "garden/pairing" in topic:
            try:
                data = json.loads(payload)
                event_name = data.get("event")
            
                if event_name in ["pairing_start", "pairing_end", "pairing_sucess", "unpair_sucess"]:
                    return
                
                if event_name == "pairing_request":
                    pairing_event = self.pairing_service.start_pairing()
                    if pairing_event:
                        self._handle_pairing_event(pairing_event)
                        
                elif event_name == "request_unpair":
                    uid_a_supprimer = data.get("uid")
                    if uid_a_supprimer:
                        msg_unpair = self.router.parser.build_unpair_command(self.parent_id, uid_a_supprimer)
                        self.lora.send_burst(msg_unpair)
                        
                else:
                    print(f"Événement de pairing inconnu: {event_name}")
                    
            except json.JSONDecodeError:
                print(f"Payload non-JSON reçu sur {topic}")
    
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
                import time
                start_wait = time.time()

                lora_msg = self.lora.receive(timeout=timeout_rx)
                
                elapsed = time.time() - start_wait

                
                if lora_msg:
                    self.router.route_message(lora_msg, self.pairing_service.is_pairing_active())

                
                time.sleep(0.1)
                
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
