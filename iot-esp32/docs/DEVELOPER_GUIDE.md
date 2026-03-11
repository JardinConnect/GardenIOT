# 👨‍💻 Guide du Développeur - IoT ESP32

Bienvenue dans le guide du développeur pour le système IoT ESP32. Ce guide vous explique comment étendre, modifier et contribuer au projet.

## 📋 Table des Matières

- [Structure du Projet](#-structure-du-projet)
- [Architecture Logicielle](#-architecture-logicielle)
- [Ajouter un Nouveau Capteur](#-ajouter-un-nouveau-capteur)
- [Ajouter un Protocole de Communication](#-ajouter-un-protocole-de-communication)
- [Créer un Nouveau État](#-créer-un-nouveau-état)
- [Étendre le DTO](#-étendre-le-dto)
- [Bonnes Pratiques de Développement](#-bonnes-pratiques-de-développement)
- [Tests et Validation](#-tests-et-validation)
- [Débogage](#-débogage)
- [Contribution](#-contribution)

## 🗂️ Structure du Projet

```
src/
├── config/              # Configuration
├── core/                # Noyau du système
│   ├── device_manager.py # Façade principale
│   ├── state_manager.py  # Gestion des états
│   ├── event_bus.py      # Bus d'événements
│   └── states.py         # États du device
├── sensors/             # Capteurs
│   ├── base_sensor.py    # Classe de base
│   ├── sensor_factory.py # Factory
│   └── *sensor.py        # Capteurs spécifiques
├── communication/       # Protocoles
│   ├── base_protocol.py  # Interface
│   └── *protocol.py      # Implémentations
├── managers/            # Gestionnaires
│   └── alert_manager.py  # Alertes
├── models/              # Modèles de données
│   └── sensor_data.py    # DTO
└── lib/                 # Bibliothèques tierces
```

## 🏗️ Architecture Logicielle

### Design Patterns Utilisés

| Pattern | Implémentation | Fichier |
|---------|---------------|---------|
| **Façade** | Interface unifiée | `device_manager.py` |
| **Singleton** | Configuration unique | `config_manager.py` |
| **Factory** | Création de capteurs | `sensor_factory.py` |
| **Strategy** | Protocoles interchangeables | `communication/*` |
| **Observer** | Notifications | `event_bus.py` |
| **State** | Machine à états | `state_manager.py` |
| **Template Method** | Lecture standardisée | `base_sensor.py` |
| **Adapter** | Uniformisation | `sensors/*_sensor.py` |
| **DTO** | Données standardisées | `sensor_data.py` |

### Flux de Données

```
main.py → DeviceManager → [EventBus, SensorManager, CommunicationManager, AlertManager]
```

## 🔧 Ajouter un Nouveau Capteur

### Étapes

1. **Créer la classe du capteur** :

```python
# src/sensors/mon_nouveau_sensor.py
from sensors.base_sensor import BaseSensor

class MonNouveauSensor(BaseSensor):
    def __init__(self, name="mon_sensor", pin=None, **kwargs):
        super().__init__(name, pin, **kwargs)
        # Initialisation spécifique
        
    def _read_raw(self):
        """Lire les données brutes du capteur."""
        # Implémentation spécifique
        return {
            'metric1': valeur1,
            'metric2': valeur2
        }
    
    def _validate(self, data):
        """Valider les données lues."""
        # Logique de validation
        return data is not None and valeur_dans_plage
```

2. **Enregistrer dans la factory** :

```python
# Dans src/sensors/sensor_factory.py
from sensors.mon_nouveau_sensor import MonNouveauSensor

# Ajouter dans la méthode _register_sensor_types()
SensorFactory.register("mon_nouveau", MonNouveauSensor)
```

3. **Configurer le capteur** :

```json
// Dans config/config.json
"sensors": [
  {
    "type": "mon_nouveau",
    "name": "mon_capteur",
    "enabled": true,
    "pin": 15,
    "params": {
      "param1": "valeur1"
    }
  }
]
```

4. **Redémarrer le device**

### Exemple Complet

Voir les capteurs existants (`dht22_sensor.py`, `bh1750_sensor.py`) pour des exemples complets.

## 📡 Ajouter un Protocole de Communication

### Étapes

1. **Créer la classe du protocole** :

```python
# src/communication/mon_protocole.py
from communication.base_protocol import CommunicationProtocol

class MonProtocole(CommunicationProtocol):
    def __init__(self, config):
        super().__init__("MonProtocole")
        # Initialisation spécifique
        
    def connect(self):
        """Établir la connexion."""
        # Implémentation spécifique
        self._connected = True
    
    def disconnect(self):
        """Fermer la connexion."""
        self._connected = False
    
    def send(self, data):
        """Envoyer des données."""
        # Implémentation spécifique
        return True
    
    def receive(self, timeout_ms=None):
        """Recevoir des données."""
        # Implémentation spécifique
        return None
```

2. **Modifier le CommunicationManager** :

```python
# Dans src/core/device_manager.py
elif comm_type == 'mon_protocole':
    protocol = MonProtocole(self.config.get('mon_protocole', {}))
```

3. **Configurer le protocole** :

```json
// Dans config/config.json
"communication": {
  "type": "mon_protocole",
  "params": {
    "param1": "valeur1"
  }
}
```

## ⚙️ Créer un Nouveau État

### Étapes

1. **Créer la classe d'état** :

```python
# src/core/states.py

class MonNouvelEtat(DeviceState):
    """Description de l'état."""
    
    name = "MON_ETAT"
    
    def handle(self, context):
        """Logique de l'état."""
        print(f"[MonNouvelEtat] Exécution...")
        
        # Logique spécifique
        # ...
        
        # Transition vers un autre état
        context.state_manager.set_state(AutreEtat())
```

2. **Utiliser l'état** :

```python
# Dans n'importe quel état existant
from core.states import MonNouvelEtat
context.state_manager.set_state(MonNouvelEtat())
```

### Exemple

Voir les états existants (`BootState`, `ActiveState`, etc.) pour des exemples complets.

## 📦 Étendre le DTO

### Ajouter un Nouveau Champ

1. **Modifier SensorData** :

```python
# src/models/sensor_data.py

class SensorData:
    def __init__(self, sensor_name, sensor_type):
        # ... champs existants
        self.custom_field = None  # Nouveau champ
    
    def set_custom_field(self, value):
        self.custom_field = value
    
    def to_dict(self):
        data = {
            # ... champs existants
            'custom_field': self.custom_field
        }
        return data
```

2. **Utiliser le nouveau champ** :

```python
# Dans un capteur
dto = SensorData("sensor", "Type")
dto.add_reading("metric", 25.5)
dto.set_custom_field("custom_value")
```

## 👍 Bonnes Pratiques de Développement

### 1. Respecter les Patterns

- Utilisez les patterns existants
- Ne réinventez pas la roue
- Documentez les nouveaux patterns

### 2. Gestion des Erreurs

```python
try:
    # Code risqué
    result = operation_risquee()
except Exception as e:
    print(f"[ERROR] {self.__class__.__name__}: {e}")
    # Gestion de l'erreur
    return None
```

### 3. Logging

```python
import time

def log(message):
    timestamp = time.strftime("%H:%M:%S", time.localtime())
    print(f"[{timestamp}] [{self.__class__.__name__}] {message}")
```

### 4. Configuration

- Utilisez toujours `config_manager.py`
- Ne hardcodez pas les valeurs
- Documentez les nouvelles options

### 5. Tests

- Testez chaque composant individuellement
- Utilisez des mocks pour le matériel
- Validez les cas limites

## 🧪 Tests et Validation

### Exécuter les Tests

```bash
# Tests unitaires
python test_dto_simple.py
python test_facade.py

# Tests d'intégration
# (sur matériel réel)
```

### Créer un Nouveau Test

```python
# test_mon_composant.py
def test_mon_composant():
    print("Testing mon composant...")
    
    try:
        # Initialisation
        from core.mon_composant import MonComposant
        composant = MonComposant()
        
        # Test fonctionnalité 1
        result = composant.fonction1()
        assert result == expected, f"Expected {expected}, got {result}"
        
        print("  [OK] All tests passed")
        return True
        
    except Exception as e:
        print(f"  [ERROR] Test failed: {e}")
        return False
```

### Bonnes Pratiques de Test

1. **Isolation** : Testez un composant à la fois
2. **Mocking** : Utilisez des mocks pour les dépendances
3. **Couverture** : Testez les cas normaux et limites
4. **Documentation** : Documentez les tests

## 🐛 Débogage

### Outils

- **Console série** : `screen /dev/ttyUSB0 115200`
- **Logs** : Activez le logging détaillé
- **Tests unitaires** : Isolez le problème

### Techniques

1. **Diviser pour régner** : Isolez le composant problématique
2. **Logs détaillés** : Ajoutez des logs temporaires
3. **Vérification des dépendances** : Vérifiez chaque dépendance
4. **Test unitaire** : Créez un test minimal

### Problèmes Courants

| Problème | Solution |
|----------|----------|
| Module manquant | Vérifiez les imports et le chemin
| Erreur de configuration | Vérifiez config.json
| Capteur non détecté | Vérifiez le câblage et les broches
| Échec LoRa | Vérifiez la fréquence et l'antenne

## 🤝 Contribution

### Processus

1. **Fork** : Forkez le dépôt
2. **Branch** : Créez une branche pour votre fonctionnalité
3. **Commit** : Commitez vos changements
4. **Push** : Poussez votre branche
5. **Pull Request** : Ouvrez une PR

### Règles

1. **Respectez le style** : Suivez le style existant
2. **Documentez** : Ajoutez de la documentation
3. **Testez** : Ajoutez des tests
4. **Commits atomiques** : Un commit = une fonctionnalité
5. **Messages clairs** : Décrivez vos changements

### Template de Commit

```
feat: ajouter le capteur XYZ

- Implémentation du capteur XYZ
- Ajout des tests unitaires
- Mise à jour de la documentation

Fixes #123
```

## 📚 Ressources

- **Documentation technique** : `docs/design_pattern.md`
- **Exemples** : Voir les composants existants
- **API MicroPython** : https://docs.micropython.org/
- **Design Patterns** : https://refactoring.guru/design-patterns

## 🎯 Checklist de Développement

- [ ] Respect des design patterns existants
- [ ] Documentation complète
- [ ] Tests unitaires ajoutés
- [ ] Configuration documentée
- [ ] Code commenté
- [ ] Validation des entrées
- [ ] Gestion des erreurs
- [ ] Logging approprié
- [ ] Intégration testée
- [ ] Performances optimisées

---

**Version** : 1.0
**Dernière mise à jour** : 2024
**Licence** : MIT
