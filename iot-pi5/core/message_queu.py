import threading

class MessageQueue:
    def __init__(self, gateway_core):
        self.gateway = gateway_core
        self.pending_messages = {}
        self.event_bus = gateway_core.event_bus
        self.event_bus.subscribe("esp32.available", self._on_esp_available)
        self.lock = threading.Lock()  # Pour éviter les chevauchements

    def queue_message(self, esp_uid: str, message: dict):
        """Ajoute un message à la file d'attente."""
        with self.lock:
            print(f"Message ajouté à la file pour {esp_uid}: {message}")
            if esp_uid not in self.pending_messages:
                self.pending_messages[esp_uid] = []
            self.pending_messages[esp_uid].append(message)

    def _on_esp_available(self, esp_uid: str):
        """Envoie les messages en attente pour un ESP32."""
        with self.lock:
            print(f"ESP32 {esp_uid} disponible, envoi des messages en attente...")
            if esp_uid in self.pending_messages:
                for message in self.pending_messages[esp_uid]:
                    self._send_message(esp_uid, message)
                self.pending_messages[esp_uid] = []

    def _send_message(self, esp_uid: str, message):
        """Envoie un message via LoRa."""
        try:
            print(f"Envoi message à {esp_uid}: {message}")
            if isinstance(message, dict) and message.get("type") == "ACK":
                # Envoyer l'ACK
                self.gateway.lora_comm.send_ack(esp_uid)
            elif isinstance(message, str):
                # Message déjà au format LoRa (string)
                self.gateway.lora_comm.send(message)
            # elif isinstance(message, dict):
            #     # Convertir le dictionnaire en message LoRa
            #     # Format attendu: {"type": "...", "data": "..."}
            #     msg_type = message.get("type", "DATA")
            #     msg_data = message.get("data", "")
            #     from datetime import datetime
            #     timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
                
            #     # Créer le message LoRa
            #     lora_message = f"B|{msg_type}|{timestamp}|{esp_uid}|{msg_data}|E"
            #     self.gateway.lora_comm.send(lora_message)
            else:
                print(f"Format de message non supporté: {type(message)}")
        except Exception as e:
            print(f"Échec envoi à {esp_uid}: {e}")