# 📐 Design Patterns IoT - Documentation

## Table des matières

- [Introduction](#introduction)
- [Vue d'ensemble de l'architecture](#vue-densemble-de-larchitecture)
- [1. Singleton Pattern](#1-singleton-pattern)
- [2. Factory Pattern](#2-factory-pattern)
- [3. Strategy Pattern](#3-strategy-pattern)
- [4. Observer Pattern](#4-observer-pattern)
- [5. State Pattern](#5-state-pattern)
- [6. Template Method Pattern](#6-template-method-pattern)
- [7. Adapter Pattern](#7-adapter-pattern)
- [8. Retry / Circuit Breaker Pattern](#8-retry--circuit-breaker-pattern)
- [9. Data Transfer Object (DTO) Pattern](#9-data-transfer-object-dto-pattern)
- [10. Façade Pattern](#10-façade-pattern)
- [Résumé des patterns et leur localisation](#résumé-des-patterns-et-leur-localisation)
- [Structure du projet](#structure-du-projet)
- [Bonnes pratiques IoT](#bonnes-pratiques-iot)
- [Glossaire](#glossaire)

---

## Introduction

Ce document décrit les design patterns mis en place dans le projet IoT embarqué sur **ESP32** et **Pico W**. L'objectif est de fournir une architecture **modulaire**, **maintenable** et **scalable**, adaptée aux contraintes de l'embarqué (mémoire limitée, consommation énergétique, fiabilité).

### Pourquoi utiliser des design patterns en IoT ?

| Problème                                 | Solution apportée                    |
| ---------------------------------------- | ------------------------------------ |
| Code spaghetti difficile à maintenir     | Architecture structurée et modulaire |
| Ajout de nouveaux capteurs complexe      | Factory Pattern → ajout en une ligne |
| Changement de protocole de communication | Strategy Pattern → interchangeable   |
| Gestion des alertes couplée aux capteurs | Observer Pattern → découplage total  |
| Ressources partagées (config, pins)      | Singleton Pattern → instance unique  |
| États du device mal gérés                | State Pattern → transitions claires  |

---

## Vue d'ensemble de l'architecture

```
┌─────────────────────────────────────────────────────┐
│                    main.py                          │
│               (Point d'entrée)                      │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              DeviceManager (Singleton)               │
│         Orchestrateur principal du device            │
├─────────────┬───────────────┬───────────────────────┤
│             │               │                       │
▼             ▼               ▼                       ▼
┌─────────┐ ┌─────────────┐ ┌──────────────┐ ┌──────────────┐
│ Config  │ │  Sensors    │ │Communication │ │   Alerts     │
│ Manager │ │  (Factory)  │ │ (Strategy)   │ │ (Observer)   │
│Singleton│ │             │ │              │ │              │
└─────────┘ └──────┬──────┘ └──────┬───────┘ └──────────────┘
                   │               │
           ┌───────┼───────┐   ┌───┼────┐
           ▼       ▼       ▼   ▼        ▼
        DHT22  BMP280  BH1750 LoRa    WiFi
       (Template Method)     (Strategy)
```

---

## 1. Singleton Pattern

### 🎯 Pourquoi ?

En IoT embarqué, certaines ressources **ne doivent exister qu'en une seule instance** :

- La **configuration** du device (pins, paramètres, seuils)
- Le **gestionnaire principal** du device
- La **connexion série** ou réseau

Sans Singleton, on risque :

- Des conflits d'accès aux ressources matérielles (pins, bus I2C/SPI)
- Une consommation mémoire excessive (duplication de données)
- Des incohérences de configuration

### 📖 Comment ça marche ?

Le Singleton garantit qu'une classe n'a **qu'une seule instance** dans tout le programme. Chaque appel au constructeur retourne la même instance.

```
Premier appel :   ConfigManager() → Crée l'instance → Retourne l'instance
Deuxième appel :  ConfigManager() → Instance existe déjà → Retourne la même instance
Troisième appel : ConfigManager() → Instance existe déjà → Retourne la même instance
```

### 💻 Implémentation

```python
# config/config_manager.py

import json

class ConfigManager:
    """
    Singleton pour la gestion centralisée de la configuration.
    Garantit une seule instance dans tout le programme.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._config = self._load_config()
        self._initialized = True

    def _load_config(self):
        """Charge la configuration depuis le fichier JSON"""
        try:
            with open('config/config.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}

    def get(self, *keys, default=None):
        """Accès à une valeur de configuration par clés imbriquées"""
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default
        return value

    def get_config(self):
        """Retourne la configuration complète"""
        return self._config
```

### 🔍 Utilisation

```python
# N'importe où dans le code :
config = ConfigManager()           # Toujours la même instance
interval = config.get('read_interval', default=60)
lora_freq = config.get('lora', 'frequency', default=868.0)
```

### Où l'appliquer dans le projet

| Classe          | Raison                            |
| --------------- | --------------------------------- |
| `ConfigManager` | Une seule source de configuration |
| `DeviceManager` | Un seul orchestrateur             |
| `PowerManager`  | Un seul gestionnaire d'énergie    |

---

## 2. Factory Pattern

### 🎯 Pourquoi ?

Dans un projet IoT, on utilise **plusieurs types de capteurs** (DHT22, BMP280, BH1750, DS18B20, LM393...). Sans Factory :

```python
#  Sans Factory Pattern - code rigide et répétitif
if sensor_type == "dht22":
    sensor = DHT22Sensor(pin=4)
elif sensor_type == "bmp280":
    sensor = BMP280Sensor(scl=22, sda=21)
elif sensor_type == "bh1750":
    sensor = BH1750Sensor(scl=22, sda=21)
# ... à chaque nouveau capteur, modifier ce code partout
```

Avec Factory :

```python
#  Avec Factory Pattern - simple et extensible
sensor = SensorFactory.create("dht22", pin=4)
```

### 📖 Comment ça marche ?

La Factory centralise la **création d'objets**. Elle associe un identifiant (string) à une classe concrète, et retourne une instance prête à l'emploi.

```
SensorFactory.create("dht22", pin=4)
       │
       ▼
┌─────────────────────────────┐
│     Registry (dictionnaire) │
│  "dht22"   → DHT22Sensor   │
│  "bmp280"  → BMP280Sensor  │
│  "bh1750"  → BH1750Sensor  │
│  "ds18b20" → DS18B20Sensor │
│  "lm393"   → LM393Sensor   │
└──────────────┬──────────────┘
               ▼
       DHT22Sensor(pin=4)
       → instance retournée
```

### 💻 Implémentation

```python
# sensors/sensor_factory.py

class SensorFactory:
    """
    Factory pour instancier des capteurs à partir de leur type.
    Permet d'ajouter de nouveaux capteurs sans modifier le code existant.
    """
    _registry = {}

    @classmethod
    def register(cls, sensor_type, sensor_class):
        """Enregistre un nouveau type de capteur dans la factory"""
        cls._registry[sensor_type.lower()] = sensor_class

    @classmethod
    def create(cls, sensor_type, **kwargs):
        """Crée une instance de capteur à partir de son type"""
        sensor_class = cls._registry.get(sensor_type.lower())
        if not sensor_class:
            raise ValueError(
                f"Unknown sensor type: '{sensor_type}'. "
                f"Available: {list(cls._registry.keys())}"
            )
        return sensor_class(**kwargs)

    @classmethod
    def create_from_config(cls, config):
        """Crée tous les capteurs définis dans la configuration"""
        sensors = []
        for sensor_cfg in config.get('sensors', []):
            try:
                sensor = cls.create(
                    sensor_cfg['type'],
                    name=sensor_cfg.get('name', sensor_cfg['type']),
                    pin=sensor_cfg.get('pin'),
                    **sensor_cfg.get('params', {})
                )
                sensors.append(sensor)
                print(f"  ✓ Sensor '{sensor.name}' initialized")
            except Exception as e:
                print(f"  ✗ Failed to create sensor '{sensor_cfg.get('type')}': {e}")
        return sensors
```

### 🔍 Utilisation

```python
# Enregistrement des capteurs (au démarrage)
from sensors.dht22_sensor import DHT22Sensor
from sensors.bmp280_sensor import BMP280Sensor

SensorFactory.register("dht22", DHT22Sensor)
SensorFactory.register("bmp280", BMP280Sensor)

# Création depuis la config.json
sensors = SensorFactory.create_from_config(config)

# Ou création manuelle
dht = SensorFactory.create("dht22", name="temp_ext", pin=4)
```

### 📄 Configuration associée (config.json)

```json
{
  "sensors": [
    {
      "type": "dht22",
      "name": "temperature_humidity",
      "pin": 4
    },
    {
      "type": "bmp280",
      "name": "pressure",
      "params": {
        "scl": 22,
        "sda": 21
      }
    },
    {
      "type": "bh1750",
      "name": "luminosity",
      "params": {
        "scl": 22,
        "sda": 21
      }
    }
  ]
}
```

### Avantages concrets

- **Ajouter un capteur** = créer une classe + une ligne `register()`
- **Configuration dynamique** depuis un fichier JSON
- **Aucune modification** du code existant (principe Open/Closed)

---

## 3. Strategy Pattern

### 🎯 Pourquoi ?

Un device IoT peut communiquer via **plusieurs protocoles** :

- **LoRa** pour les longues distances sans WiFi
- **WiFi/HTTP** pour les communications locales
- **MQTT** pour le temps réel
- **Bluetooth** pour la configuration

Sans Strategy, le code de communication serait **couplé** au reste de l'application :

```python
#  Sans Strategy - code couplé et difficile à modifier
def send_data(data):
    if mode == "lora":
        # 50 lignes de code LoRa
        pass
    elif mode == "wifi":
        # 50 lignes de code WiFi
        pass
    elif mode == "mqtt":
        # 50 lignes de code MQTT
        pass
```

### 📖 Comment ça marche ?

On définit une **interface commune** pour tous les protocoles. Le `CommunicationManager` délègue l'envoi à la stratégie active, qui peut être **changée à chaud**.

```
┌─────────────────────────┐
│  CommunicationManager   │
│  (utilise une stratégie) │
└───────────┬─────────────┘
            │ send(data)
            ▼
┌─────────────────────────┐
│  CommunicationProtocol  │  ← Interface commune
│  (classe abstraite)     │
├─────────────────────────┤
│  + connect()            │
│  + send(data)           │
│  + disconnect()         │
│  + is_connected()       │
└─────┬─────────┬─────────┘
      │         │
      ▼         ▼
┌──────────┐ ┌──────────┐
│LoRa      │ │WiFi      │
│Protocol  │ │Protocol  │
└──────────┘ └──────────┘
```

### 💻 Implémentation

```python
# communication/base_protocol.py

class CommunicationProtocol:
    """Interface commune pour tous les protocoles de communication"""

    def __init__(self, name):
        self.name = name
        self._connected = False

    def connect(self):
        """Établir la connexion"""
        raise NotImplementedError

    def disconnect(self):
        """Fermer la connexion"""
        raise NotImplementedError

    def send(self, data):
        """Envoyer des données"""
        raise NotImplementedError

    def receive(self):
        """Recevoir des données"""
        raise NotImplementedError

    def is_connected(self):
        """Vérifier l'état de la connexion"""
        return self._connected
```

```python
# communication/lora_protocol.py

from communication.base_protocol import CommunicationProtocol
from lib.ulora import LoRa

class LoRaProtocol(CommunicationProtocol):
    """Stratégie de communication via LoRa"""

    def __init__(self, config):
        super().__init__("LoRa")
        self.frequency = config.get('frequency', 868.0)
        self.sf = config.get('spreading_factor', 7)
        self._lora = None

    def connect(self):
        self._lora = LoRa(self.frequency, self.sf)
        self._connected = True
        print(f"[{self.name}] Connected at {self.frequency}MHz")

    def send(self, data):
        if not self._connected:
            self.connect()
        payload = self._encode(data)
        self._lora.send(payload)
        print(f"[{self.name}] Data sent ({len(payload)} bytes)")

    def disconnect(self):
        self._lora = None
        self._connected = False

    def _encode(self, data):
        """Encode les données pour la transmission LoRa"""
        import json
        return json.dumps(data)
```

```python
# communication/wifi_protocol.py

from communication.base_protocol import CommunicationProtocol
import urequests

class WiFiProtocol(CommunicationProtocol):
    """Stratégie de communication via WiFi/HTTP"""

    def __init__(self, config):
        super().__init__("WiFi")
        self.ssid = config.get('ssid')
        self.password = config.get('password')
        self.endpoint = config.get('endpoint')

    def connect(self):
        import network
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(self.ssid, self.password)
        self._connected = True
        print(f"[{self.name}] Connected to {self.ssid}")

    def send(self, data):
        if not self._connected:
            self.connect()
        import json
        response = urequests.post(
            self.endpoint,
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        print(f"[{self.name}] HTTP {response.status_code}")
        response.close()

    def disconnect(self):
        self._connected = False
```

```python
# communication/communication_manager.py

class CommunicationManager:
    """
    Gestionnaire de communication utilisant le Strategy Pattern.
    Permet de changer de protocole à chaud.
    """

    def __init__(self, strategy=None):
        self._strategy = strategy
        self._fallback = None

    def set_strategy(self, strategy):
        """Changer la stratégie de communication"""
        print(f"Communication switched to: {strategy.name}")
        self._strategy = strategy

    def set_fallback(self, fallback_strategy):
        """Définir une stratégie de repli"""
        self._fallback = fallback_strategy

    def send(self, data):
        """Envoyer des données avec la stratégie active"""
        try:
            self._strategy.send(data)
        except Exception as e:
            print(f"Send failed via {self._strategy.name}: {e}")
            if self._fallback:
                print(f"Falling back to {self._fallback.name}")
                self._fallback.send(data)
```

### 🔍 Utilisation

```python
# Initialisation
lora = LoRaProtocol(config.get('lora'))
wifi = WiFiProtocol(config.get('wifi'))

comm = CommunicationManager(strategy=lora)
comm.set_fallback(wifi)  # WiFi en secours

# Envoi → utilise LoRa, bascule sur WiFi si échec
comm.send(sensor_data)

# Changement de stratégie à chaud
comm.set_strategy(wifi)
```

### Avantages concrets

- **Changement de protocole** sans modifier le code métier
- **Fallback automatique** si un protocole échoue
- **Ajout de nouveaux protocoles** sans toucher au code existant

---

## 4. Observer Pattern

### 🎯 Pourquoi ?

Dans un système IoT, **plusieurs modules** doivent réagir aux données des capteurs :

- **AlertManager** → déclencher une alerte si un seuil est dépassé
- **Logger** → enregistrer les données
- **Display** → mettre à jour un écran
- **CommunicationManager** → envoyer les données

Sans Observer, chaque capteur devrait **connaître** tous les modules → **couplage fort**.

```python
#  Sans Observer - le capteur connaît tout le monde
def read_sensor():
    data = get_data()
    alert_manager.check(data)      # couplé à AlertManager
    logger.log(data)               # couplé à Logger
    display.update(data)           # couplé à Display
    comm.send(data)                # couplé à CommunicationManager
```

### 📖 Comment ça marche ?

Les capteurs (Subject) **notifient** les modules intéressés (Observers) sans les connaître directement.

```
┌──────────────────┐
│  SensorManager   │  (Subject)
│  ─────────────── │
│  observers = [   │
│    AlertManager, │─────────┐
│    Logger,       │──────┐  │
│    Display       │───┐  │  │
│  ]               │   │  │  │
└────────┬─────────┘   │  │  │
         │ notify()    │  │  │
         │             │  │  │
         ▼             ▼  ▼  ▼
   Données envoyées à tous les observers
```

### 💻 Implémentation

```python
# managers/event_bus.py

class EventBus:
    """
    Bus d'événements central (Observer Pattern).
    Permet aux modules de s'abonner à des événements sans couplage.
    """

    def __init__(self):
        self._subscribers = {}

    def subscribe(self, event_type, callback):
        """S'abonner à un type d'événement"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        print(f"  ✓ Subscribed to '{event_type}'")

    def unsubscribe(self, event_type, callback):
        """Se désabonner d'un type d'événement"""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)

    def publish(self, event_type, data=None):
        """Publier un événement à tous les abonnés"""
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Error in subscriber for '{event_type}': {e}")
```

```python
# managers/alert_manager.py

class AlertManager:
    """
    Observer qui surveille les seuils d'alerte.
    S'abonne aux événements de lecture des capteurs.
    """

    def __init__(self, config):
        self._thresholds = config.get('thresholds', {})
        self._alerts_active = {}

    def on_sensor_data(self, data):
        """Callback appelé quand un capteur publie des données"""
        sensor_name = data.get('sensor')
        readings = data.get('data', {})

        for metric, value in readings.items():
            threshold = self._thresholds.get(sensor_name, {}).get(metric)
            if threshold:
                self._check_threshold(sensor_name, metric, value, threshold)

    def _check_threshold(self, sensor, metric, value, threshold):
        """Vérifie si une valeur dépasse un seuil"""
        alert_key = f"{sensor}.{metric}"

        if 'max' in threshold and value > threshold['max']:
            if alert_key not in self._alerts_active:
                self._alerts_active[alert_key] = True
                print(f"  🚨 ALERT: {sensor}/{metric} = {value} > {threshold['max']}")

        elif 'min' in threshold and value < threshold['min']:
            if alert_key not in self._alerts_active:
                self._alerts_active[alert_key] = True
                print(f"  🚨 ALERT: {sensor}/{metric} = {value} < {threshold['min']}")

        else:
            if alert_key in self._alerts_active:
                del self._alerts_active[alert_key]
                print(f"   Alert cleared: {sensor}/{metric} = {value}")
```

### 🔍 Utilisation

```python
# Initialisation
event_bus = EventBus()
alert_manager = AlertManager(config)

# Abonnement aux événements
event_bus.subscribe("sensor.data", alert_manager.on_sensor_data)
event_bus.subscribe("sensor.data", logger.on_sensor_data)
event_bus.subscribe("sensor.error", alert_manager.on_sensor_error)

# Publication (dans SensorManager)
event_bus.publish("sensor.data", {
    'sensor': 'dht22',
    'data': {'temperature': 35.2, 'humidity': 80}
})
# → AlertManager ET Logger sont notifiés automatiquement
```

### Avantages concrets

- **Découplage total** entre capteurs et modules de traitement
- **Ajout d'un observer** sans modifier les capteurs
- **Événements typés** (`sensor.data`, `sensor.error`, `alert.triggered`)

---

## 5. State Pattern

### 🎯 Pourquoi ?

Un device IoT passe par **plusieurs états** au cours de son cycle de vie :

```
BOOT → PAIRING → ACTIVE → SLEEP → ACTIVE → ERROR → RECOVERY → ACTIVE
```

Sans State Pattern, on obtient des `if/elif` interminables :

```python
#  Sans State Pattern
while True:
    if state == "booting":
        # 20 lignes...
    elif state == "pairing":
        # 30 lignes...
    elif state == "active":
        # 40 lignes...
    elif state == "sleeping":
        # 15 lignes...
    elif state == "error":
        # 25 lignes...
```

### 📖 Comment ça marche ?

Chaque état est une **classe** avec son propre comportement. Le device délègue à l'état courant.

```
┌─────────────────────┐
│   DeviceContext     │
│   ───────────────── │
│   current_state ────┼──→ ActiveState
│   set_state()       │         │
│   request()    ─────┼─────→ handle(context)
└─────────────────────┘         │
                                ▼
                        read_sensors()
                        send_data()
                        → set_state(SleepState)

┌────────────┐  ┌────────────┐  ┌─────────────┐  ┌────────────┐
│ BootState  │→ │PairingState│→ │ ActiveState  │→ │ SleepState │
│            │  │            │  │              │  │            │
│ init HW    │  │ wait pair  │  │ read sensors │  │ deep sleep │
│ load config│  │ exchange ID│  │ send data    │  │ wake timer │
│ → Pairing  │  │ → Active   │  │ → Sleep      │  │ → Active   │
└────────────┘  └────────────┘  └─────────────┘  └────────────┘
                                       │
                                       ▼ (si erreur)
                                ┌─────────────┐
                                │ ErrorState  │
                                │             │
                                │ log error   │
                                │ retry logic │
                                │ → Active    │
                                └─────────────┘
```

### 💻 Implémentation

```python
# core/states.py

class DeviceState:
    """Classe de base pour les états du device"""

    name = "base"

    def enter(self, context):
        """Appelé quand le device entre dans cet état"""
        print(f"[STATE] Entering: {self.name}")

    def handle(self, context):
        """Comportement de l'état - à surcharger"""
        raise NotImplementedError

    def exit(self, context):
        """Appelé quand le device quitte cet état"""
        pass


class BootState(DeviceState):
    """État de démarrage : initialisation du matériel"""

    name = "BOOT"

    def handle(self, context):
        print("  Loading configuration...")
        context.config.load()
        print("  Initializing hardware...")
        context.init_hardware()
        # Transition vers Pairing ou Active
        if context.config.get('pairing', 'required', default=False):
            context.set_state(PairingState())
        else:
            context.set_state(ActiveState())


class PairingState(DeviceState):
    """État d'appairage : association avec la gateway"""

    name = "PAIRING"

    def handle(self, context):
        print("  Waiting for pairing...")
        success = context.pairing_manager.start_pairing()
        if success:
            print("  ✓ Pairing successful")
            context.set_state(ActiveState())
        else:
            print("  ✗ Pairing failed, retrying...")
            import time
            time.sleep(5)


class ActiveState(DeviceState):
    """État actif : lecture des capteurs et envoi des données"""

    name = "ACTIVE"

    def handle(self, context):
        try:
            # Lire tous les capteurs
            data = context.sensor_manager.read_all()

            # Publier les données
            context.event_bus.publish("sensor.data", data)

            # Envoyer via le protocole de communication
            context.communication.send(data)

            # Transition vers Sleep
            context.set_state(SleepState())

        except Exception as e:
            print(f"  ✗ Error in active state: {e}")
            context.set_state(ErrorState(error=e))


class SleepState(DeviceState):
    """État de veille : économie d'énergie"""

    name = "SLEEP"

    def handle(self, context):
        sleep_duration = context.config.get('power', 'sleep_duration', default=60)
        print(f"  Sleeping for {sleep_duration}s...")
        context.power_manager.deep_sleep(sleep_duration)
        # Au réveil → retour en Active
        context.set_state(ActiveState())


class ErrorState(DeviceState):
    """État d'erreur : tentative de récupération"""

    name = "ERROR"
    MAX_RETRIES = 3

    def __init__(self, error=None):
        self.error = error
        self.retry_count = 0

    def handle(self, context):
        print(f"  Error: {self.error}")
        self.retry_count += 1

        if self.retry_count <= self.MAX_RETRIES:
            print(f"  Retry {self.retry_count}/{self.MAX_RETRIES}...")
            import time
            time.sleep(5)
            context.set_state(ActiveState())
        else:
            print("  Max retries reached. Rebooting...")
            import machine
            machine.reset()
```

### 🔍 Utilisation

```python
# Dans DeviceManager
class DeviceManager:
    def __init__(self):
        self._state = BootState()

    def set_state(self, new_state):
        self._state.exit(self)
        self._state = new_state
        self._state.enter(self)

    def run(self):
        while True:
            self._state.handle(self)
```

### Avantages concrets

- **Chaque état est isolé** dans sa propre classe
- **Transitions explicites** et faciles à suivre
- **Ajout d'un nouvel état** sans modifier les autres
- **Debug simplifié** grâce aux logs d'état

---

## 6. Template Method Pattern

### 🎯 Pourquoi ?

Tous les capteurs suivent le **même processus** de lecture :

1. Vérifier que le capteur est prêt
2. Lire les données brutes
3. Valider les données
4. Formater le résultat

Seules les étapes 2 et 3 changent selon le capteur. Le Template Method définit le **squelette** de l'algorithme et laisse les sous-classes implémenter les parties variables.

### 📖 Comment ça marche ?

```
BaseSensor.read()           ← Méthode template (ne change jamais)
    │
    ├── _check_ready()      ← Commun à tous
    ├── _read_raw()         ← Spécifique à chaque capteur
    ├── _validate(data)     ← Spécifique à chaque capteur
    └── _format_data(data)  ← Commun à tous
```

### 💻 Implémentation

```python
# sensors/base_sensor.py

import time

class BaseSensor:
    """
    Classe de base pour tous les capteurs.
    Utilise le Template Method Pattern pour standardiser la lecture.
    """

    def __init__(self, name, pin=None, **kwargs):
        self.name = name
        self.pin = pin
        self._last_reading = None
        self._last_read_time = 0
        self._read_interval = kwargs.get('read_interval', 2)
        self._error_count = 0
        self._max_errors = 5

    # ═══════════════════════════════════════
    # TEMPLATE METHOD - Ne pas surcharger
    # ═══════════════════════════════════════

    def read(self, force=False):
        """
        Méthode template : définit le processus de lecture.
        Les sous-classes implémentent _read_raw() et _validate().
        """
        # Étape 1 : Vérifier le cache
        if not force and not self._should_read():
            return self._last_reading

        # Étape 2 : Lire les données brutes
        try:
            raw_data = self._read_raw()
        except Exception as e:
            self._error_count += 1
            print(f"  ✗ [{self.name}] Read error: {e}")
            return self._last_reading

        # Étape 3 : Valider les données
        if not self._validate(raw_data):
            self._error_count += 1
            print(f"  ✗ [{self.name}] Invalid data: {raw_data}")
            return self._last_reading

        # Étape 4 : Formater et retourner
        self._error_count = 0
        self._last_reading = self._format_data(raw_data)
        self._last_read_time = time.time()
        return self._last_reading

    # ═══════════════════════════════════════
    # MÉTHODES À IMPLÉMENTER (sous-classes)
    # ═══════════════════════════════════════

    def _read_raw(self):
        """Lecture brute du capteur - À IMPLÉMENTER"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _read_raw()"
        )

    def _validate(self, data):
        """Validation des données - À IMPLÉMENTER"""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _validate()"
        )

    # ═══════════════════════════════════════
    # MÉTHODES COMMUNES (optionnellement surchargeables)
    # ═══════════════════════════════════════

    def _should_read(self):
        """Vérifie si assez de temps s'est écoulé depuis la dernière lecture"""
        return (time.time() - self._last_read_time) >= self._read_interval

    def _format_data(self, raw_data):
        """Formate les données pour l'envoi"""
        return {
            'sensor': self.name,
            'type': self.__class__.__name__,
            'timestamp': time.time(),
            'data': raw_data,
            'errors': self._error_count
        }

    def is_healthy(self):
        """Vérifie si le capteur fonctionne correctement"""
        return self._error_count < self._max_errors
```

```python
# sensors/dht22_sensor.py

from sensors.base_sensor import BaseSensor
import dht
from machine import Pin

class DHT22Sensor(BaseSensor):
    """Capteur de température et humidité DHT22"""

    def __init__(self, name="dht22", pin=4, **kwargs):
        super().__init__(name, pin, **kwargs)
        self._sensor = dht.DHT22(Pin(self.pin))

    def _read_raw(self):
        """Lecture spécifique au DHT22"""
        self._sensor.measure()
        return {
            'temperature': self._sensor.temperature(),
            'humidity': self._sensor.humidity()
        }

    def _validate(self, data):
        """Validation spécifique au DHT22"""
        temp = data.get('temperature', None)
        hum = data.get('humidity', None)
        return (
            temp is not None and -40 <= temp <= 80 and
            hum is not None and 0 <= hum <= 100
        )
```

```python
# sensors/bmp280_sensor.py

from sensors.base_sensor import BaseSensor
from lib.bmp280 import BMP280
from machine import Pin, I2C

class BMP280Sensor(BaseSensor):
    """Capteur de pression et température BMP280"""

    def __init__(self, name="bmp280", pin=None, scl=22, sda=21, **kwargs):
        super().__init__(name, pin, **kwargs)
        i2c = I2C(0, scl=Pin(scl), sda=Pin(sda))
        self._sensor = BMP280(i2c)

    def _read_raw(self):
        """Lecture spécifique au BMP280"""
        return {
            'temperature': self._sensor.temperature,
            'pressure': self._sensor.pressure
        }

    def _validate(self, data):
        """Validation spécifique au BMP280"""
        temp = data.get('temperature', None)
        pressure = data.get('pressure', None)
        return (
            temp is not None and -40 <= temp <= 85 and
            pressure is not None and 300 <= pressure <= 1100
        )
```

### Avantages concrets

- **Pas de duplication** de la logique de cache, validation, formatage
- **Nouveau capteur** = implémenter seulement `_read_raw()` et `_validate()`
- **Cohérence** du format de sortie entre tous les capteurs

---

## 7. Adapter Pattern

### 🎯 Pourquoi ?

Les bibliothèques tierces (dans `lib/`) ont chacune une **API différente** :

```python
# bmp280.py → accès par propriété
bmp.temperature
bmp.pressure

# dht.py → accès par méthode
dht.measure()
dht.temperature()

# bh1750.py → accès par méthode avec format différent
bh.luminance(BH1750.ONCE_HIRES_1)
```

L'Adapter **uniformise** ces interfaces pour que `BaseSensor` puisse les utiliser de manière transparente.

### 📖 Comment ça marche ?

```
Code métier
    │
    ▼
┌──────────────┐      ┌──────────────┐
│   Adapter    │ ───→ │  Lib tierce  │
│ (interface   │      │  (API native)│
│  uniforme)   │      │              │
└──────────────┘      └──────────────┘

Exemple :
┌──────────────────┐      ┌──────────────┐
│ BMP280Sensor     │ ───→ │ lib/bmp280.py│
│   _read_raw()    │      │  .temperature│
│   → { temp, prs }│      │  .pressure   │
└──────────────────┘      └──────────────┘

┌──────────────────┐      ┌──────────────┐
│ DHT22Sensor      │ ───→ │ dht (builtin)│
│   _read_raw()    │      │  .measure()  │
│   → { temp, hum }│      │  .temperature│
└──────────────────┘      └──────────────┘
```

### 💻 Implémentation

```python
# sensors/bh1750_sensor.py

from sensors.base_sensor import BaseSensor
from lib.bh1750 import BH1750
from machine import Pin, I2C

class BH1750Sensor(BaseSensor):
    """
    Adapter pour le capteur de luminosité BH1750.
    Adapte l'API spécifique de la lib BH1750 vers l'interface BaseSensor.
    """

    def __init__(self, name="bh1750", pin=None, scl=22, sda=21, **kwargs):
        super().__init__(name, pin, **kwargs)
        i2c = I2C(0, scl=Pin(scl), sda=Pin(sda))
        self._sensor = BH1750(i2c)

    def _read_raw(self):
        """
        Adapte l'API BH1750 vers le format standard.
        BH1750 utilise luminance(mode) → on uniformise en dict.
        """
        lux = self._sensor.luminance(BH1750.ONCE_HIRES_1)
        return {
            'luminosity': round(lux, 2)
        }

    def _validate(self, data):
        """Validation spécifique au BH1750"""
        lux = data.get('luminosity', None)
        return lux is not None and 0 <= lux <= 65535
```

```python
# sensors/ds18b20_sensor.py

from sensors.base_sensor import BaseSensor
import onewire
import ds18x20
from machine import Pin
import time

class DS18B20Sensor(BaseSensor):
    """
    Adapter pour le capteur de température DS18B20.
    Le DS18B20 utilise le protocole OneWire → adapté vers BaseSensor.
    """

    def __init__(self, name="ds18b20", pin=4, **kwargs):
        super().__init__(name, pin, **kwargs)
        self._ow = onewire.OneWire(Pin(self.pin))
        self._sensor = ds18x20.DS18X20(self._ow)
        self._roms = self._sensor.scan()

    def _read_raw(self):
        """
        Adapte le protocole OneWire vers le format standard.
        DS18B20 nécessite convert_temp() + attente + read_temp().
        """
        self._sensor.convert_temp()
        time.sleep_ms(750)  # Temps de conversion requis

        readings = {}
        for i, rom in enumerate(self._roms):
            temp = self._sensor.read_temp(rom)
            readings[f'temperature_{i}'] = round(temp, 2)

        # Si un seul capteur, simplifier la clé
        if len(readings) == 1:
            return {'temperature': list(readings.values())[0]}
        return readings

    def _validate(self, data):
        """Validation spécifique au DS18B20"""
        for key, value in data.items():
            if value is None or value < -55 or value > 125:
                return False
        return True
```

```python
# sensors/lm393_sensor.py

from sensors.base_sensor import BaseSensor
from machine import Pin, ADC

class LM393Sensor(BaseSensor):
    """
    Adapter pour le capteur d'humidité du sol LM393.
    Le LM393 utilise un ADC analogique → adapté vers BaseSensor.
    """

    def __init__(self, name="lm393", pin=34, **kwargs):
        super().__init__(name, pin, **kwargs)
        self._adc = ADC(Pin(self.pin))
        self._adc.atten(ADC.ATTN_11DB)      # Plage 0-3.3V
        self._adc.width(ADC.WIDTH_12BIT)     # Résolution 12 bits (0-4095)
        self._dry_value = kwargs.get('dry_value', 4095)
        self._wet_value = kwargs.get('wet_value', 0)

    def _read_raw(self):
        """
        Adapte la lecture analogique vers un pourcentage d'humidité.
        LM393 renvoie une valeur brute ADC → convertie en %.
        """
        raw = self._adc.read()
        # Conversion en pourcentage (inversé : 4095=sec, 0=mouillé)
        moisture_pct = ((self._dry_value - raw) /
                        (self._dry_value - self._wet_value)) * 100
        moisture_pct = max(0, min(100, moisture_pct))

        return {
            'soil_moisture': round(moisture_pct, 1),
            'raw_value': raw
        }

    def _validate(self, data):
        """Validation spécifique au LM393"""
        moisture = data.get('soil_moisture', None)
        raw = data.get('raw_value', None)
        return (
            moisture is not None and 0 <= moisture <= 100 and
            raw is not None and 0 <= raw <= 4095
        )
```

### Avantages concrets

- **Uniformité** : toutes les libs tierces exposent la même interface
- **Remplacement facile** : changer de lib sans toucher au code métier
- **Encapsulation** : les détails du protocole (OneWire, I2C, ADC) sont cachés

---

## 8. Retry / Circuit Breaker Pattern

### 🎯 Pourquoi ?

En IoT, les communications **échouent régulièrement** :

- Signal LoRa faible
- WiFi instable
- Capteur déconnecté temporairement

Sans mécanisme de retry, une seule erreur peut faire **planter tout le système**.

### 📖 Comment ça marche ?

```
Tentative 1 → Échec
    │
    ▼ (attente 1s)
Tentative 2 → Échec
    │
    ▼ (attente 2s)
Tentative 3 → Échec
    │
    ▼ (attente 4s)  ← Backoff exponentiel
Tentative 4 → Succès ✓

───────────────────────────────────

Circuit Breaker :

CLOSED (normal)
    │
    ▼ (3 échecs consécutifs)
OPEN (bloqué)
    │
    ▼ (après 30s de pause)
HALF-OPEN (test)
    │
    ├── Succès → CLOSED
    └── Échec  → OPEN
```

### 💻 Implémentation

```python
# utils/retry.py

import time

class RetryHandler:
    """
    Gère les tentatives de retry avec backoff exponentiel.
    Évite de surcharger un service défaillant.
    """

    def __init__(self, max_retries=3, base_delay=1, max_delay=60):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def execute(self, func, *args, **kwargs):
        """
        Exécute une fonction avec retry automatique.

        Args:
            func: Fonction à exécuter
            *args, **kwargs: Arguments de la fonction

        Returns:
            Le résultat de la fonction si succès

        Raises:
            La dernière exception si tous les retries échouent
        """
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 1:
                    print(f"  ✓ Succeeded on attempt {attempt}")
                return result

            except Exception as e:
                last_exception = e
                delay = min(
                    self.base_delay * (2 ** (attempt - 1)),
                    self.max_delay
                )
                print(f"  ✗ Attempt {attempt}/{self.max_retries} "
                      f"failed: {e} → retry in {delay}s")
                time.sleep(delay)

        print(f"  ✗ All {self.max_retries} attempts failed")
        raise last_exception


class CircuitBreaker:
    """
    Circuit Breaker : coupe les appels vers un service défaillant
    pour éviter de gaspiller des ressources.

    États :
    - CLOSED  : fonctionnement normal
    - OPEN    : service bloqué (trop d'erreurs)
    - HALF_OPEN : test de reprise après le timeout
    """

    STATE_CLOSED = "CLOSED"
    STATE_OPEN = "OPEN"
    STATE_HALF_OPEN = "HALF_OPEN"

    def __init__(self, failure_threshold=3, recovery_timeout=30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = self.STATE_CLOSED
        self._failure_count = 0
        self._last_failure_time = 0

    @property
    def state(self):
        """État actuel du circuit breaker"""
        if self._state == self.STATE_OPEN:
            # Vérifier si le timeout est écoulé
            if (time.time() - self._last_failure_time) >= self.recovery_timeout:
                self._state = self.STATE_HALF_OPEN
                print(f"  [CircuitBreaker] → HALF_OPEN (testing)")
        return self._state

    def execute(self, func, *args, **kwargs):
        """Exécute une fonction à travers le circuit breaker"""
        current_state = self.state

        if current_state == self.STATE_OPEN:
            print(f"  [CircuitBreaker] OPEN - call blocked")
            return None

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Appelé lors d'un succès"""
        self._failure_count = 0
        if self._state == self.STATE_HALF_OPEN:
            print(f"  [CircuitBreaker] → CLOSED (recovered)")
        self._state = self.STATE_CLOSED

    def _on_failure(self):
        """Appelé lors d'un échec"""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = self.STATE_OPEN
            print(f"  [CircuitBreaker] → OPEN "
                  f"(after {self._failure_count} failures)")
```

### 🔍 Utilisation

```python
# Avec RetryHandler
retry = RetryHandler(max_retries=3, base_delay=2)
retry.execute(communication.send, sensor_data)

# Avec CircuitBreaker
cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

def send_with_protection(data):
    result = cb.execute(communication.send, data)
    if result is None:
        # Circuit ouvert → stocker localement
        local_storage.save(data)
    return result
```

### Avantages concrets

- **Résilience** : le système survit aux pannes temporaires
- **Backoff exponentiel** : évite de surcharger le réseau
- **Circuit Breaker** : économise l'énergie en arrêtant les tentatives inutiles
- **Stockage local** : les données ne sont pas perdues

---

## 9. Data Transfer Object (DTO) Pattern

### 🎯 Pourquoi ?

Les données circulent entre **plusieurs couches** du système :

- Capteur → SensorManager → EventBus → AlertManager → Communication

Sans format standardisé, chaque module interprète les données différemment → **bugs et incohérences**.

### 📖 Comment ça marche ?

Le DTO définit une **structure de données commune** pour tout le système.

```
Capteur                    DTO                      Communication
┌──────────┐         ┌──────────────┐          ┌──────────────────┐
│ temp=22.5│  ───→   │ SensorData   │   ───→   │ JSON encodé      │
│ hum=65   │         │  sensor_name │          │ prêt à envoyer   │
└──────────┘         │  timestamp   │          └──────────────────┘
                     │  readings[]  │
                     │  is_valid    │
                     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │ AlertManager │
                     │ (même format)│
                     └──────────────┘
```

### 💻 Implémentation

```python
# models/sensor_data.py

import time

class SensorReading:
    """Représente une lecture individuelle d'un capteur"""

    def __init__(self, metric, value, unit=""):
        self.metric = metric      # "temperature", "humidity", etc.
        self.value = value        # 22.5
        self.unit = unit          # "°C", "%", "hPa", "lux"

    def to_dict(self):
        return {
            'metric': self.metric,
            'value': self.value,
            'unit': self.unit
        }


class SensorData:
    """
    DTO pour les données capteurs.
    Format standardisé utilisé dans tout le système.
    """

    def __init__(self, sensor_name, sensor_type):
        self.sensor_name = sensor_name
        self.sensor_type = sensor_type
        self.timestamp = time.time()
        self.readings = []
        self.is_valid = True
        self.error = None

    def add_reading(self, metric, value, unit=""):
        """Ajouter une lecture"""
        self.readings.append(SensorReading(metric, value, unit))

    def get_reading(self, metric):
        """Récupérer une lecture par son nom"""
        for reading in self.readings:
            if reading.metric == metric:
                return reading.value
        return None

    def set_error(self, error_message):
        """Marquer les données comme invalides"""
        self.is_valid = False
        self.error = error_message

    def to_dict(self):
        """Sérialisation pour l'envoi"""
        return {
            'sensor': self.sensor_name,
            'type': self.sensor_type,
            'timestamp': self.timestamp,
            'valid': self.is_valid,
            'readings': [r.to_dict() for r in self.readings],
            'error': self.error
        }

    def to_compact(self):
        """
        Format compact pour les communications limitées (LoRa).
        Réduit la taille du payload.
        """
        data = {'s': self.sensor_name, 't': self.timestamp}
        for reading in self.readings:
            data[reading.metric[:4]] = reading.value  # Clé tronquée
        return data

    def __repr__(self):
        readings_str = ", ".join(
            f"{r.metric}={r.value}{r.unit}" for r in self.readings
        )
        return f"SensorData({self.sensor_name}: {readings_str})"
```

### 🔍 Utilisation

```python
# Dans un capteur (DHT22Sensor._format_data)
def _format_data(self, raw_data):
    dto = SensorData(self.name, "DHT22")
    dto.add_reading("temperature", raw_data['temperature'], "°C")
    dto.add_reading("humidity", raw_data['humidity'], "%")
    return dto

# Dans AlertManager
def on_sensor_data(self, dto: SensorData):
    temp = dto.get_reading("temperature")
    if temp and temp > 40:
        self.trigger_alert(dto.sensor_name, "temperature", temp)

# Pour l'envoi via LoRa (compact)
payload = dto.to_compact()
# → {'s': 'dht22', 't': 1738850000, 'temp': 22.5, 'humi': 65}

# Pour l'envoi via WiFi (complet)
payload = dto.to_dict()
# → {'sensor': 'dht22', 'type': 'DHT22', 'timestamp': ..., 'readings': [...]}
```

### Avantages concrets

- **Format unique** dans tout le système
- **Double sérialisation** : compact (LoRa) ou complet (WiFi)
- **Validation intégrée** avec le flag `is_valid`
- **Pas de bugs** liés à des clés manquantes ou mal nommées

---

## 10. Façade Pattern

### 🎯 Pourquoi ?

Le `main.py` ne devrait pas connaître les détails internes du système. Le **DeviceManager** agit comme une **façade** qui simplifie l'interface.

### 📖 Comment ça marche ?

```
                Sans Façade                          Avec Façade
           ┌──────────────────┐              ┌──────────────────┐
           │     main.py      │              │     main.py      │
           └───┬──┬──┬──┬──┬─┘              └────────┬─────────┘
               │  │  │  │  │                         │
               ▼  ▼  ▼  ▼  ▼                         ▼
            Config                           ┌──────────────────┐
            SensorFactory                    │  DeviceManager   │
            LoRaProtocol                     │    (Façade)      │
            AlertManager                     │                  │
            EventBus                         │  initialize()    │
            PowerManager                     │  run()           │
                                             └──────────────────┘
   → main.py connaît tout                   → main.py ne connaît
   → couplage maximum                         qu'une seule classe
```

### 💻 Implémentation

```python
# core/device_manager.py

import gc
import time
from config.config_manager import ConfigManager
from sensors.sensor_factory import SensorFactory
from sensors.dht22_sensor import DHT22Sensor
from sensors.bmp280_sensor import BMP280Sensor
from sensors.bh1750_sensor import BH1750Sensor
from sensors.ds18b20_sensor import DS18B20Sensor
from sensors.lm393_sensor import LM393Sensor
from communication.lora_protocol import LoRaProtocol
from communication.wifi_protocol import WiFiProtocol
from communication.communication_manager import CommunicationManager
from managers.event_bus import EventBus
from managers.alert_manager import AlertManager
from core.states import BootState

class DeviceManager:
    """
    Façade principale du système IoT.
    Simplifie l'interface pour main.py.
    Combine aussi le Singleton Pattern.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.config = ConfigManager()
        self.event_bus = EventBus()
        self.sensors = []
        self.communication = None
        self.alert_manager = None
        self._state = BootState()
        self._running = False
        self._initialized = True

    def initialize(self):
        """
        Initialise tout le système.
        L'appelant n'a pas besoin de connaître les détails.
        """
        print("=" * 40)
        print("  IoT Device Starting...")
        print("=" * 40)

        # 1. Enregistrer les capteurs disponibles
        self._register_sensors()

        # 2. Créer les capteurs depuis la config
        print("\n[Sensors]")
        self.sensors = SensorFactory.create_from_config(
            self.config.get_config()
        )

        # 3. Initialiser la communication
        print("\n[Communication]")
        self._init_communication()

        # 4. Initialiser les alertes
        print("\n[Alerts]")
        self.alert_manager = AlertManager(self.config.get_config())
        self.event_bus.subscribe("sensor.data", self.alert_manager.on_sensor_data)

        # 5. Libérer la mémoire
        gc.collect()

        print(f"\n✓ Device ready with {len(self.sensors)} sensors")
        print("=" * 40)

    def run(self):
        """
        Boucle principale.
        Délègue au State Pattern pour le comportement.
        """
        self._running = True
        print("\nDevice running...\n")

        while self._running:
            try:
                self._state.handle(self)
            except KeyboardInterrupt:
                print("\nStopping device...")
                self._running = False
            except Exception as e:
                print(f"Critical error: {e}")
                time.sleep(5)

    def stop(self):
        """Arrêter le device proprement"""
        self._running = False
        if self.communication:
            self.communication.disconnect()
        print("Device stopped.")

    def set_state(self, new_state):
        """Changer l'état du device (utilisé par State Pattern)"""
        self._state.exit(self)
        self._state = new_state
        self._state.enter(self)

    # ═══════════════════════════════════════
    # Méthodes internes (cachées par la façade)
    # ═══════════════════════════════════════

    def _register_sensors(self):
        """Enregistre tous les types de capteurs disponibles"""
        SensorFactory.register("dht22", DHT22Sensor)
        SensorFactory.register("bmp280", BMP280Sensor)
        SensorFactory.register("bh1750", BH1750Sensor)
        SensorFactory.register("ds18b20", DS18B20Sensor)
        SensorFactory.register("lm393", LM393Sensor)

    def _init_communication(self):
        """Initialise le protocole de communication"""
        comm_config = self.config.get('communication', default={})
        comm_type = comm_config.get('type', 'lora')

        if comm_type == 'lora':
            protocol = LoRaProtocol(comm_config.get('lora', {}))
        else:
            protocol = WiFiProtocol(comm_config.get('wifi', {}))

        self.communication = CommunicationManager(strategy=protocol)
        print(f"  ✓ Communication: {comm_type}")
```

```python
# main.py - Simple grâce à la Façade

from core.device_manager import DeviceManager

def main():
    device = DeviceManager()    # Singleton
    device.initialize()          # Tout est initialisé en interne
    device.run()                 # Boucle principale

if __name__ == '__main__':
    main()
```

### Avantages concrets

- **main.py** fait **3 lignes** de code
- **Aucune connaissance** des sous-systèmes requise
- **Modification interne** sans impacter le point d'entrée
- **Tests simplifiés** : on teste la façade, pas les détails

---

## Résumé des patterns et leur localisation

| #   | Pattern                     | Fichier                                              | Rôle                                     |
| --- | --------------------------- | ---------------------------------------------------- | ---------------------------------------- |
| 1   | **Singleton**               | `config/config_manager.py`, `core/device_manager.py` | Instance unique des ressources partagées |
| 2   | **Factory**                 | `sensors/sensor_factory.py`                          | Création dynamique de capteurs           |
| 3   | **Strategy**                | `communication/base_protocol.py`                     | Protocoles interchangeables              |
| 4   | **Observer**                | `managers/event_bus.py`                              | Notifications découplées                 |
| 5   | **State**                   | `core/states.py`                                     | Gestion des états du device              |
| 6   | **Template Method**         | `sensors/base_sensor.py`                             | Algorithme de lecture standardisé        |
| 7   | **Adapter**                 | `sensors/*_sensor.py`                                | Uniformisation des libs tierces          |
| 8   | **Retry / Circuit Breaker** | `utils/retry.py`                                     | Résilience aux pannes                    |
| 9   | **DTO**                     | `models/sensor_data.py`                              | Format de données standardisé            |
| 10  | **Façade**                  | `core/device_manager.py`                             | Interface simplifiée                     |

---

## Structure du projet

```
project_root/
│
├── 📄 boot.py                       # Initialisation MicroPython
├── 📄 main.py                       # Point d'entrée → DeviceManager
│
├── 📁 config/
│   ├── config.json                  # Configuration (capteurs, seuils, comm)
│   ├── pins.py                      # Mapping des pins
│   └── config_manager.py            # 🔷 Singleton
│
├── 📁 core/
│   ├── device_manager.py            # 🔷 Singleton + Façade
│   ├── states.py                    # 🔷 State Pattern
│   └── power_manager.py             # Gestion énergie / deep sleep
│
├── 📁 sensors/
│   ├── base_sensor.py               # 🔷 Template Method
│   ├── sensor_factory.py            # 🔷 Factory Pattern
│   ├── dht22_sensor.py              # 🔷 Adapter
│   ├── bmp280_sensor.py             # 🔷 Adapter
│   ├── bh1750_sensor.py             # 🔷 Adapter
│   ├── ds18b20_sensor.py            # 🔷 Adapter
│   └── lm393_sensor.py              # 🔷 Adapter
│
├── 📁 communication/
│   ├── base_protocol.py             # 🔷 Strategy Pattern (interface)
│   ├── lora_protocol.py             # Stratégie LoRa
│   ├── wifi_protocol.py             # Stratégie WiFi
│   └── communication_manager.py     # Gestionnaire + fallback
│
├── 📁 managers/
│   ├── event_bus.py                 # 🔷 Observer Pattern
│   ├── sensor_manager.py            # Gestion des capteurs
│   ├── alert_manager.py             # Observer → alertes
│   └── pairing_manager.py           # Gestion du pairing
│
├── 📁 models/
│   └── sensor_data.py               # 🔷 DTO Pattern
│
├── 📁 lib/                          # Bibliothèques tierces
│   ├── bh1750.py
│   ├── bmp280.py
│   ├── ds3231.py
│   ├── Lora.py
│   └── ulora.py
│
└── 📁 utils/
    ├── retry.py                     # 🔷 Retry + Circuit Breaker
    ├── logger.py                    # Système de logs léger
    └── time_helper.py               # Utilitaires temps
```

---

## Diagramme de flux complet

```
                              ┌──────────┐
                              │  boot.py │
                              └────┬─────┘
                                   │
                                   ▼
                              ┌──────────┐
                              │ main.py  │
                              └────┬─────┘
                                   │
                          ┌────────▼────────┐
                          │ DeviceManager   │ ← Façade + Singleton
                          │ (initialize)    │
                          └───┬────┬────┬───┘
                              │    │    │
              ┌───────────────┘    │    └───────────────┐
              ▼                    ▼                    ▼
     ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
     │ SensorFactory  │  │   EventBus     │  │  CommManager   │
     │   (Factory)    │  │  (Observer)    │  │  (Strategy)    │
     └───────┬────────┘  └───────┬────────┘  └───────┬────────┘
             │                   │                   │
     ┌───────┼───────┐   ┌──────┼──────┐    ┌───────┼───────┐
     ▼       ▼       ▼   ▼      ▼      ▼    ▼               ▼
  DHT22  BMP280  BH1750  Alert Logger  ...  LoRa           WiFi
  (Template Method)       Manager           Protocol       Protocol
  (Adapter)               (Observer)        (Strategy)     (Strategy)
     │                                         │
     ▼                                         ▼
  SensorData (DTO)                    RetryHandler
                                      CircuitBreaker
```

---

## Bonnes pratiques IoT

### 🔋 Gestion de l'énergie

| Pratique                   | Description                                                          |
| -------------------------- | -------------------------------------------------------------------- |
| **Deep Sleep**             | Mettre le microcontrôleur en veille entre les lectures               |
| **Duty Cycling**           | Alterner périodes actives et inactives                               |
| **Lecture conditionnelle** | Ne lire que si le délai minimum est écoulé (cache dans `BaseSensor`) |

### 🛡️ Fiabilité

| Pratique                   | Description                                                        |
| -------------------------- | ------------------------------------------------------------------ |
| **Watchdog Timer**         | Redémarrage automatique si le code est bloqué                      |
| **Retry Logic**            | Réessayer N fois avant d'abandonner (dans `ErrorState`)            |
| **Fallback Communication** | Si LoRa échoue → WiFi (dans `CommunicationManager`)                |
| **Error Counter**          | Désactiver un capteur défaillant (`_max_errors` dans `BaseSensor`) |

### 💾 Mémoire

| Pratique               | Description                                              |
| ---------------------- | -------------------------------------------------------- |
| **gc.collect()**       | Forcer le garbage collector régulièrement                |
| **Éviter les strings** | Utiliser des constantes numériques pour les événements   |
| **Streaming JSON**     | Encoder les données au fil de l'eau plutôt qu'en mémoire |

### 🔐 Sécurité

| Pratique                   | Description                                           |
| -------------------------- | ----------------------------------------------------- |
| **Config externe**         | Ne pas hardcoder les mots de passe dans le code       |
| **Validation des entrées** | Toujours valider les données capteurs (`_validate()`) |
| **Chiffrement LoRa**       | Utiliser AES pour les transmissions sensibles         |

---

## Glossaire

| Terme               | Définition                                                   |
| ------------------- | ------------------------------------------------------------ |
| **Singleton**       | Pattern qui garantit une instance unique d'une classe        |
| **Factory**         | Pattern qui centralise la création d'objets                  |
| **Strategy**        | Pattern qui permet de changer d'algorithme à chaud           |
| **Observer**        | Pattern qui notifie automatiquement les modules intéressés   |
| **State**           | Pattern qui encapsule le comportement selon l'état           |
| **Template Method** | Pattern qui définit le squelette d'un algorithme             |
| **Adapter**         | Pattern qui uniformise des interfaces différentes            |
| **Retry**           | Mécanisme de réessai automatique après un échec              |
| **Circuit Breaker** | Mécanisme qui coupe les appels vers un service défaillant    |
| **DTO**             | Objet de transfert de données entre les couches du système   |
| **Façade**          | Pattern qui simplifie l'interface d'un sous-système complexe |
| **Deep Sleep**      | Mode de veille profonde du microcontrôleur                   |
| **I2C**             | Protocole de communication série pour les capteurs           |
| **LoRa**            | Protocole radio longue portée, basse consommation            |
| **MQTT**            | Protocole de messagerie léger pour l'IoT                     |
