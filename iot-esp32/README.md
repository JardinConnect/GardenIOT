# 🏡 IoT ESP32 Device - Guide Utilisateur

Bienvenue dans le système IoT ESP32 ! Ce guide vous explique comment utiliser le device IoT avec toutes ses fonctionnalités.

## 📋 Table des Matières

- [Installation et Configuration](#-installation-et-configuration)
- [Utilisation de Base](#-utilisation-de-base)
- [Modes de Fonctionnement](#-modes-de-fonctionnement)
- [Configuration des Capteurs](#-configuration-des-capteurs)
- [Communication LoRa](#-communication-lora)
- [Gestion des Alertes](#-gestion-des-alertes)
- [Commandes à Distance](#-commandes-à-distance)
- [Dépannage](#-dépannage)
- [Exemples Avancés](#-exemples-avancés)

## 🛠️ Installation et Configuration

### Prérequis

- ESP32 avec MicroPython
- Capteurs compatibles (DHT22, BH1750, DS18B20, LM393)
- Module LoRa (SX1276/78/79)
- Alimentation stable

### Installation

1. **Télécharger le code** : Clonez ce dépôt sur votre machine
2. **Configurer l'ESP32** : Flashez MicroPython sur votre ESP32
3. **Copier les fichiers** : Transférez tous les fichiers dans `src/` vers votre ESP32
4. **Configurer** : Modifiez `config/config.json` selon vos besoins

### Configuration de Base

Éditez `config/config.json` :

```json
{
  "device": {
    "uid": "ESP32-001",        // Identifiant unique du device
    "send_interval": 60,        // Intervalle d'envoi en secondes
    "listen_timeout": 5000      // Timeout d'écoute en ms
  },
  "lora": {
    "frequency": 433.1,         // Fréquence LoRa
    "spreading_factor": 10,     // Facteur d'étalement
    "tx_power": 14             // Puissance de transmission
  },
  "sensors": [
    {
      "type": "dht22",
      "name": "air",
      "enabled": true,
      "pin": 27
    }
  ]
}
```

## 🚀 Utilisation de Base

### Lancement Normal

```python
from core.device_manager import DeviceManager

# Créer le device
device = DeviceManager()

# Initialiser tous les composants
device.initialize()

# Lancer le système (machine à états)
device.run()
```

### Lancement en Mode Test

```python
from core.device_manager import DeviceManager

device = DeviceManager()
device.initialize()

# Exécuter des cycles manuels (pour le débogage)
while True:
    device.run_cycle()
```

## 🎛️ Modes de Fonctionnement

### 1. Mode Boot (Démarrage)
- Initialise tous les composants
- Vérifie la configuration
- Passe automatiquement au mode suivant

### 2. Mode Pairing (Appairage)
- **Activé quand** : Aucun parent_id n'est configuré
- **Comment activer** : Appuyez sur le bouton de pairing
- **Processus** :
  1. Envoie un message PAIR avec l'UID
  2. Attend un PAIR_ACK de la gateway
  3. Sauvegarde le parent_id
  4. Passe en mode actif

### 3. Mode Actif (Opération Normal)
- **Fonctionnement** :
  1. Lit tous les capteurs
  2. Vérifie les alertes
  3. Envoie les données via LoRa
  4. Écoute les commandes
  5. Passe en mode sleep

### 4. Mode Sleep (Économie d'Énergie)
- **Durée** : Configurable via `send_interval`
- **Consommation** : Minimale
- **Réveil** : Automatique pour le prochain cycle

### 5. Mode Erreur (Récupération)
- **Activé quand** : Erreur critique détectée
- **Comportement** :
  - 3 tentatives de récupération
  - Reboot automatique si nécessaire
  - Notifications d'erreur

## 🔧 Configuration des Capteurs

### Capteurs Supportés

| Type | Description | Broches |
|------|-------------|---------|
| DHT22 | Température & Humidité | 1x GPIO |
| BH1750 | Luminosité | I2C (SDA, SCL) |
| DS18B20 | Température | 1x GPIO |
| LM393 | Humidité du sol | 1x ADC |

### Ajouter un Capteur

1. **Éditer la configuration** :

```json
"sensors": [
  {
    "type": "dht22",
    "name": "air",
    "enabled": true,
    "pin": 27,
    "alerts": {
      "temperature": {"min": 0, "max": 45},
      "humidity": {"min": 20, "max": 90}
    }
  }
]
```

2. **Redémarrer le device**

### Configurer les Alertes

```json
"alerts": {
  "temperature": {
    "min": 0,    // Alerte si < 0°C
    "max": 45    // Alerte si > 45°C
  },
  "humidity": {
    "min": 20,   // Alerte si < 20%
    "max": 90    // Alerte si > 90%
  }
}
```

## 📡 Communication LoRa

### Configuration

```json
"lora": {
  "frequency": 433.1,       // 433MHz, 868MHz, ou 915MHz
  "spreading_factor": 10,   // 7-12 (plus haut = plus loin)
  "bandwidth": 500000,      // 7.8kHz - 500kHz
  "coding_rate": 5,          // 5-8 (plus haut = plus robuste)
  "tx_power": 14,           // 2-20 dBm
  "sync_word": "0x12"       // Mot de synchronisation
}
```

### Messages LoRa

| Type | Description | Format |
|------|-------------|--------|
| D | Données | `D:temp:25.5,hum:65` |
| U | Unpair | `U:ESP32-001` |
| A | Config Alerte | `A:temp_min:0,temp_max:50` |
| C | Commande | `C:REBOOT` |

### Fallback Automatique

Si LoRa échoue, le système peut basculer sur WiFi (si configuré) :

```json
"communication": {
  "type": "lora",
  "fallback_enabled": true,
  "fallback_type": "wifi"
}
```

## 🚨 Gestion des Alertes

### Types d'Alerte

1. **Seuil dépassé** : Valeur au-dessus/au-dessous du seuil
2. **Erreur de capteur** : Lecture échouée
3. **Erreur de communication** : Échec d'envoi

### Comportement

- **Notification** : Message LoRa envoyé
- **Journalisation** : Événement enregistré
- **Action** : Selon la configuration

### Exemple de Configuration

```json
"sensors": [
  {
    "type": "dht22",
    "name": "air",
    "alerts": {
      "temperature": {
        "min": 0,
        "max": 45,
        "action": "NOTIFY"
      }
    }
  }
]
```

## 📟 Commandes à Distance

### Commandes Supportées

| Commande | Description | Exemple |
|----------|-------------|---------|
| REBOOT | Redémarre le device | `C:REBOOT` |
| RESET_CONFIG | Réinitialise la configuration | `C:RESET_CONFIG` |
| SET_INTERVAL | Change l'intervalle | `C:SET_INTERVAL:30` |
| GET_STATS | Récupère les statistiques | `C:GET_STATS` |

### Envoyer une Commande

```python
message = {
    'type': 'C',
    'command': 'REBOOT',
    'params': {}
}
device.communication.send(message)
```

##  Dépannage

### Problèmes Courants

| Problème | Solution |
|----------|----------|
| Device ne démarre pas | Vérifier l'alimentation et les connexions |
| Pas de données capteurs | Vérifier le câblage et les broches |
| Échec LoRa | Vérifier la fréquence et l'antenne |
| Erreurs de configuration | Vérifier le fichier config.json |
| Device ne répond pas | Redémarrer manuellement |

### Journalisation

Les messages sont affichés sur la console série :

```
[14:30:15] Device initialized
[14:30:15] Entering BOOT state
[14:30:16] Entering ACTIVE state
[14:30:16] Reading sensors...
[14:30:17] Data sent: T:25.5,H:65.0
```

### Récupération d'Urgence

1. **Bouton reset** : Appuyez pour redémarrer
2. **Effacer config** : Supprimez `config/config.json`
3. **Mode safe** : Maintenez le bouton au démarrage

## 💡 Exemples Avancés

### 1. Configuration Multi-Capteurs

```json
"sensors": [
  {
    "type": "dht22",
    "name": "air",
    "pin": 27,
    "alerts": {"temperature": {"min": 0, "max": 45}}
  },
  {
    "type": "bh1750",
    "name": "light",
    "bus": "i2c"
  },
  {
    "type": "ds18b20",
    "name": "soil_temp",
    "pin": 4
  }
]
```

### 2. Configuration LoRa Longue Distance

```json
"lora": {
  "frequency": 868.0,
  "spreading_factor": 12,
  "bandwidth": 125000,
  "coding_rate": 8,
  "tx_power": 20
}
```

### 3. Mode Économie d'Énergie

```json
"power": {
  "sleep_interval": 300,  // 5 minutes
  "deep_sleep": true     // Utilise le deep sleep
}
```

### 4. Configuration Complète

```json
{
  "device": {
    "uid": "ESP32-GREENHOUSE",
    "send_interval": 300,
    "listen_timeout": 10000
  },
  "lora": {
    "frequency": 868.0,
    "spreading_factor": 10,
    "tx_power": 14
  },
  "sensors": [
    {
      "type": "dht22",
      "name": "air",
      "pin": 27,
      "alerts": {
        "temperature": {"min": 5, "max": 40},
        "humidity": {"min": 30, "max": 80}
      }
    },
    {
      "type": "lm393",
      "name": "soil_moisture",
      "pin": 35,
      "params": {"dry_value": 3500, "wet_value": 900},
      "alerts": {"soil_moisture": {"min": 20}}
    }
  ],
  "communication": {
    "fallback_enabled": true
  }
}
```

## 📚 Référence Technique

### Classes Principales

- **DeviceManager** : Façade principale
- **SensorManager** : Gestion des capteurs
- **CommunicationManager** : Gestion LoRa/WiFi
- **AlertManager** : Gestion des alertes
- **StateManager** : Machine à états

### Patterns Utilisés

1. **Façade** : DeviceManager
2. **Singleton** : ConfigManager
3. **Factory** : SensorFactory
4. **Strategy** : Communication protocols
5. **Observer** : EventBus
6. **State** : StateManager
7. **Template Method** : BaseSensor
8. **Adapter** : Capteurs individuels
9. **DTO** : SensorData
10. **Retry/Circuit Breaker** : Communication

## 🎯 Bonnes Pratiques

1. **Sauvegardez votre configuration** avant les mises à jour
2. **Testez les capteurs individuellement** avant l'intégration
3. **Surveillez la consommation** pour optimiser la batterie
4. **Mettez à jour régulièrement** le firmware
5. **Documentez vos modifications** pour la maintenance

## 🔧 Maintenance

### Mise à Jour

1. Arrêtez le device
2. Copiez les nouveaux fichiers
3. Redémarrez

### Sauvegarde

```bash
# Sauvegarder la configuration
cp config/config.json config/config_backup.json

# Sauvegarder les logs
# (selon votre système de logging)
```

### Restauration

```bash
# Restaurer la configuration
cp config/config_backup.json config/config.json

# Redémarrer
reset
```

## 📞 Support

Pour toute question ou problème :

- Consultez la documentation technique
- Vérifiez les exemples fournis
- Examinez les logs pour les erreurs
- Contactez l'équipe de support si nécessaire

---

**Version** : 1.0
**Dernière mise à jour** : 2024
**Licence** : MIT
