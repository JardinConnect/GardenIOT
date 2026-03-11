# Tests pour le Système Gateway Pi5

## Structure des Tests

```
tests/
├── unit/                # Tests unitaires
│   ├── test_messages.py  # Tests des modèles de messages
│   └── test_message_router.py  # Tests du router
│
└── integration/         # Tests d'intégration
    └── test_data_flow.py # Tests des flux complets
```

## Types de Tests

### 1. Tests Unitaires

**Objectif** : Tester chaque composant individuellement en isolation

**Couverture** :
- Parsing et formatage des messages LoRa
- Conversion JSON pour MQTT
- Création et manipulation des modèles de données
- Routing des différents types de messages

**Exécution** :
```bash
# Exécuter tous les tests unitaires
python -m unittest discover tests/unit

# Exécuter un test spécifique
python tests/unit/test_messages.py
```

### 2. Tests d'Intégration

**Objectif** : Tester les flux complets à travers plusieurs composants

**Couverture** :
- Flux complet de données capteurs (LoRa → MQTT)
- Flux complet de configuration d'alerte (MQTT → LoRa)
- Flux complet d'alerte déclenchée (LoRa → MQTT)
- Flux complet de pairing
- Gestion des cellules non autorisées

**Exécution** :
```bash
# Exécuter tous les tests d'intégration
python -m unittest discover tests/integration

# Exécuter un test spécifique avec plus de détails
python tests/integration/test_data_flow.py -v
```

## Configuration des Tests

### Mocks et Dependencies

Les tests utilisent `unittest.mock` pour simuler :
- La communication LoRa
- La communication MQTT
- Le repository des enfants
- Les états du système

### Structure Typique d'un Test

```python
def test_nom_du_test(self):
    # 1. Configuration (Setup)
    # - Créer les mocks
    # - Configurer les comportements
    
    # 2. Exécution (Exercise)
    # - Appeler la méthode à tester
    
    # 3. Vérification (Assert)
    # - Vérifier les appels aux mocks
    # - Vérifier les résultats
    
    # 4. Nettoyage (Teardown)
    # - Réinitialiser les mocks si nécessaire
```

## Exécution des Tests

### Tous les Tests
```bash
python -m unittest discover tests
```

### Tests Unitaires Seulement
```bash
python -m unittest discover tests/unit
```

### Tests d'Intégration Seulement
```bash
python -m unittest discover tests/integration
```

### Test Spécifique
```bash
python tests/unit/test_messages.py
```

### Avec Plus de Détails
```bash
python -m unittest discover tests -v
```

## Scénarios Testés

### 1. Données Capteurs
- **Entrée** : Message LoRa avec données capteurs
- **Sortie** : Message MQTT avec données formatées
- **Validation** : Format des données, présence de tous les champs

### 2. Configuration d'Alerte
- **Entrée** : Payload MQTT avec configuration d'alerte
- **Sortie** : Messages LoRa envoyés aux cellules concernées
- **Validation** : Format LoRa, envoi à toutes les cellules valides

### 3. Alerte Déclenchée
- **Entrée** : Message LoRa avec alerte déclenchée
- **Sortie** : Message MQTT avec détails de l'alerte
- **Validation** : Tous les champs présents, format correct

### 4. Pairing
- **Entrée** : Message LoRa de demande de pairing
- **Sortie** : ACK LoRa + Notification MQTT
- **Validation** : Enfant ajouté, messages envoyés

### 5. Cellule Non Autorisée
- **Entrée** : Message d'une cellule non appairée
- **Sortie** : Aucun message
- **Validation** : Message ignoré, rien publié

## Bonnes Pratiques

1. **Isolation** : Chaque test est indépendant
2. **Clarté** : Noms de tests descriptifs
3. **Validation** : Vérification de tous les aspects importants
4. **Maintenabilité** : Tests faciles à comprendre et modifier
5. **Performance** : Exécution rapide

## Couverture de Code

Les tests couvrent :
-  Parsing des messages LoRa
-  Création des modèles de données
-  Routing des messages
-  Transformation des formats
-  Gestion des erreurs
-  Validation des données
-  Flux complets de bout en bout

## Intégration CI/CD

Pour intégrer ces tests dans un pipeline CI/CD, ajouter :

```yaml
# Exemple pour GitHub Actions
- name: Run tests
  run: |
    python -m pip install -r requirements.txt
    python -m unittest discover tests -v
```

## Développement de Nouveaux Tests

Pour ajouter un nouveau test :

1. **Identifier le composant** à tester
2. **Créer un nouveau fichier** dans `tests/unit/` ou `tests/integration/`
3. **Importer les dépendances** nécessaires
4. **Créer une classe** héritant de `unittest.TestCase`
5. **Implémenter les méthodes** de test
6. **Exécuter** pour vérifier

Exemple minimal :
```python
import unittest
from unittest.mock import Mock
from my_module import MyClass

class TestMyClass(unittest.TestCase):
    def test_my_method(self):
        obj = MyClass()
        result = obj.my_method("input")
        self.assertEqual(result, "expected_output")

if __name__ == '__main__':
    unittest.main()
```

## Rapport de Couverture

Pour générer un rapport de couverture :

```bash
pip install coverage
coverage run -m unittest discover tests
coverage report
coverage html  # Génère un rapport HTML
```

## Maintenance

- **Mettre à jour les tests** lorsque le code change
- **Ajouter des tests** pour les nouvelles fonctionnalités
- **Supprimer les tests** pour le code supprimé
- **Exécuter régulièrement** pour détecter les régressions
