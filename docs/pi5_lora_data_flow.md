# Flux de traitement des données LoRa - Gateway Pi5

Ce document explique le flux simplifié de réception des données LoRa et d'envoi des ACK sur le Gateway Pi5.

## Aperçu général

Le Gateway Pi5 traite les messages LoRa entrants selon ce flux :
1. Réception du message LoRa
2. Validation du format
3. Envoi d'ACK (si ce n'est pas déjà un ACK)
4. Routage vers MQTT (pour les messages de données)

## Diagramme de flux

```
Pi5 LoRa Data Flow
├── GatewayCore.main_loop()
│   └── process_lora_messages()
│       ├── LoRaCommunication.receive()
│       │   ├── Écoute LoRa (timeout: 2s)
│       │   ├── Validation anti-doublon
│       │   ├── Validation format B|...|E
│       │   └── Retourne: message brut ou None
│       │
│       ├── LoRaMessage.from_lora_format()
│       │   ├── Parse le message
│       │   ├── Valide le type de message
│       │   └── Retourne: LoRaMessage ou None
│       │
│       ├── Si message valide:
│       │   ├── Log: 📡 [TYPE] de [UID]: [DATA]
│       │   ├── Si type ≠ ACK:
│       │   │   └── LoRaCommunication.send_ack()
│       │   │       ├── Construit: B|ACK|timestamp|GATEWAY_PI|target_uid|E
│       │   │       ├── Envoie via LoRa (3 tentatives)
│       │   │       └── Retourne: True/False
│       │   └── Si type = DATA:
│       │       └── MessageRouter.route_from_lora()
│       │           └── _handle_lora_data()
│       │               ├── Vérifie enfant autorisé
│       │               ├── Parse SensorData
│       │               ├── Construit payload MQTT
│       │               └── Publie sur MQTT topic: garden/sensors/{uid}
│       │
│       └── Si message invalide:
│           └── Log erreur et incrémente stats.errors
│
└── Retour à la boucle principale
```

## Détails des étapes

### 1. Réception du message LoRa

**Méthode**: `LoRaCommunication.receive()`

**Processus**:
- Écoute sur la fréquence LoRa configurée
- Timeout de 2 secondes
- Validation anti-doublon (3 secondes)
- Validation du format de base (B|...|E)
- Retourne le message brut ou None

**Logs**:
```
[LoRaCommunication.receive] ENTRY - Waiting for message...
[LoRaCommunication.receive] Raw message: B|D|2023-01-01T12:00:00Z|ESP32-001|1TA25;1HA45|E
[LoRaCommunication.receive] Valid message received: B|D|2023-01-01T12:00:00Z|ESP32-001|1TA25;1HA45|E
[LoRaCommunication.receive] EXIT - Message returned
```

### 2. Parsing du message

**Méthode**: `LoRaMessage.from_lora_format()`

**Validation**:
- Format: `B|TYPE|TIMESTAMP|UID|DATAS|E`
- Types valides: D, ACK, PA, U, A, C
- UID non vide

**Retourne**: Objet LoRaMessage ou None

### 3. Traitement dans GatewayCore

**Méthode**: `GatewayCore.process_lora_messages()`

**Logique**:
- Si message valide:
  - Log le message reçu
  - Si type ≠ ACK: envoie ACK
  - Si type = DATA: route vers MQTT
- Si message invalide:
  - Log l'erreur
  - Incrémente les statistiques d'erreurs

**Logs**:
```
[GatewayCore.process_lora_messages] ENTRY - Checking for LoRa messages...
[GatewayCore.process_lora_messages] Raw message received: B|D|2023-01-01T12:00:00Z|ESP32-001|1TA25;1HA45|E
📡 [D] de ESP32-001: 1TA25;1HA45
[GatewayCore.process_lora_messages] ACK sent successfully to ESP32-001
[GatewayCore.process_lora_messages] Routing message to MQTT...
[GatewayCore.process_lora_messages] EXIT - Message processed successfully
```

### 4. Envoi de l'ACK

**Méthode**: `LoRaCommunication.send_ack()`

**Format**: `B|ACK|TIMESTAMP|GATEWAY_UID|TARGET_UID|E`

**Exemple**: `B|ACK|2023-01-01T12:00:01Z|GATEWAY_PI|ESP32-001|E`

**Processus**:
- 3 tentatives d'envoi
- Retourne True si succès
- Log le résultat

**Logs**:
```
[LoRaCommunication.send_ack] ENTRY - Sending ACK to ESP32-001
[LoRaCommunication.send_ack] ACK message: B|ACK|2023-01-01T12:00:01Z|GATEWAY_PI|ESP32-001|E
[LoRaCommunication.send_ack] SUCCESS - ACK sent to ESP32-001
[LoRaCommunication.send_ack] EXIT
```

### 5. Routage vers MQTT

**Méthode**: `MessageRouter._handle_lora_data()`

**Processus**:
- Vérifie que l'enfant est autorisé
- Parse les données capteurs
- Construit le payload MQTT
- Publie sur le topic `garden/sensors/{uid}`

**Payload MQTT**:
```json
{
  "uid": "ESP32-001",
  "timestamp": "2023-01-01T12:00:00Z",
  "raw_data": "1TA25;1HA45",
  "parsed": {
    "TA:1": 25,
    "HA:1": 45
  }
}
```

**Logs**:
```
[MessageRouter._handle_lora_data] ENTRY - Processing DATA message from ESP32-001
[MessageRouter._handle_lora_data] Sensor data parsed: {'TA:1': 25, 'HA:1': 45}
[MessageRouter._handle_lora_data] SUCCESS - Data sent to MQTT: garden/sensors/ESP32-001
[MessageRouter._handle_lora_data] EXIT - Data message processed
```

## Gestion des erreurs

1. **Message invalide**: Logué et ignoré
2. **Échec d'envoi ACK**: Logué mais le traitement continue
3. **Échec MQTT**: Logué mais le traitement continue
4. **Exception**: Capturée, loguée et statistiques mises à jour

## Configuration pertinente

```json
{
  "gateway_uid": "GATEWAY_PI",
  "lora": {
    "frequency": 433.1,
    "bandwidth": 500000,
    "spreading_factor": 10,
    "sync_word": "0x12"
  }
}
```

## Points clés

1. **Flux linéaire**: Réception → Validation → ACK → Routage
2. **Logs détaillés**: Chaque étape est loguée pour le débogage
3. **Robustesse**: Gestion des erreurs à chaque niveau
4. **Séparation des responsabilités**:
   - `LoRaCommunication`: Réception/envoi LoRa
   - `GatewayCore`: Orchestration et logs
   - `MessageRouter`: Traitement métier et MQTT

## Exemple complet de logs

```
[LoRaCommunication.receive] ENTRY - Waiting for message...
[LoRaCommunication.receive] Raw message: B|D|2023-01-01T12:00:00Z|ESP32-001|1TA25;1HA45|E
[LoRaCommunication.receive] Valid message received: B|D|2023-01-01T12:00:00Z|ESP32-001|1TA25;1HA45|E
[LoRaCommunication.receive] EXIT - Message returned

[GatewayCore.process_lora_messages] ENTRY - Checking for LoRa messages...
[GatewayCore.process_lora_messages] Raw message received: B|D|2023-01-01T12:00:00Z|ESP32-001|1TA25;1HA45|E
📡 [D] de ESP32-001: 1TA25;1HA45

[LoRaCommunication.send_ack] ENTRY - Sending ACK to ESP32-001
[LoRaCommunication.send_ack] ACK message: B|ACK|2023-01-01T12:00:01Z|GATEWAY_PI|ESP32-001|E
[LoRaCommunication.send_ack] SUCCESS - ACK sent to ESP32-001
[LoRaCommunication.send_ack] EXIT

[GatewayCore.process_lora_messages] ACK sent successfully to ESP32-001
[GatewayCore.process_lora_messages] Routing message to MQTT...

[MessageRouter._handle_lora_data] ENTRY - Processing DATA message from ESP32-001
[MessageRouter._handle_lora_data] Sensor data parsed: {'TA:1': 25, 'HA:1': 45}
[MessageRouter._handle_lora_data] SUCCESS - Data sent to MQTT: garden/sensors/ESP32-001
[MessageRouter._handle_lora_data] EXIT - Data message processed

[GatewayCore.process_lora_messages] EXIT - Message processed successfully
```

## Schéma visuel

```
┌─────────────────────────────────────────────────────────────────┐
│                    Pi5 LoRa Data Processing Flow                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐  │
│  │  Receive    │──────▶│  Parse      │──────▶│  Send ACK   │  │
│  └─────────────┘       └─────────────┘       └─────────────┘  │
│        │                     │                     │          │
│        ▼                     ▼                     ▼          │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐  │
│  │  Validate   │──────▶│  Log        │──────▶│  Route to  │  │
│  │  Format     │       │  Message    │       │  MQTT      │  │
│  └─────────────┘       └─────────────┘       └─────────────┘  │
│        │                     │                     │          │
│        ▼                     ▼                     ▼          │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐  │
│  │  Anti-Dup    │       │  Send ACK   │       │  Publish   │  │
│  │  Check       │       │  (if needed)│       │  to MQTT   │  │
│  └─────────────┘       └─────────────┘       │  (if DATA) │  │
│                                              └─────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```
