# config.py

# ============================================
# MQTT
# ============================================
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60

MQTT_TOPIC_DATA = "garden/data"
MQTT_TOPIC_PAIRING = "garden/pairing"
MQTT_TOPIC_ALERTS = "garden/alert"              

# ============================================
# LoRa
# ============================================
LORA_FREQUENCY = 433.1
LORA_SIGNAL_BANDWIDTH = 500000
LORA_SPREADING_FACTOR = 10
LORA_CODING_RATE = 5
LORA_PREAMBLE_LENGTH = 8
LORA_ENABLE_CRC = False

# ============================================
# Bouton
# ============================================
DUREE_PAIRING_SEC = 30.0
DUREE_RESET_SEC = 15.0

# ============================================
# Timeouts
# ============================================
TIMEOUT_RX_NORMAL = 0.1
TIMEOUT_RX_PAIRING = 0.5
ANTI_DOUBLON_SEC = 1.0
