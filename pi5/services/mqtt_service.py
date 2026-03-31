# services/mqtt_service.py
"""Service de gestion MQTT"""

import paho.mqtt.client as mqtt
import json
from datetime import datetime
from config import *

class MqttService:
    """Service de gestion de la connexion et publication MQTT"""
    
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.connected = False
        self.command_callback = None
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """Configure les callbacks MQTT"""
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
    
    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """Callback lors de la connexion"""
        if not reason_code.is_failure:
            self.connected = True
            print("[MQTT] Connecté avec succès au broker")
            
            client.subscribe(MQTT_TOPIC_ALERTS)
            client.subscribe(MQTT_TOPIC_PAIRING)
        else:
            print(f"[MQTT] Échec connexion: {reason_code}")
            self.connected = False
    
    def _on_message(self, client, userdata, msg):
        """Callback lors de la réception d'un message"""
        payload = msg.payload.decode()
        print(f"[MQTT] Commande reçue -> {msg.topic}: {payload}")
        
        if self.command_callback:
            try:
                self.command_callback(msg.topic, payload)
            except Exception as e:
                print(f"[MQTT] Erreur traitement commande: {e}")
    
    def set_command_callback(self, callback):
        """
        Définit le callback pour traiter les commandes MQTT
        
        """
        self.command_callback = callback
    
    def connect(self):
        """Se connecte au broker MQTT"""
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            self.client.loop_start()
        except Exception as e:
            print(f"[MQTT] Erreur connexion: {e}")
    
    def publish(self, topic: str, message: str) -> bool:
        """
        Publie un message sur un topic
    
        """
        if not self.connected:
            print(f" [MQTT] Non connecté, message ignoré")
            return False
        
        try:
            result = self.client.publish(topic, message)
            if result.rc == 0:
                print(f"Publié sur le topic mqtt {topic}")
                return True
            else:
                print(f"[MQTT] Échec publication: {result.rc}")
                return False
        except Exception as e:
            print(f"[MQTT] Erreur: {e}")
            return False
    
    def publish_event(self, event_type: str, data: dict):
        """
        Publie un événement (pairing, alertes, etc.)
        """
        
        data["timestamp"] = datetime.now().isoformat()
        
        topic_map = {
            "pairing": MQTT_TOPIC_PAIRING,
            "data": MQTT_TOPIC_DATA,
            "alert": MQTT_TOPIC_ALERTS,
        }
        
        topic = topic_map.get(event_type)
        
        if not topic:
            print(f"[MQTT] Événement ignoré, topic inconnu pour : {event_type}")
            return
            
        self.publish(topic, json.dumps(data))
    
    def disconnect(self):
        """Déconnexion propre"""
        self.client.loop_stop()
        self.client.disconnect()
