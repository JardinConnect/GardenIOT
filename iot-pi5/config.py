"""
Configuration du système Gateway
"""
import board


# Configuration par défaut
DEFAULT_CONFIG = {
    "lora": {
        "frequency": 433.1,
        "bandwidth": 500000,
        "spreading_factor": 10,
        "coding_rate": 5,
        "preamble_length": 8,
        "enable_crc": False,
        "cs_pin": board.D5,
        "reset_pin": board.D25
    },
    "mqtt": {
        "broker_host": "localhost",
        "broker_port": 1883,
        "client_id": "garden-gateway-pi5",
        "username": None,
        "password": None,
        "keepalive": 60,
        "qos": 1
    },
    "repository": {
        "file_path": "child.json"
    },
    "system": {
        "pairing_duration": 30,
        "button_pin": board.D22,
        "button_press_threshold": 3.0,
        "button_reset_threshold": 15.0
    }
}


def load_config():
    """Charge la configuration"""
    # Pour l'instant, retourne la config par défaut
    # Peut être étendu pour charger depuis un fichier
    return DEFAULT_CONFIG
