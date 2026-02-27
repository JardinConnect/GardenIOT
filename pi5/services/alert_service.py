# services/alert_service.py
"""Service de gestion des alertes capteurs"""

import json
from .message_service import MessageService

class AlertService:
    """Gère la configuration, suppression et déclenchement des alertes"""
    
    def __init__(self, lora_service, mqtt_service, node_manager):
        self.lora = lora_service
        self.mqtt = mqtt_service
        self.nodes = node_manager
        self.parser = MessageService()
    
    def handle_mqtt_alert_command(self, payload: str):
        """Traite une demande MQTT de configuration ou suppression"""
        try:
            data = json.loads(payload)
            event_type = data.get("event")
            
            uid = data.get("uid")
            sensor_type = data.get("sensor_type")
            
            if not uid or not sensor_type:
                print(f"Commande invalide: uid ou sensor_type manquant")
                return
            
            if not self.nodes.est_autorise(uid):
                print(f"ESP32 {uid} non autorisé")
                return

            if event_type == "alert_config":
                self._configure_alert(uid, sensor_type, data.get("max"), data.get("min"))
            elif event_type == "alert_sup":
                self._delete_alert(uid, sensor_type)
            else:
                print(f"⚠Evénement d'alerte inconnu: {event_type}")
                
        except json.JSONDecodeError:
            print(f"Format JSON invalide: {payload}")
        except Exception as e:
            print(f"Erreur traitement alerte: {e}")
    
    def _configure_alert(self, uid: str, sensor_type: str, max_val, min_val):
        """Envoi de l'ordre de création via LoRa"""
        print(f"\nConfiguration d'alerte pour {uid}")
        print(f"   Capteur: {sensor_type} (Min: {min_val}, Max: {max_val})")
        
        lora_msg = self.parser.build_alert_config(uid, sensor_type, max_val, min_val)
        self.lora.send(lora_msg, retry=5)

    def _delete_alert(self, uid: str, sensor_type: str):
        """Envoi de l'ordre de suppression via LoRa"""
        print(f"\nSuppression d'alerte pour {uid} (Capteur: {sensor_type})")
        
        lora_msg = self.parser.build_alert_delete(uid, sensor_type)
        self.lora.send(lora_msg, retry=5)

    def handle_alert_ack(self, uid: str, sensor_type: str, action_type: str, max_val=None, min_val=None):
        """Appelé par MessageRouter quand l'ESP32 confirme l'action"""
        if action_type == "configured":
            event_name = "alert_create"
        else:
            event_name = "alert_deleted"
            
        print(f"Confirmation LoRa reçue : {event_name} pour {uid}")
        
        self.mqtt.publish_event("alert", { 
            "event": event_name,
            "uid": uid,
            "sensor_type": sensor_type,
            "max": max_val,
            "min": min_val
        })

    def handle_alert_triggered(self, uid: str, alert_data: dict):
        """Traite une alerte déclenchée par un ESP32 (La sirène)"""
        print(f"\nAlerte déclenchée sur la cellule {uid}")
        print(f"   Capteur: {alert_data.get('sensor_type')} = {alert_data.get('value')}")
        
        self.mqtt.publish_event("alert", {
            "event": "alert_trigger",
            "uid": uid,
            "sensor_type": alert_data.get("sensor_type"),
            "value": alert_data.get("value"),
            "max": alert_data.get("max"),
            "min": alert_data.get("min")
        })
