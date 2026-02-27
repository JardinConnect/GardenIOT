"""
Message Router - Gère le routing des messages entre LoRa et MQTT
"""
from typing import Dict, Any, Optional
from ..models.messages import LoRaMessage, MqttMessage, MessageType, SensorData, AlertConfig


class MessageRouter:
    """
    Route les messages entre les différents composants
    Gère les transformations de format et la logique métier
    """
    
    def __init__(self, gateway_core):
        self.gateway = gateway_core
        
        # Mappings des topics MQTT
        self.mqtt_topics = {
            "sensor_data": "garden/sensors/{uid}",
            "pairing_request": "garden/pairing/request",
            "pairing_success": "garden/pairing/success/{uid}",
            "alert_config": "garden/alerts/config/{uid}",
            "alert_trigger": "garden/alerts/trigger/{uid}",
            "system_state": "garden/system/state",
            "unpair": "garden/pairing/unpair/{uid}"
        }
    
    def route_from_lora(self, lora_message: LoRaMessage):
        """Route un message provenant de LoRa"""
        handler_name = f"_handle_lora_{lora_message.message_type.name.lower()}"
        handler = getattr(self, handler_name, self._handle_unknown_lora)
        handler(lora_message)
    
    def route_from_mqtt(self, topic: str, payload: str, qos: int = 1):
        """Route un message provenant de MQTT"""
        try:
            mqtt_message = MqttMessage.from_mqtt(topic, payload, qos)
            
            # Extraire l'UID si présent dans le topic
            uid = self._extract_uid_from_topic(topic)
            
            # Déterminer le type de message
            if "alerts/config" in topic:
                self._handle_mqtt_alert_config(uid, mqtt_message.payload)
            elif "pairing/unpair" in topic:
                self._handle_mqtt_unpair(uid, mqtt_message.payload)
            elif "pairing/request" in topic:
                self._handle_mqtt_pairing_request(mqtt_message.payload)
            else:
                print(f"⚠️ Topic MQTT non géré: {topic}")
                
        except Exception as e:
            print(f"❌ Erreur routing MQTT: {e}")
    
    # Handlers pour messages LoRa
    def _handle_lora_data(self, message: LoRaMessage):
        """Traite les données capteurs"""
        # Parser les données capteurs (conserve le format original)
        sensor_data = SensorData.from_lora_data(message.data)
        
        # Vérifier si l'enfant est autorisé
        if not self.gateway.child_repo.is_child_authorized(message.uid):
            print(f"⚠️ Données de {message.uid} ignorées (non appairé)")
            return
        
        # Construire le payload MQTT avec le format original
        payload = {
            "uid": message.uid,
            "timestamp": message.timestamp,
            "raw_data": sensor_data.raw_data,  # Format original pour le backend
            "parsed": sensor_data.parsed_values  # Valeurs parsées
        }
        
        # Publier sur MQTT
        topic = self.mqtt_topics["sensor_data"].format(uid=message.uid)
        self.gateway.mqtt_comm.publish(topic, payload, qos=1)
        
        print(f"📤 Données envoyées à MQTT: {topic}")
    
    def _handle_lora_pairing(self, message: LoRaMessage):
        """Traite les demandes de pairing"""
        # Vérifier si nous sommes en mode pairing
        if not self.gateway.current_state or not isinstance(self.gateway.current_state, PairingState):
            print(f"❌ Pairing refusé pour {message.uid} (mode pairing inactif)")
            return
        
        # Ajouter l'enfant
        success = self.gateway.child_repo.add_child(message.uid)
        
        if success:
            print(f"✅ Nouveau enfant appairé: {message.uid}")
            
            # Construire l'ACK
            ack_message = LoRaMessage(
                message_type=MessageType.ACK,
                timestamp=message.timestamp,
                uid=self.gateway.child_repo.get_parent_id(),
                data=message.uid
            )
            
            # Envoyer l'ACK
            self.gateway.lora_comm.send(ack_message.to_lora_format())
            
            # Notifier via MQTT
            self.gateway.mqtt_comm.publish(
                self.mqtt_topics["pairing_success"].format(uid=message.uid),
                {"uid": message.uid, "parent_id": self.gateway.child_repo.get_parent_id()},
                qos=0
            )
        else:
            print(f"ℹ️ Enfant déjà connu: {message.uid}")
    
    def _handle_lora_unpair(self, message: LoRaMessage):
        """Traite les demandes de désappariement"""
        success = self.gateway.child_repo.remove_child(message.uid)
        
        if success:
            print(f"🗑️ Enfant désappairé: {message.uid}")
            
            # Notifier via MQTT
            self.gateway.mqtt_comm.publish(
                self.mqtt_topics["unpair"].format(uid=message.uid),
                {"uid": message.uid, "action": "unpaired"},
                qos=0
            )
        else:
            print(f"⚠️ Échec désappariement: {message.uid}")
    
    def _handle_lora_alert_config(self, message: LoRaMessage):
        """Traite les accusés de réception de configuration d'alerte"""
        print(f"🛠️ ACK alerte reçu de {message.uid}: {message.data}")
        
        # Notifier via MQTT
        self.gateway.mqtt_comm.publish(
            f"garden/alerts/ack/{message.uid}",
            {
                "uid": message.uid, 
                "status": "received", 
                "data": message.data,
                "timestamp": self._get_current_timestamp()
            },
            qos=0
        )
    
    def _handle_lora_alert_trigger(self, message: LoRaMessage):
        """Traite les alertes déclenchées"""
        # Parser les données d'alerte avec le nouveau format
        alert_trigger = AlertTrigger.from_lora_data(message.data)
        
        # Publier sur MQTT
        self.gateway.mqtt_comm.publish(
            self.mqtt_topics["alert_trigger"].format(uid=message.uid),
            alert_trigger.to_dict(),
            qos=1
        )
        
        print(f"⚠️ Alerte déclenchée: {alert_trigger.alert_id} sur {message.uid}")
    
    def _handle_unknown_lora(self, message: LoRaMessage):
        """Gère les messages LoRa inconnus"""
        print(f"⚠️ Message LoRa inconnu: {message.message_type.value} de {message.uid}")
    
    # Handlers pour messages MQTT
    def _handle_mqtt_alert_config(self, payload: Dict[str, Any]):
        """Traite les configurations d'alerte depuis MQTT"""
        alert_id = payload.get("id", "")
        print(f"📩 Configuration alerte reçue: {alert_id}")
        
        # Créer la configuration à partir du payload backend
        alert_config = AlertConfig.from_mqtt_payload(payload)
        
        # Vérifier que les cellules existent
        valid_cells = []
        for cell_id in alert_config.cell_ids:
            if self.gateway.child_repo.is_child_authorized(cell_id):
                valid_cells.append(cell_id)
            else:
                print(f"⚠️ Cellule {cell_id} non appairée - ignorée")
        
        if not valid_cells:
            print(f"⚠️ Aucune cellule valide pour l'alerte {alert_id}")
            return
        
        # Mettre à jour la liste des cellules valides
        alert_config.cell_ids = valid_cells
        
        # Envoyer la configuration à chaque cellule concernée
        for cell_uid in valid_cells:
            lora_message = LoRaMessage(
                message_type=MessageType.ALERT_CONFIG,
                timestamp=self._get_current_timestamp(),
                uid=cell_uid,
                data=alert_config.to_lora_data()
            )
            
            success = self.gateway.lora_comm.send(lora_message.to_lora_format())
            if success:
                print(f"📤 Config alerte {alert_id} envoyée à {cell_uid} via LoRa")
            else:
                print(f"❌ Échec envoi à {cell_uid}")
    
    def _handle_mqtt_unpair(self, uid: str, payload: Dict[str, Any]):
        """Traite les commandes de désappariement depuis MQTT"""
        print(f"📩 Commande désappariement reçue pour {uid}")
        
        # Construire le message LoRa
        lora_message = LoRaMessage(
            message_type=MessageType.UNPAIR,
            timestamp=self._get_current_timestamp(),
            uid=uid,
            data=""
        )
        
        # Envoyer via LoRa
        self.gateway.lora_comm.send(lora_message.to_lora_format())
        
        # Supprimer de la liste locale
        self.gateway.child_repo.remove_child(uid)
        
        print(f"🗑️ Désappariement commandé pour {uid}")
    
    def _handle_mqtt_pairing_request(self, payload: Dict[str, Any]):
        """Traite les demandes de pairing depuis MQTT"""
        event = payload.get("event")
        
        if event == "start":
            print("📩 Demande pairing MQTT reçue")
            self.gateway.trigger_pairing_mode()
        elif event == "stop":
            print("📩 Arrêt pairing MQTT reçu")
            self.gateway.set_state(SystemState.NORMAL)
    
    # Méthodes utilitaires
    def _extract_uid_from_topic(self, topic: str) -> Optional[str]:
        """Extrait l'UID d'un topic MQTT"""
        parts = topic.split("/")
        for part in parts:
            if part.startswith("uid-") or len(part) == 12:  # Format UID attendu
                return part.replace("uid-", "")
        return None
    
    def _parse_alert_data(self, data_str: str) -> Dict[str, Any]:
        """Parse les données d'alerte"""
        try:
            # Format attendu: TYPE=value>threshold
            parts = data_str.split("=")
            if len(parts) == 2:
                alert_type = parts[0]
                value_threshold = parts[1].split(">")
                if len(value_threshold) == 2:
                    return {
                        "type": alert_type,
                        "value": float(value_threshold[0]),
                        "threshold": float(value_threshold[1])
                    }
        except Exception:
            pass
        
        return {"type": "unknown", "value": None, "threshold": None}
    
    def _get_current_timestamp(self) -> str:
        """Retourne un timestamp ISO formaté"""
        from datetime import datetime
        return datetime.now().isoformat()
