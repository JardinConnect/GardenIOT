# services/message_router.py
"""Routeur des messages LoRa"""

import json
from .message_service import MessageService
from config import MQTT_TOPIC_DATA

class MessageRouter:
    """Route et traite les messages LoRa reçus"""
    
    def __init__(self, lora_service, mqtt_service, node_manager, alert_service, parent_id: str):

        self.lora = lora_service
        self.mqtt = mqtt_service
        self.nodes = node_manager
        self.alerts = alert_service
        self.parent_id = parent_id
        self.parser = MessageService()
    
    def route_message(self, msg: str, is_pairing_active: bool):
        """
        Parse et route un message LoRa vers le bon handler
        
        """
        parsed = self.parser.parse(msg)
        
        if not parsed:
            print(f"Échec du parsing: {msg}")
            return
        
        
        if not parsed.get("uid"):
            print(f"UID manquant")
            return
        
        msg_type = parsed["type"]
        uid = parsed["uid"]
        
        # Router selon le type
        if msg_type == "P":  # Pairing
            self._handle_pairing(uid, is_pairing_active)
        
        elif msg_type == "D":  # Data
            self._handle_data(parsed)
        
        elif msg_type == "AT":  # Alert Triggered
            self._handle_alert_triggered(parsed)
            
        elif msg_type == "AC":  # Alert Configured
            self._handle_alert_ack(uid, parsed, "configured")
            
        elif msg_type == "AD":  # Alert Deleted
            self._handle_alert_ack(uid, parsed, "deleted")
        
        elif msg_type == "U":  # Unpair
            self._handle_unpair(uid)
        
        else:
            print(f"Type de message inconnu: {msg_type}")
    
    def _handle_pairing(self, uid: str, is_pairing_active: bool):
        """Gère une demande de pairing"""
        if not is_pairing_active:
            print(f"PAIRING REFUSÉ: {uid} (mode inactif)")
            return
        
        print(f"\nDEMANDE PAIRING de {uid}")
        
        # Ajouter l'enfant
        success = self.nodes.add_child(uid)
        
        if success:
            print(f"Nouvel enfant ajouté: {uid}")
        else:
            print(f"ESP32 déjà connu: {uid}")
        
        # Publier l'événement
        self.mqtt.publish_event("pairing", {
            "event": "pairing_sucess",
            "uid": uid,
        })
        
        # Envoyer l'ACK
        print(f"Envoi ACK PAIRING...", end="")
        ack_msg = self.parser.build_ack_pairing(self.parent_id, uid)
        self.lora.send_ack_burst(ack_msg)
    
    def _handle_data(self, parsed: dict):
        """Gère un message de données"""
        uid = parsed["uid"]
        is_known = self.nodes.est_autorise(uid)
        
        status = "OK" if is_known else "INCONNU"
        print(f"\n Reception des données de la cellule {uid}: {parsed['datas']}")
        
        if not is_known:
            print(f"[MQTT] Capteur non autorisé, message ignoré")
            return
        
        # Publier au format backend
        backend_format = self.parser.format_for_backend(parsed)
        if backend_format:
            self.mqtt.publish(MQTT_TOPIC_DATA, backend_format)
    
    def _handle_alert_triggered(self, parsed: dict):
        """Gère une alerte déclenchée"""
        uid = parsed["uid"]
        alert_data = parsed.get("alert", {})
        self.alerts.handle_alert_triggered(uid, alert_data)
    
    def _handle_unpair(self, uid: str):
        """Gère une demande de dé-pairing"""
        print(f"\nUNPAIR: {uid}")
        self.nodes.remove_child(uid)
        
        # Publier l'événement
        self.mqtt.publish_event("pairing", {
            "event": "unpair_sucess",
            "uid": uid
        })
    
    def _handle_alert_ack(self, uid: str, parsed: dict, action_type: str):
        """
        Gère la réception d'un ACK de l'ESP32 concernant une alerte.
        """
        if not self.nodes.est_autorise(uid):
            print(f"[LoRa] ACK d'alerte reçu d'un nœud inconnu: {uid}")
            return

        datas = (parsed.get("datas") or "").strip()
        sensor_type, max_val, min_val = self.parser.parse_alert_ack_datas(datas)

        print(f"[LoRa] Réception ACK: Alerte {action_type} sur {uid} ({sensor_type})")

        self.alerts.handle_alert_ack(uid, sensor_type, action_type, max_val, min_val)
