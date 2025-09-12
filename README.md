# Protocol de Communication LoRa

## Format du Message

```
B|TYPE|TIMESTAMP|UID(4octets)|DATAS|E
```

- **B** : Début du message
- **TYPE** : Type de capteur (voir ci-dessous)
- **TIMESTAMP** : Horodatage de la mesure
- **UID** : Identifiant unique du noeud (4 octets)
- **DATAS** : Données du capteur (8 bits, 0-100 pour pourcentages, valeurs décimales pour autres)
- **E** : Fin du message

## Types de Messages

| Type | Description |
|------|-------------|
| 1    | Datas (données de capteurs) |
| 2    | Alerte |
| 3    | Error |

## Types de Capteurs

| Code | Description |
|------|-------------|
| TA   | Température Air |
| TS   | Température Sol |
| HA   | Humidité Air |
| HS   | Humidité Sol |
| B    | Batterie |
| L    | Luminosité |

## Format ACK

Structure de réponse avec gestion d'erreurs :
- ACK positif pour confirmation de réception
- Gestion des erreurs de transmission

## Exemples de Messages

### Message de type Datas (Type 1)
```
B|1|17778946513|f5io|1B100:1TA12:1TS13:1HA25:1HS100:2HS95:L9|E
```

Décomposition :
- `B` : Début
- `1` : Type de message (Datas)
- `17778946513` : Timestamp
- `f5io` : UID du noeud
- `1B100:1TA12:1TS13:1HA25:1HS100:2HS95:L9` : Données (séparées par `:`)
  - `1B100` : Batterie à 100%
  - `1TA12` : Température Air 12°C
  - `1TS13` : Température Sol 13°C
  - `1HA25` : Humidité Air 25%
  - `1HS100` : Humidité Sol 1 à 100%
  - `2HS95` : Humidité Sol 2 à 95%
  - `L9` : Luminosité 9%
- `E` : Fin

### Message d'Alerte (Type 2)
```
B|2|781354877456|f5yu|2HS0|E
```

Décomposition :
- `B` : Début
- `2` : Type de message (Alerte)
- `781354877456` : Timestamp
- `f5yu` : UID du noeud
- `2HS0` : Alerte - Humidité Sol 2 à 0% (sol sec)
- `E` : Fin

### Message d'Erreur (Type 3)
```
B|3|78455465164|f5yu|1HSERR|E
```

Décomposition :
- `B` : Début
- `3` : Type de message (Error)
- `78455465164` : Timestamp
- `f5yu` : UID du noeud
- `1HSERR` : Erreur sur le capteur Humidité Sol 1
- `E` : Fin

## Notes

- Les données sont encodées sur 8 bits
- Conversion en valeur décimale côté récepteur
- Communication unidirectionnelle : Pico2W → Pi5
- Format des données dans la section DATAS :
  - Pour messages type 1 : `[ID][TYPE][VALEUR]:[ID][TYPE][VALEUR]:...`
  - Chaque donnée capteur est séparée par `:`
  - `[ID]` : Numéro du capteur (1, 2, etc.) - optionnel pour capteurs uniques comme L
  - `[TYPE]` : Type de capteur (TA, TS, HA, HS, B, L)
  - `[VALEUR]` : Valeur mesurée