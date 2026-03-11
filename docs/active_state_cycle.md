# Cycle de vie de l'état ACTIVE

Ce document explique en détail le cycle de vie de l'état ACTIVE dans le système IoT ESP32.

## Aperçu général

L'état ACTIVE est l'état principal où le device:
1. Lit les données des capteurs
2. Formate et envoie les données via LoRa
3. Attend un accusé de réception (ACK) du gateway
4. Écoute les messages entrants
5. Transitionne vers l'état SLEEP

## Diagramme de flux

```
ACTIVE State Cycle
├── run_cycle() [DeviceManager]
│   ├── Read sensors (SensorManager)
│   │   └── Returns: {"sensor1": {"temp": 25.3, "hum": 45}, ...}
│   │
│   ├── Format data (DeviceManager._format_sensor_data)
│   │   └── Converts to: "1TA25;1HA45;..."
│   │
│   ├── Send via LoRa (CommunicationManager.send with expect_ack=True)
│   │   ├── LoRaProtocol.send()
│   │   │   ├── Builds message: "B|D|2023-01-01T12:00:00Z|ESP32-001|1TA25;1HA45|E"
│   │   │   ├── Adds padding: "XXXXB|D|2023-01-01T12:00:00Z|ESP32-001|1TA25;1HA45|E"
│   │   │   ├── Sends via hardware LoRa
│   │   │   └── Waits for ACK (expect_ack=True)
│   │   │       ├── Listens for response
│   │   │       ├── Parses ACK message
│   │   │       └── Returns True if ACK received
│   │   └── Returns: True/False
│   │
│   └── Listen for messages (DeviceManager._listen_for_messages)
│       ├── communication.receive()
│       └── Handles incoming messages (ACK, commands, etc.)
│
└── Transition to SLEEP state
```

## Détails des étapes

### 1. Lecture des capteurs

**Méthode**: `DeviceManager.run_cycle()` → `SensorManager.read_all_sensors()`

**Responsabilité**: SensorManager
- Lit tous les capteurs configurés
- Retourne un dictionnaire avec les données brutes
- Exemple de retour: `{"bme280": {"temperature": 25.3, "humidity": 45.2, "pressure": 1013.25}}`

**Logs**:
```
[DeviceManager.run_cycle] Reading sensors...
[DeviceManager.run_cycle] Sensor data received: {...}
```

### 2. Formatage des données

**Méthode**: `DeviceManager._format_sensor_data()`

**Responsabilité**: DeviceManager
- Convertit les données brutes en format compact
- Utilise les codes configurés pour chaque capteur
- Format final: `1{code}{value};1{code}{value};...`

**Exemple**:
- Entrée: `{"temperature": 25.3, "humidity": 45.2}`
- Codes: `{"temperature": "TA", "humidity": "HA"}`
- Sortie: `1TA25;1HA45`

**Logs**:
```
[DeviceManager._format_sensor_data] ENTRY
[DeviceManager._format_sensor_data] Formatted bme280.temperature: TA25
[DeviceManager._format_sensor_data] Formatted bme280.humidity: HA45
[DeviceManager._format_sensor_data] EXIT - Formatted payload: 1TA25;1HA45
```

### 3. Envoi des données via LoRa

**Méthode**: `DeviceManager._send_sensor_data_with_ack()` → `CommunicationManager.send()`

**Responsabilité**: CommunicationManager + LoRaProtocol

**Format du message LoRa**:
```
B|D|TIMESTAMP|UID|DATAS|E
```

**Champs**:
- `B`: Début de trame
- `D`: Type de message (Data)
- `TIMESTAMP`: Horodatage ISO (ex: 2023-01-01T12:00:00Z)
- `UID`: Identifiant du device (ex: ESP32-001)
- `DATAS`: Données formatées (ex: 1TA25;1HA45)
- `E`: Fin de trame

**Processus**:
1. Construction du message
2. Ajout de padding (XXXX)
3. Envoi via le hardware LoRa
4. Attente de l'ACK (si `expect_ack=True`)

**Logs**:
```
[DeviceManager._send_sensor_data_with_ack] ENTRY
[DeviceManager._send_sensor_data_with_ack] Sending message with ACK: {'type': 'D', 'uid': 'ESP32-001', 'datas': '1TA25;1HA45'}
[LoRa] Envoi (1/3): b'XXXXB|D|2023-01-01T12:00:00Z|ESP32-001|1TA25;1HA45|E'
[DeviceManager._send_sensor_data_with_ack] Data sent and ACK received: 1TA25;1HA45
[DeviceManager._send_sensor_data_with_ack] EXIT
```

### 4. Attente de l'ACK

**Processus**:
1. Après l'envoi, le device passe en mode écoute
2. Attend un message de type ACK
3. Vérifie que l'ACK contient son UID
4. Si ACK reçu: succès
5. Si timeout: échec (retries possibles)

**Format de l'ACK attendu**:
```
B|ACK|TIMESTAMP|GATEWAY_PI|ESP32-001|E
```

### 5. Écoute des messages entrants

**Méthode**: `DeviceManager._listen_for_messages()`

**Responsabilité**: DeviceManager
- Écoute les messages entrants pendant un timeout configuré
- Traite les messages reçus (ACK, commandes, etc.)
- Publie les événements sur l'EventBus

**Logs**:
```
[DeviceManager._listen_for_messages] ENTRY
[DeviceManager._listen_for_messages] Waiting for messages (timeout: 5000ms)
[DeviceManager._listen_for_messages] No message received
[DeviceManager._listen_for_messages] EXIT
```

### 6. Transition vers SLEEP

Après completion du cycle, l'état ACTIVE transitionne vers SLEEP:
```python
# Dans ActiveState.handle()
context.set_state(SleepState())
```

## Gestion des erreurs

1. **Pas de données capteurs**: Le cycle continue sans envoi
2. **Échec d'envoi**: Logué, mais le cycle continue
3. **Pas d'ACK reçu**: Logué, mais le cycle continue
4. **Exception**: Capturée et loguée, transition vers ERROR state si nécessaire

## Configuration pertinente

```json
{
  "device": {
    "listen_timeout": 5000,
    "uid": "ESP32-001"
  },
  "sensors": [
    {
      "name": "bme280",
      "enabled": true,
      "codes": {
        "temperature": "TA",
        "humidity": "HA",
        "pressure": "PA"
      }
    }
  ],
  "lora": {
    "ack_timeout_ms": 3000,
    "max_retries": 3
  }
}
```

## Points clés

1. **Responsabilités claires**:
   - DeviceManager: Orchestration et formatage
   - SensorManager: Lecture des capteurs uniquement
   - CommunicationManager: Gestion de la communication LoRa

2. **Logs détaillés**: Chaque méthode a des logs d'entrée/sortie

3. **Format compact**: Les données sont optimisées pour la transmission LoRa

4. **Gestion d'ACK**: Le système attend et vérifie les accusés de réception

5. **Cycle complet**: Lecture → Formatage → Envoi → Écoute → Transition

## Exemple de logs complet

```
==================================================
[DeviceManager.run_cycle] ENTRY - Starting ACTIVE cycle
[DeviceManager.run_cycle] Reading sensors...
[SensorManager] Reading sensor: bme280
[DeviceManager.run_cycle] Sensor data received: {'bme280': {'temperature': 25.3, 'humidity': 45.2}}
[DeviceManager.run_cycle] Formatting and sending data...
[DeviceManager._format_sensor_data] ENTRY
[DeviceManager._format_sensor_data] Formatted bme280.temperature: TA25
[DeviceManager._format_sensor_data] Formatted bme280.humidity: HA45
[DeviceManager._format_sensor_data] EXIT - Formatted payload: 1TA25;1HA45
[DeviceManager._send_sensor_data_with_ack] ENTRY
[DeviceManager._send_sensor_data_with_ack] Sending message with ACK: {'type': 'D', 'uid': 'ESP32-001', 'datas': '1TA25;1HA45'}
[LoRa] Envoi (1/3): b'XXXXB|D|2023-01-01T12:00:00Z|ESP32-001|1TA25;1HA45|E'
[LoRa] ACK recu
[DeviceManager._send_sensor_data_with_ack] Data sent and ACK received: 1TA25;1HA45
[DeviceManager._send_sensor_data_with_ack] EXIT
[DeviceManager.run_cycle] Listening for incoming messages...
[DeviceManager._listen_for_messages] ENTRY
[DeviceManager._listen_for_messages] Waiting for messages (timeout: 5000ms)
[DeviceManager._listen_for_messages] No message received
[DeviceManager._listen_for_messages] EXIT
[DeviceManager.run_cycle] EXIT - Cycle completed
[StateManager] State: ACTIVE SLEEP
```
