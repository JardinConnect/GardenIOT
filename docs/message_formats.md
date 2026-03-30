# Formats de messages - LoRa et MQTT

Ce document reference tous les formats de messages utilises dans le systeme IoT, aussi bien cote LoRa (ESP32 <-> Pi5) que cote MQTT (Pi5 <-> Backend).

---

## 1. LoRa - Format general

Tous les messages LoRa suivent le meme format de trame :

```
B|TYPE|TIMESTAMP|UID|DATA|E
```

| Champ | Description | Exemple |
|-------|-------------|---------|
| `B` | Delimiteur de debut (Begin) | `B` |
| `TYPE` | Type de message (voir tableau ci-dessous) | `D`, `S`, `ACK`, `C`... |
| `TIMESTAMP` | Horodatage ISO 8601 UTC | `2026-03-30T18:00:00Z` |
| `UID` | Identifiant de l'emetteur ou du destinataire | `004b1235062c`, `GATEWAY_PI` |
| `DATA` | Donnees specifiques au type (detaillees ci-dessous) | `1TA22.5;1HA45` |
| `E` | Delimiteur de fin (End) | `E` |

### Types de messages LoRa

| Type | Code | Direction | Description |
|------|------|-----------|-------------|
| DATA | `D` | ESP32 -> Pi5 | Donnees capteurs |
| STATUS | `S` | ESP32 <-> Pi5 | Fin de cycle avec compteur de messages |
| PAIRING | `PA` | Pi5 -> ESP32 | Attribution de pairing |
| PA_ACK | `PA_ACK` | ESP32 -> Pi5 | Confirmation de pairing |
| ACK | `ACK` | Pi5 -> ESP32 | Accuse de reception |
| ACK | `ACK` | ESP32 -> Pi5 | Accuse de reception (cycle gateway) |
| ALERT_CONFIG | `A` | Pi5 -> ESP32 | Configuration d'alerte |
| ALERT_TRIGGER | `T` | ESP32 -> Pi5 | Alerte declenchee |
| COMMAND | `C` | Pi5 -> ESP32 | Commande generique |
| UNPAIR | `U` | ESP32 -> Pi5 | Demande de desappariement |

---

## 2. LoRa - Detail par type de message

### 2.1 DATA (`D`) - Donnees capteurs

**Direction :** ESP32 -> Pi5

```
B|D|<timestamp>|<esp32_uid>|<sensor_data>|E
```

**Champ DATA :** `{index}{code}{value};{index}{code}{value};...`

Chaque capteur est encode sous la forme `{index}{code}{value}` separe par `;` :

| Element | Description | Exemple |
|---------|-------------|---------|
| `index` | Numero du capteur (1-9) | `1` |
| `code` | Code du type de mesure (lettres) | `TA`, `HA`, `TS`, `HS`, `L` |
| `value` | Valeur mesuree (entier ou decimal, peut etre negatif) | `22.5`, `-3` |

**Codes capteurs connus :**

| Code | Signification |
|------|---------------|
| `TA` | Temperature Air |
| `TS` | Temperature Sol |
| `HA` | Humidite Air |
| `HS` | Humidite Sol |
| `L` | Luminosite |

**Exemple complet :**

```
B|D|2026-03-30T18:00:00Z|004b1235062c|1TA22.7;1TS21.2;1HA43.6;1HS10;2HS8.1|E
```

Decodage :
- Capteur 1, Temperature Air : 22.7
- Capteur 1, Temperature Sol : 21.2
- Capteur 1, Humidite Air : 43.6
- Capteur 1, Humidite Sol : 10
- Capteur 2, Humidite Sol : 8.1

---

### 2.2 STATUS (`S`) - Fin de cycle

**Direction :** ESP32 -> Pi5 (fin d'envoi) / Pi5 -> ESP32 (fin de cycle gateway)

```
B|S|<timestamp>|<uid>|<status>;<count>|E
```

**Champ DATA :** `{status};{count}`

| Element | Description | Valeurs |
|---------|-------------|---------|
| `status` | Resultat du cycle | `O` (OK) / `F` (Fail) |
| `count` | Nombre de messages envoyes dans ce cycle | Entier (ex: `3`) |

**Exemple :**

```
B|S|2026-03-30T18:00:05Z|004b1235062c|O;2|E
```

Le Pi5 compare `count` avec le nombre de messages DATA/TRIGGER effectivement recus pour decider du ACK (`OK` ou `KO`).

---

### 2.3 ACK (`ACK`) - Accuse de reception

**Direction :** Pi5 -> ESP32 (apres reception du STATUS)

```
B|ACK|<timestamp>|<esp32_uid>|<status>;<state>|E
```

**Champ DATA :** `{status};{state}`

| Element | Description | Valeurs |
|---------|-------------|---------|
| `status` | Validation des donnees recues | `OK` (tout recu) / `KO` (erreur ou mismatch) |
| `state` | Prochaine action pour l'ESP32 | `S` (Sleep) / `L` (Listen - gateway a des messages) |

**Exemple :**

```
B|ACK|2026-03-30T18:00:06Z|004b1235062c|OK;S|E
```

- `OK;S` : donnees validees, l'ESP32 peut dormir
- `OK;L` : donnees validees, l'ESP32 doit rester en ecoute (le gateway a des messages a envoyer)
- `KO;S` : erreur, l'ESP32 peut dormir (il reessaiera au prochain cycle)

**Direction :** ESP32 -> Pi5 (apres reception des messages gateway dans l'etat L)

```
B|ACK|<timestamp>|<esp32_uid>|<status>|E
```

| Element | Description | Valeurs |
|---------|-------------|---------|
| `status` | Validation des messages recus du gateway | `OK` / `KO` |

---

### 2.4 PAIRING (`PA`) - Attribution de pairing

**Direction :** Pi5 -> ESP32

```
B|PA|<timestamp>|<pi5_uid>|<new_uid>;<parent_id>|E
```

**Champ DATA :** `{new_uid};{parent_id}`

| Element | Description | Exemple |
|---------|-------------|---------|
| `new_uid` | UID attribue a l'ESP32 | `004b1235062c` |
| `parent_id` | UID du gateway parent | `GATEWAY_PI` |

**Exemple :**

```
B|PA|2026-03-30T18:00:00Z|GATEWAY_PI|004b1235062c;GATEWAY_PI|E
```

---

### 2.5 PA_ACK (`PA_ACK`) - Confirmation de pairing

**Direction :** ESP32 -> Pi5

```
B|PA_ACK|<timestamp>|<esp32_uid>|<status>|E
```

**Champ DATA :** `{status}`

| Element | Description | Valeurs |
|---------|-------------|---------|
| `status` | Resultat du pairing | `OK` / `KO` |

**Exemple :**

```
B|PA_ACK|2026-03-30T18:00:01Z|004b1235062c|OK|E
```

---

### 2.6 COMMAND (`C`) - Commande generique

**Direction :** Pi5 -> ESP32

```
B|C|<timestamp>|<uid>|<command_data>|E
```

**Champ UID :**
- **Broadcast** (IA) : `parent_id` (GATEWAY_PI) - tous les ESP32 reconnaissent le parent
- **Cible** (SET) : `child_uid` (004b1235062c) - seul l'ESP32 cible recoit

**Champ DATA :** Depend de la commande :

#### Instant Analytics (IA)

```
DATA = "IA"
```

Demande une remontee immediate des donnees capteurs. L'ESP32 active le flag `_force_send` et transite en ActiveState.

**Exemple :**

```
B|C|2026-03-30T18:00:00Z|GATEWAY_PI|IA|E
```

#### Settings Update (SET)

```
DATA = "SET:{key}={value};{key}={value}"
```

| Cle | Config ESP32 | Description |
|-----|-------------|-------------|
| `send_interval` | `device.send_interval` | Intervalle d'envoi en secondes |
| `sleep_interval` | `power.sleep_interval` | Duree du sleep en secondes |

**Exemple :**

```
B|C|2026-03-30T18:00:00Z|004b1235062c|SET:send_interval=30;sleep_interval=10|E
```

#### Reboot

```
DATA = "REBOOT"
```

**Exemple :**

```
B|C|2026-03-30T18:00:00Z|004b1235062c|REBOOT|E
```

#### Reset Config

```
DATA = "RESET_CONFIG"
```

**Exemple :**

```
B|C|2026-03-30T18:00:00Z|004b1235062c|RESET_CONFIG|E
```

---

### 2.7 ALERT_CONFIG (`A`) - Configuration d'alerte

**Direction :** Pi5 -> ESP32

```
B|A|<timestamp>|<esp32_uid>|<alert_config>|E
```

**Champ DATA :** `{alert_id}:{is_active}:{sensor_configs}`

| Element | Description | Exemple |
|---------|-------------|---------|
| `alert_id` | ID de l'alerte | `alert-123` |
| `is_active` | Alerte active | `1` (oui) / `0` (non) |
| `sensor_configs` | Configs capteurs separees par `;` | voir ci-dessous |

Chaque config capteur : `{index}{type}:{crit_min}:{crit_max}:{warn_min}:{warn_max}`

| Element | Description | Exemple |
|---------|-------------|---------|
| `index` | Index du capteur | `1` |
| `type` | Type de capteur | `TA`, `HA` |
| `crit_min` | Seuil critique minimum | `0` |
| `crit_max` | Seuil critique maximum | `40` |
| `warn_min` | Seuil warning minimum | `5` |
| `warn_max` | Seuil warning maximum | `35` |

**Exemple :**

```
B|A|2026-03-30T18:00:00Z|004b1235062c|alert-123:1:1TA:0:40:5:35;1HA:20:90:30:80|E
```

---

### 2.8 ALERT_TRIGGER (`T`) - Alerte declenchee

**Direction :** ESP32 -> Pi5

```
B|T|<timestamp>|<esp32_uid>|<alert_data>|E
```

**Champ DATA :** `{alert_id};{level};{identifier};{value}`

| Element | Description | Exemple |
|---------|-------------|---------|
| `alert_id` | ID de l'alerte declenchee | `alert-123` |
| `level` | Niveau de l'alerte | `C` (Critical) / `W` (Warning) |
| `identifier` | Identifiant capteur (index + code) | `1HA` |
| `value` | Valeur mesuree qui a declenche l'alerte | `54.3` |

**Exemple :**

```
B|T|2026-03-30T18:00:00Z|004b1235062c|alert-123;W;1HA;54.3|E
```

---

### 2.9 UNPAIR (`U`) - Desappariement

**Direction :** ESP32 -> Pi5

```
B|U|<timestamp>|<esp32_uid>||E
```

**Champ DATA :** vide

**Exemple :**

```
B|U|2026-03-30T18:00:00Z|004b1235062c||E
```

---

## 3. MQTT - Topics et payloads

### 3.1 Topics entrants (Backend -> Pi5)

#### `garden/alerts/config` (QoS 1)

Configure une alerte sur un ou plusieurs ESP32.

**Payload :**

```json
{
  "id": "alert-123",
  "is_active": true,
  "cell_ids": ["004b1235062c", "00ab34cd56ef"],
  "sensors": [
    {
      "type": "TA",
      "index": 1,
      "criticalRange": [0, 40],
      "warningRange": [5, 35]
    },
    {
      "type": "HA",
      "index": 1,
      "criticalRange": [20, 90],
      "warningRange": [30, 80]
    }
  ]
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `id` | string | Identifiant unique de l'alerte |
| `is_active` | bool | Alerte active ou non |
| `cell_ids` | string[] | Liste des UIDs ESP32 concernes |
| `sensors` | object[] | Configuration des seuils par capteur |
| `sensors[].type` | string | Code capteur (`TA`, `HA`, etc.) |
| `sensors[].index` | int | Index du capteur |
| `sensors[].criticalRange` | [min, max] | Seuils critiques |
| `sensors[].warningRange` | [min, max] | Seuils warning |

**Action :** Le Pi5 convertit en trame LoRa `A` et la met en queue pour chaque `cell_id` valide. Envoyee lors du prochain ACK avec state `L`.

---

#### `garden/pairing/request` (QoS 0)

Demande de demarrage ou arret du mode pairing.

**Payload :**

```json
{
  "event": "start"
}
```

| Champ | Type | Valeurs | Description |
|-------|------|---------|-------------|
| `event` | string | `start` / `stop` | Demarrer ou arreter le pairing |

**Action :** Le Pi5 entre en mode PAIRING (broadcast LoRa `PA` aux ESP32 en attente).

---

#### `garden/devices/command` (QoS 0)

Commande systeme a envoyer aux ESP32.

**Payload :**

```json
{
  "command": "instant_analytics"
}
```

| Champ | Type | Valeurs | Description |
|-------|------|---------|-------------|
| `command` | string | `instant_analytics` | Remontee immediate des donnees |
| | | `reboot` | Redemarrage du gateway |
| | | `factory_reset` | Reinitialisation de la configuration |

**Action selon la commande :**
- `instant_analytics` : burst LoRa `C` avec data `IA` (broadcast, uid = parent_id)
- `reboot` : redemarrage du Pi5
- `factory_reset` : reinitialisation de la configuration

---

#### `garden/devices/settings` (QoS 0)

Mise a jour de la configuration d'un ESP32.

**Payload :**

```json
{
  "uid": "004b1235062c",
  "send_interval": 30,
  "sleep_interval": 10
}
```

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `uid` | string | non | UID du device cible. Si absent, envoye a tous les children |
| `send_interval` | int | non | Intervalle d'envoi en secondes (config `device.send_interval`) |
| `sleep_interval` | int | non | Duree du sleep en secondes (config `power.sleep_interval`) |

Au moins un setting (`send_interval` ou `sleep_interval`) est requis.

**Action :** Burst LoRa `C` avec data `SET:key=val;key=val` cible sur le `uid` fourni (ou chaque child si absent).

---

### 3.2 Topics sortants (Pi5 -> Backend)

#### `garden/analytics` (QoS 1)

Donnees capteurs recues d'un ESP32.

**Payload :**

```json
{
  "uid": "004b1235062c",
  "timestamp": "2026-03-30T18:00:00Z",
  "sensors": {
    "1TA": 22.7,
    "1TS": 21.2,
    "1HA": 43.6,
    "1HS": 10,
    "2HS": 8.1
  }
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `uid` | string | UID de l'ESP32 source |
| `timestamp` | string | Horodatage ISO 8601 |
| `sensors` | object | Dictionnaire `{code: valeur}` des mesures |

---

#### `garden/pairing/result` (QoS 1)

Resultat d'un pairing reussi.

**Payload :**

```json
{
  "uid": "004b1235062c",
  "status": "ok",
  "parent_id": "GATEWAY_PI"
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `uid` | string | UID de l'ESP32 appaire |
| `status` | string | Toujours `ok` |
| `parent_id` | string | UID du gateway parent |

---

#### `garden/pairing/unpair` (QoS 0)

Notification de desappariement.

**Payload :**

```json
{
  "uid": "004b1235062c",
  "action": "unpaired"
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `uid` | string | UID de l'ESP32 desappaire |
| `action` | string | Toujours `unpaired` |

---

#### `garden/alerts/trigger` (QoS 1)

Alerte declenchee par un ESP32.

**Payload :**

```json
{
  "alert_id": "alert-123",
  "cell_uid": "004b1235062c",
  "sensor_type": "HA",
  "sensor_index": 1,
  "value": 54.3,
  "trigger_type": "W",
  "timestamp": "2026-03-30T18:00:00Z"
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `alert_id` | string | ID de l'alerte declenchee |
| `cell_uid` | string | UID de l'ESP32 source |
| `sensor_type` | string | Code du capteur (`TA`, `HA`, etc.) |
| `sensor_index` | int | Index du capteur |
| `value` | float | Valeur mesuree |
| `trigger_type` | string | `C` (Critical) / `W` (Warning) |
| `timestamp` | string | Horodatage du declenchement |

---

#### `garden/alerts/ack/{uid}` (QoS 0)

Confirmation de reception d'une config d'alerte par un ESP32.

**Payload :**

```json
{
  "uid": "004b1235062c",
  "status": "received",
  "data": "alert-123:1:1TA:0:40:5:35",
  "timestamp": "2026-03-30T18:00:01Z"
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `uid` | string | UID de l'ESP32 |
| `status` | string | Toujours `received` |
| `data` | string | Donnees brutes de la config d'alerte |
| `timestamp` | string | Horodatage de la reception |

---

## 4. Resume des flux

### 4.1 Cycle normal (ESP32 -> Pi5 -> Backend)

```
ESP32                          Pi5                         Backend
  |-- B|D|ts|uid|data|E ------>|                              |
  |-- B|D|ts|uid|data|E ------>|                              |
  |-- B|T|ts|uid|alert|E ----->|                              |
  |-- B|S|ts|uid|O;3|E ------>|                              |
  |                            |-- garden/analytics --------->|
  |                            |-- garden/analytics --------->|
  |                            |-- garden/alerts/trigger ---->|
  |<-- B|ACK|ts|uid|OK;S|E ---|                              |
  |-- SleepState               |                              |
```

### 4.2 Cycle avec messages gateway (Pi5 -> ESP32)

```
ESP32                          Pi5                         Backend
  |-- B|D|...|E --------------->|                              |
  |-- B|S|...|O;1|E ---------->|                              |
  |<-- B|ACK|ts|uid|OK;L|E ---|  (L = Listen, gateway a des messages)
  |                            |                              |
  |<-- B|A|ts|uid|config|E ----|  (alert config)              |
  |<-- B|S|ts|uid|O;1|E ------|  (status du gateway)          |
  |-- B|ACK|ts|uid|OK|E ------>|                              |
  |-- SleepState               |                              |
```

### 4.3 Instant Analytics (Backend -> ESP32 via Pi5)

```
Backend                        Pi5                         ESP32 (sleep)
  |-- garden/devices/command -->|                              |
  |   {"command":"instant_analytics"}                          |
  |                            |-- burst 18s ----------------->|
  |                            |   B|C|ts|GATEWAY_PI|IA|E     |  (broadcast)
  |                            |                              |-- wake
  |                            |                              |-- read sensors
  |                            |<-- B|D|ts|uid|data|E --------|
  |<-- garden/analytics -------|                              |
```

### 4.4 Settings Update (Backend -> ESP32 via Pi5)

```
Backend                        Pi5                         ESP32 (sleep)
  |-- garden/devices/settings ->|                              |
  |   {"uid":"004b..","send_interval":30}                      |
  |                            |-- burst 18s ----------------->|
  |                            |   B|C|ts|004b..|SET:...|E    |  (cible)
  |                            |                              |-- wake
  |                            |                              |-- apply config
  |                            |                              |-- save
  |                            |                              |-- SleepState
```

### 4.5 Pairing (Pi5 -> ESP32)

```
Backend                        Pi5                         ESP32 (bouton)
  |-- garden/pairing/request -->|                              |
  |   {"event":"start"}        |                              |
  |                            |-- B|PA|ts|GW|uid;GW|E ------>|
  |                            |<-- B|PA_ACK|ts|uid|OK|E -----|
  |<-- garden/pairing/result --|                              |
  |   {"uid":"004b..","status":"ok"}                          |
```
