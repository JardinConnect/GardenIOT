# Garden IoT Gateway - Pi5

Système Gateway pour la communication entre les devices ESP32 enfants et le backend via MQTT.

## Architecture

Ce système implémente une architecture modulaire avec les composants suivants :

- **GatewayCore** : Cœur du système, coordonne tous les composants
- **MessageRouter** : Route les messages entre LoRa et MQTT
- **LoRaCommunication** : Gère la radio LoRa
- **MqttCommunication** : Gère la connexion MQTT
- **ChildRepository** : Gère la persistence des enfants appairés

## Design Patterns Implémentés

1. **State Pattern** : Gestion des différents états du système
2. **Bridge Pattern** : Séparation abstraction/implémentation
3. **Command Pattern** : Encapsulation des opérations
4. **Repository Pattern** : Persistence des données
5. **Observer Pattern** : Communication via callbacks

## Structure du Projet

```
iot-pi5/
├── core/                  # Noyau du système
├── communications/        # Protocoles de communication
├── repositories/          # Persistence
├── models/                # Modèles de données
├── services/              # Services (à implémenter)
├── main.py                # Point d'entrée
├── config.py              # Configuration
├── requirements.txt       # Dépendances
└── README.md              # Documentation
```

## Configuration

La configuration se trouve dans `config.py` ou peut être passée directement :

```python
CONFIG = {
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
```

## Topics MQTT

### Publication (Pi5 → Backend)
- `garden/sensors/{uid}` : Données capteurs (QoS 1)
- `garden/pairing/success/{uid}` : Succès pairing (QoS 0)
- `garden/alerts/trigger/{uid}` : Alertes déclenchées (QoS 1)
- `garden/system/state` : État du système (QoS 0)

### Abonnement (Backend → Pi5)
- `garden/alerts/config/{uid}` : Configurations d'alerte (QoS 1)
- `garden/pairing/request` : Demandes de pairing (QoS 0)
- `garden/pairing/unpair/{uid}` : Commandes de désappariement (QoS 0)
- `garden/system/command` : Commandes système (QoS 0)

## Fonctionnalités

### 1. Appariement des Devices
- Appui court (3s) sur le bouton → Active le mode pairing
- Appui long (15s) → Reset complet des enfants
- Les devices enfants peuvent s'appairer pendant la fenêtre de pairing

### 2. Transmission des Données
- Les ESP32 envoient leurs données capteurs via LoRa
- Le Pi5 les reçoit et les publie sur MQTT
- Seuls les devices appairés sont acceptés

### 3. Configuration des Alertes
- Le backend envoie les configurations d'alerte via MQTT
- Le Pi5 les transmet aux ESP32 concernés via LoRa
- Les ESP32 envoient des ACK et déclenchent des alertes si nécessaire

### 4. Gestion d'État
- **Normal** : Fonctionnement standard
- **Pairing** : Mode appariement actif
- **Maintenance** : Mode pour mises à jour

## Installation

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer le système
python main.py
```

## Dépendances

- `paho-mqtt` : Client MQTT
- `adafruit-circuitpython-rfm9x` : Driver LoRa
- `RPi.GPIO` : Gestion des GPIO

## Intégration avec le Backend

Le backend doit :
1. S'abonner aux topics de données et d'alertes
2. Publier les configurations sur les topics appropriés
3. Gérer l'authentification des devices via les UID

## Développement Futur

- [ ] Implémenter un système d'ACK plus robuste
- [ ] Ajouter le chiffrement des messages LoRa
- [ ] Implémenter la journalisation complète
- [ ] Ajouter des métriques et monitoring
- [ ] Implémenter les mises à jour OTA

## Licence

MIT
