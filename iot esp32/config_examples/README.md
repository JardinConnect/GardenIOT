# 📁 Exemples de Configuration

Ce dossier contient des exemples de fichiers de configuration pour différentes utilisations du système IoT ESP32.

## 📋 Fichiers Disponibles

### 1. **advanced_config.json**
Configuration avancée pour une ferme intelligente avec :
- 4 capteurs (DHT22, BH1750, DS18B20, LM393)
- Configuration LoRa optimisée pour la longue distance
- Gestion avancée des alertes avec hystérésis
- Fallback automatique sur WiFi
- Paramètres de puissance optimisés

**Cas d'utilisation** : Agriculture intelligente, serre connectée, monitoring environnemental

### 2. **basic_config.json** (dans config/)
Configuration de base avec :
- 1 capteur DHT22
- Configuration LoRa standard
- Paramètres par défaut

**Cas d'utilisation** : Démarrage rapide, tests initiaux

## 🚀 Comment Utiliser

1. **Copier un exemple** :
   ```bash
   cp config_examples/advanced_config.json config/config.json
   ```

2. **Modifier selon vos besoins** :
   ```bash
   nano config/config.json
   ```

3. **Redémarrer le device**

## 📝 Structure de Configuration

### Sections Principales

```json
{
  "device": { ... },        // Paramètres du device
  "lora": { ... },          // Configuration LoRa
  "communication": { ... },  // Stratégies de communication
  "sensors": [ ... ],       // Liste des capteurs
  "pairing": { ... },       // Paramètres d'appairage
  "alerts": { ... },        // Configuration des alertes
  "power": { ... }          // Gestion de l'alimentation
}
```

### Paramètres Device

| Paramètre | Description | Valeurs Typiques |
|-----------|-------------|------------------|
| uid | Identifiant unique | "ESP32-001" |
| send_interval | Intervalle d'envoi (s) | 60-300 |
| listen_timeout | Timeout écoute (ms) | 5000-10000 |
| debug_mode | Mode débogage | true/false |
| deep_sleep_enabled | Deep sleep activé | true/false |

### Paramètres LoRa

| Paramètre | Description | Valeurs Typiques |
|-----------|-------------|------------------|
| frequency | Fréquence (MHz) | 433.1, 868.0, 915.0 |
| spreading_factor | Facteur d'étalement | 7-12 |
| bandwidth | Bande passante (Hz) | 7800-500000 |
| tx_power | Puissance (dBm) | 2-20 |
| coding_rate | Taux de codage | 5-8 |

### Configuration Capteur

```json
{
  "type": "dht22",          // Type de capteur
  "name": "air",            // Nom unique
  "enabled": true,           // Activé/désactivé
  "pin": 27,                // Broche GPIO
  "alerts": { ... },         // Alertes
  "codes": { ... }           // Codes de transmission
}
```

## 💡 Conseils

1. **Commencez simple** : Utilisez `basic_config.json` pour les tests initiaux
2. **Activez un capteur à la fois** : Pour le débogage
3. **Ajustez les intervalles** : Selon vos besoins de batterie
4. **Testez la portée LoRa** : Ajustez spreading_factor et tx_power
5. **Sauvegardez vos configs** : Avant les mises à jour

## 📚 Documentation Complète

Voir le [Guide Utilisateur](../README.md) pour plus de détails sur chaque paramètre.

---

**Dernière mise à jour** : 2024
**Licence** : MIT
