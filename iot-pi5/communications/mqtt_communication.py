"""
Communication MQTT - Gestion de la connexion au broker MQTT
"""
import time
import json
import paho.mqtt.client as mqtt
from typing import Callable, Optional, Dict, Any


class MqttCommunication:
    """
    Gère la communication MQTT avec le broker
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.client = None
        self.connected = False
        self.message_callback = None
        self.subscribed_topics = []
        self.loop_running = False
    
    def initialize(self):
        """Initialise la connexion MQTT"""
        try:
            print("📡 Initialisation MQTT...")
            
            # Créer le client
            self.client = mqtt.Client(
                client_id=self.config.get("client_id", "garden-gateway"),
                clean_session=True
            )
            
            # Configurer les callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            # Configuration de la connexion
            # if self.config.get("username") and self.config.get("password"):
            #     self.client.username_pw_set(
            #         self.config["username"],
            #         self.config["password"]
            #     )
            
            # Connexion au broker
            self.connect()
            
        except Exception as e:
            print(f" Échec initialisation MQTT: {e}")
            raise
    
    def connect(self):
        """Établit la connexion au broker"""
        try:
            if not self.client:
                self.initialize()
                return
            
            print(f"🔌 Connexion à {self.config['broker_host']}:{self.config['broker_port']}...")
            
            self._ensure_loop_running()

            self.client.connect(
                self.config["broker_host"],
                self.config["broker_port"],
                keepalive=self.config.get("keepalive", 60)
            )
            
            # Attendre la connexion
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < 5:
                time.sleep(0.1)
            
            if self.connected:
                print(" Connecté au broker MQTT")
            else:
                print(" Timeout connexion MQTT")
                
        except Exception as e:
            print(f" Échec connexion MQTT: {e}")
            self.connected = False
    
    def reconnect(self):
        """Tente de se reconnecter"""
        try:
            if self.client:
                self.connected = False
                self._ensure_loop_running()
                self.client.reconnect()

                start_time = time.time()
                while not self.connected and (time.time() - start_time) < 5:
                    time.sleep(0.1)

                if self.connected:
                    print(" Reconnexion MQTT réussie")
                else:
                    print(" Timeout reconnexion MQTT")
        except Exception as e:
            print(f" Échec reconnexion MQTT: {e}")
            self.connected = False

    def _ensure_loop_running(self):
        """S'assure que la boucle réseau MQTT tourne."""
        if not self.loop_running:
            self.client.loop_start()
            self.loop_running = True
    
    def disconnect(self):
        """Déconnecte du broker"""
        if self.client:
            try:
                if self.loop_running:
                    self.client.loop_stop()
                    self.loop_running = False
                self.client.disconnect()
                self.connected = False
                print("🔌 Déconnecté du broker MQTT")
            except:
                pass
    
    def is_connected(self) -> bool:
        """Retourne True si connecté"""
        return self.connected
    
    def publish(self, topic: str, payload: Dict[str, Any], qos: int = 1) -> bool:
        """Publie un message sur un topic"""
        print(f" MQTT publish... {self.connected=}, {topic=}, {payload=}")
        if not self.connected:
            return False
        
        try:
            if not isinstance(payload, str):
                payload = json.dumps(payload)
            
            result = self.client.publish(topic, payload, qos=qos)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f" Erreur publication MQTT sur {topic}: {e}")
            return False
    
    def subscribe(self, topic: str, qos: int = 1):
        """S'abonne à un topic"""
        if not self.connected:
            print(" Impossible de s'abonner - non connecté")
            return False
        
        try:
            result, mid = self.client.subscribe(topic, qos)
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.subscribed_topics.append(topic)
                print(f" Abonnement à {topic}")
                return True
            else:
                print(f" Échec abonnement à {topic}")
                return False
                
        except Exception as e:
            print(f" Erreur abonnement MQTT: {e}")
            return False
    
    def set_message_callback(self, callback: Callable[[str, str, int], None]):
        """Définit le callback pour les messages entrants"""
        self.message_callback = callback
    
    def _subscribe_to_topics(self):
        """S'abonne à tous les topics nécessaires pour consommer les messages"""
        topics = [
            ("garden/alerts/config", 1),
            ("garden/pairing/request", 0),
            ("garden/pairing/unpair", 0),
            ("garden/devices/command", 0),
            ("garden/devices/settings", 0)
        ]
        
        for topic, qos in topics:
            self.subscribe(topic, qos)
    
    # Callbacks MQTT
    def _on_connect(self, client, userdata, flags, rc):
        """Callback appelé lors de la connexion"""
        if rc == 0:
            self.connected = True
            print(" Connecté au broker MQTT")
            self._subscribe_to_topics()
        else:
            self.connected = False
            print(f" Échec connexion MQTT (code {rc})")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback appelé lors de la déconnexion"""
        self.connected = False
        print(f"🔌 Déconnecté du broker MQTT (code {rc})")
    
    def _on_message(self, client, userdata, msg):
        """Callback appelé lors de la réception d'un message"""
        try:
            payload = msg.payload.decode('utf-8')
            print(f" MQTT reçu sur {msg.topic}: {payload}...")
            
            # Appeler le callback si défini
            if self.message_callback:
                self.message_callback(msg.topic, payload, msg.qos)
                
        except Exception as e:
            print(f" Erreur traitement message MQTT: {e}")
