# Instant Analytics - Remontee de donnees en temps reel

Ce document decrit le mecanisme d'**Instant Analytics** (IA) qui permet au frontend de demander une remontee immediate des donnees capteurs depuis les ESP32, meme lorsqu'ils sont en mode sleep.

## Apercu general

```
Frontend (MQTT)          Pi5 Gateway              ESP32 (SleepState)
     |                        |                          |
     |-- command: IA -------->|                          |
     |                        |-- LoRa burst (18s) ----->|  (listen window 100ms)
     |                        |-- LoRa burst ----------->|
     |                        |-- LoRa burst ----------->|  <-- capte le message
     |                        |                          |-- wake up -> ActiveState
     |                        |                          |-- read sensors
     |                        |<---- LoRa data (force) --|
     |<-- MQTT data ----------|                          |
     |                        |                          |-- SleepState
```

## Architecture

### Composants impliques

| Composant | Fichier | Role |
|-----------|---------|------|
| **MessageRouter** | `iot-pi5/core/message_router.py` | Recoit la commande MQTT et dispatch |
| **GatewayCore** | `iot-pi5/core/gateway_core.py` | Envoie le burst LoRa aux ESP32 |
| **SleepState** | `iot-esp32/src/core/states.py` | Ecoute LoRa pendant les micro-sleeps |
| **DeviceManager** | `iot-esp32/src/core/device_manager.py` | Dispatch le message, gere la commande IA |
| **CommunicationManager** | `iot-esp32/src/communication/communication_manager.py` | Force l'envoi des donnees (bypass intervalle) |
| **LoRaProtocol** | `iot-esp32/src/communication/lora_protocol.py` | Gestion radio SX1276, pre-check IRQ apres lightsleep |

---

## 1. Declenchement (Pi5)

### 1.1 MQTT - Topic et payload

Le frontend publie sur le topic MQTT :

```
Topic:   garden/devices/command
Payload: {"command": "instant_analytics"}
QoS:     0
```

### 1.2 Routage MQTT

`MessageRouter.route_from_mqtt()` detecte le topic `devices/command` et appelle `_handle_mqtt_device_command()` :

```python
def _handle_mqtt_device_command(self, payload: dict):
    command = payload.get("command")
    if command == "instant_analytics":
        self.gateway.get_instant_analytics()
```

### 1.3 Burst LoRa

`GatewayCore.get_instant_analytics()` envoie le message LoRa **en boucle pendant 18 secondes** dans un thread daemon separe :

```python
BURST_INTERVAL = 0.5   # 500ms entre chaque envoi
BURST_DURATION = 18.0  # couvre le sleep_interval ESP32 (15s) + marge
```

**Pourquoi un burst ?** L'ESP32 en SleepState n'ecoute que 100ms toutes les 1100ms (~9% du temps). Un seul envoi a une faible probabilite d'etre capte. Le burst de 18s garantit que l'ESP32 capte au moins un message, peu importe ou il en est dans son cycle de sleep.

**Calcul de probabilite :**
- Cycle ESP32 : 1000ms sleep + 100ms listen = 1100ms
- En 18s : ~16 cycles, soit ~1600ms de temps d'ecoute total
- Le Pi5 envoie ~36 paquets (un toutes les 500ms)
- Probabilite de capter au moins 1 paquet : >99%

### 1.4 Protocole LoRa - Trame Command

```
Format:  B|C|<timestamp>|<gateway_uid>|IA|E
Exemple: B|C|2026-03-27T15:52:56Z|GATEWAY_PI|IA|E

Champs:
  B             - Delimiteur debut
  C             - Type de message (Command)
  timestamp     - ISO 8601 UTC
  GATEWAY_PI    - UID de l'emetteur (gateway)
  IA            - Donnee = type de commande (Instant Analytics)
  E             - Delimiteur fin
```

Le padding `XXXX` (4 bytes) est ajoute en tete de trame cote ESP32 lors de l'envoi pour compenser un artefact materiel. Cote Pi5, ce padding est gere differemment.

---

## 2. Reception et reveil (ESP32)

### 2.1 SleepState - Micro-sleep avec fenetre d'ecoute

L'ESP32 ne fait pas un sleep continu de 15s. Il utilise un pattern **micro-sleep + listen window** :

```
Configuration (config.json > power):
  sleep_interval:    15      # duree totale de sleep en secondes
  micro_sleep_ms:    1000    # duree d'un micro-sleep (lightsleep)
  listen_timeout_ms: 100     # fenetre d'ecoute LoRa apres chaque micro-sleep
```

```
Boucle SleepState (15 cycles) :
  |-- lightsleep(1000ms) --|-- receive(100ms) --|-- lightsleep(1000ms) --|-- ...
      CPU dort                 radio ecoute          CPU dort
      radio en RX mode         poll IRQ flags        radio en RX mode
```

### 2.2 Problematique : LoRa SX1276 et lightsleep ESP32

C'est le point technique le plus critique du mecanisme.

#### Le probleme

Pendant `lightsleep(1000ms)` :
- Le **CPU ESP32 est arrete** (pas d'execution de code, pas de traitement d'interruptions GPIO)
- Le **radio SX1276 continue de fonctionner** (c'est un chip externe sur SPI, independant du CPU)
- Si le radio est en mode RX, il **peut recevoir un paquet** pendant le lightsleep
- Le flag **RxDone** (bit 6 du registre IRQ 0x12) est positionne sur le SX1276
- Mais l'interruption GPIO (DIO0) **ne peut pas etre traitee** car le CPU dort
- Le callback `_on_receive()` n'est donc **jamais appele** -> `_rx_buffer` reste `None`

#### Le piege initial (corrige)

Sans le pre-check, `receive()` faisait immediatement :

```python
# PROBLEME : ceci efface le flag RxDone AVANT de le verifier !
self._lora._write(0x01, 0x81)  # Standby
self._lora._write(0x12, 0xFF)  # Clear ALL IRQ flags  <-- RxDone perdu !
self._lora.recv()               # RX mode
# -> Le paquet est dans le FIFO mais on ne sait plus qu'il est la
```

Le paquet recu pendant lightsleep etait **dans le FIFO** du SX1276, mais le flag indiquant sa presence etait efface. Le paquet etait perdu silencieusement.

#### La correction : pre-check IRQ

Avant de toucher aux registres, on verifie d'abord si un paquet est deja arrive :

```python
def receive(self, timeout_ms=None):
    # 1. Verifier le buffer software (paquet arrive pendant que le code tournait)
    if self._rx_buffer is not None:
        # ... traiter le buffer
        return msg

    # 2. PRE-CHECK : verifier si le radio a recu pendant lightsleep
    irq_pre = self._lora._read(0x12)
    if irq_pre & 0x40:  # RxDone - paquet recu pendant lightsleep
        self._lora._write(0x01, 0x81)  # Standby pour lire le FIFO en securite
        self._lora._write(0x12, 0xFF)  # Clear IRQ
        raw_payload = self._lora._read_payload()  # Lire le paquet du FIFO
        msg = self._process_raw_payload(raw_payload)
        if msg:
            self._lora.recv()  # Remettre en RX
            return msg

    # 3. Mode normal : Standby -> Clear -> RX -> poll
    self._lora._write(0x01, 0x81)  # Standby
    self._lora._write(0x12, 0xFF)  # Clear IRQ
    self._lora.recv()               # RX mode
    # ... polling loop ...
```

**Ordre des operations dans le registre IRQ (0x12) du SX1276 :**

| Bit | Flag | Signification |
|-----|------|---------------|
| 6 | RxDone | Paquet recu avec succes |
| 5 | CrcError | Erreur CRC detectee |
| 4 | ValidHeader | Header valide recu |
| 3 | TxDone | Transmission terminee |

### 2.3 Assurer le mode RX avant lightsleep

Apres le cycle Active (envoi de donnees), le radio peut rester en **Standby** (post-send). Pour que le radio puisse recevoir pendant le prochain lightsleep, il faut le remettre en RX.

Ceci est fait a la fin de `DeviceManager.run_cycle()` :

```python
# 4. Go back to listening
self.communication.receive(timeout_ms=1)
```

Cet appel force le radio a passer par la sequence `Standby -> Clear IRQ -> RX mode`, garantissant que le premier lightsleep du SleepState aura le radio en ecoute.

### 2.4 Reveil generique

Le SleepState effectue un **reveil generique** sur n'importe quel message LoRa recu (pas uniquement les commandes IA) :

```python
msg = context.communication.receive(timeout_ms=listen_timeout_ms)
if msg:
    context._wake_message = msg       # Sauvegarder pour traitement ulterieur
    context.set_state(ActiveState())   # Transition vers ActiveState
    return
```

Le message brut est stocke dans `context._wake_message`. Aucun parsing de commande n'est fait dans le SleepState - c'est le DeviceManager qui s'en charge.

### 2.5 Nettoyage des IRQ parasites du bouton

`lightsleep()` peut declencher des IRQ parasites sur le pin du bouton de pairing (via `wake_on_ext0`). Le `SleepState.exit()` efface le flag pour eviter un passage non desire en mode pairing :

```python
def exit(self, context):
    context._pairing_requested = False
```

---

## 3. Dispatch et traitement de la commande (ESP32)

### 3.1 Dispatch du wake message

Dans la boucle principale de `DeviceManager.run()`, apres la gestion du bouton mais avant `state_manager.handle()` :

```python
if self._wake_message:
    msg = self._wake_message
    self._wake_message = None
    self.communication._handle_incoming(msg)
```

`_handle_incoming()` verifie l'UID et publie l'evenement sur l'EventBus :
- Event : `message.received.C`
- Handler : `DeviceManager._handle_command_message()`

### 3.2 Verification UID

`_handle_incoming()` appelle `_check_my_uid(uid)` qui accepte :
- **L'UID du device** (`004b1235062c`) - messages adresses a ce device
- **L'UID du parent/gateway** (`GATEWAY_PI`) - messages broadcast depuis le gateway

```python
def _check_my_uid(self, uid):
    if self._device_uid and uid == self._device_uid:
        return True
    parent_id = self._config.get('device.parent_id') if self._config else None
    if parent_id and uid == parent_id:
        return True
    return False
```

### 3.3 Traitement de la commande IA

```python
def _handle_command_message(self, message):
    command = message.get('data', '')
    if command == 'IA':
        self.communication._force_send = True
        if not isinstance(self.state_manager.current_state, ActiveState):
            self.state_manager.set_state(ActiveState())
```

Actions :
1. **`_force_send = True`** sur le CommunicationManager
2. **Transition ActiveState** si pas deja actif (dans le cas du reveil depuis SleepState, on est deja en ActiveState)

---

## 4. Envoi force des donnees (ESP32)

### 4.1 Bypass de l'intervalle d'envoi

Normalement, `_check_send_conditions()` verifie que suffisamment de temps s'est ecoule depuis le dernier envoi (`send_interval` en config). Avec `_force_send`, cette verification est bypassee :

```python
def _check_send_conditions(self, timestamp):
    if self._force_send:
        self._force_send = False  # Reset apres utilisation (one-shot)
        return True

    # Verification normale de l'intervalle...
    send_interval = self._config.get('device.send_interval', 60)
    now = time.time()
    if self.last_send_time is None or (now - self.last_send_time) >= send_interval:
        return True
    return False
```

### 4.2 Flux complet de l'envoi force

```
_handle_command_message('IA')
  -> _force_send = True

ActiveState.handle()
  -> run_cycle()
    -> SensorManager.read_all()         # Lecture capteurs
    -> event_bus.publish('sensor.data.ready', data)
      -> CommunicationManager._on_sensor_data_ready()
        -> _message_queue.append(data)
        -> _check_send_conditions()      # _force_send = True -> return True
        -> event_bus.publish('cycle.communication.send')
          -> _cycle_communication_send()
            -> _do_send_cycle()          # Envoi LoRa de tous les messages en queue
            -> Attente ACK du gateway
  -> SleepState()
```

---

## 5. Types de commandes supportes

Le systeme de commandes est generique et extensible via le topic MQTT `garden/devices/command` :

| Commande MQTT | Code LoRa | Description |
|---------------|-----------|-------------|
| `instant_analytics` | `IA` | Remontee immediate des donnees capteurs |
| `reboot` | `REBOOT` | Redemarrage du device |
| `factory_reset` | `RESET_CONFIG` | Reinitialisation de la configuration |

Pour ajouter une nouvelle commande :
1. Ajouter le cas dans `MessageRouter._handle_mqtt_device_command()` (Pi5)
2. Implementer l'action dans `GatewayCore` (Pi5)
3. Ajouter le cas dans `DeviceManager._handle_command_message()` (ESP32)

---

## 6. Configuration

### ESP32 (`config.json`)

```json
{
  "power": {
    "sleep_interval": 15,
    "micro_sleep_ms": 1000,
    "listen_timeout_ms": 100
  },
  "device": {
    "send_interval": 60
  }
}
```

### Pi5 (`gateway_core.py`)

```python
BURST_INTERVAL = 0.5   # 500ms entre chaque envoi LoRa
BURST_DURATION = 18.0  # Doit couvrir sleep_interval + marge
```

> **Important :** `BURST_DURATION` doit etre >= `sleep_interval` + `micro_sleep_ms/1000` pour garantir que l'ESP32 capte au moins un message.

---

## 7. Diagramme temporel detaille

```
Temps (ms)    ESP32                           Pi5
0             |-- lightsleep(1000) ---------->|
              |   CPU dort, radio RX          |
1000          |   wake                        |
1000-1100     |-- receive(100ms) ------------>|  (poll IRQ, rien recu)
1100          |-- lightsleep(1000) ---------->|
              |                               |
1500          |                               |<-- MQTT: instant_analytics
              |                               |-- Thread burst demarre
1500          |                               |-- LoRa send B|C|...|IA|E
2000          |                               |-- LoRa send B|C|...|IA|E
2100          |   wake                        |
              |-- receive(100ms)              |
              |   pre-check IRQ: RxDone=1 !   |
              |   lire FIFO -> message IA     |
              |   return message              |
              |                               |
2100          |-- _wake_message = msg         |
              |-- set_state(ActiveState)      |
              |                               |
              | [main loop]                   |
              |-- dispatch _wake_message      |
              |   -> _handle_incoming         |
              |   -> _check_my_uid(GATEWAY_PI)|  = True (parent)
              |   -> event: message.received.C|
              |   -> _handle_command_message  |
              |   -> _force_send = True       |
              |                               |
              | [ActiveState.handle()]        |
              |-- run_cycle()                 |
              |   read sensors                |
              |   queue data                  |
              |   _check_send_conditions      |
              |   -> _force_send -> True      |
              |-- LoRa send data ------------>|-- receive data
              |   wait ACK                    |-- process + MQTT publish
              |<-- LoRa ACK ------------------|
              |                               |
              |-- SleepState                  |
              |-- lightsleep(1000)...         |-- burst continue (thread)
              |                               |
19500         |                               |-- burst termine (18s)
```

---

## 8. Bugs connus et corrections appliquees

### 8.1 Paquet perdu apres lightsleep
- **Cause :** `receive()` effacait les IRQ flags avant de verifier si un paquet etait arrive pendant le sleep
- **Fix :** Pre-check du registre IRQ (bit RxDone) avant toute operation de clear
- **Fichier :** `lora_protocol.py` - methode `receive()`

### 8.2 Radio en Standby au debut du sleep
- **Cause :** Apres `send()` dans ActiveState, le radio reste en Standby, donc le premier lightsleep ne peut rien recevoir
- **Fix :** Appel `receive(timeout_ms=1)` a la fin de `run_cycle()` pour forcer le radio en RX
- **Fichier :** `device_manager.py` - methode `run_cycle()`

### 8.3 Burst trop court
- **Cause :** Burst initial de 3s ne couvrait pas le sleep interval de 15s
- **Fix :** Burst augmente a 18s avec envoi toutes les 500ms
- **Fichier :** `gateway_core.py` - methode `get_instant_analytics()`

### 8.4 UID non reconnu pour les commandes gateway
- **Cause :** `_check_my_uid()` ne reconnaissait que l'UID du device, pas celui du gateway
- **Fix :** Accepter aussi le `parent_id` (gateway) comme UID valide
- **Fichier :** `communication_manager.py` - methode `_check_my_uid()`

### 8.5 IRQ parasites du bouton apres lightsleep
- **Cause :** `lightsleep()` + `wake_on_ext0` declenchait des IRQ parasites sur le pin bouton
- **Fix :** `SleepState.exit()` efface `_pairing_requested`
- **Fichier :** `states.py` - methode `SleepState.exit()`
