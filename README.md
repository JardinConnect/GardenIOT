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
| TA   | Température Air | {-40;80}
| TS   | Température Sol | {-40;80}
| HA   | Humidité Air | {0;100}
| HS   | Humidité Sol | {0;100}
| B    | Batterie | {0;100}
| L    | Luminosité | {0;65535}

## Format ACK

Structure de réponse avec gestion d'erreurs :
- ACK positif pour confirmation de réception
- Gestion des erreurs de transmission

## Exemples de Messages

### Message de type Datas (Type 1)
```
B|1|17778946513|f5io|1B100:1TA12:1TS13:1HA25:1HS100:2HS95:1L9|E
```

Décomposition :
- `B` : Début
- `1` : Type de message (Datas)
- `17778946513` : Timestamp
- `f5io` : UID du noeud
- `1B1001TA121TS131HA251HS1002HS95L9` : Données
  - `1B100` : Batterie à 100%
  - `1TA12` : Température Air 12°C
  - `1TS13` : Température Sol 13°C
  - `1HA25` : Humidité Air 25%
  - `1HS100` : Humidité Sol 1 à 100%
  - `2HS95` : Humidité Sol 2 à 95% (Si jamais un deuxième est branché ! Sinon non)
  - `L9` : Luminosité 12455 lux
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
- Format des données : `1[TYPE][VALEUR]` où le préfixe `1` indique une donnée valide
