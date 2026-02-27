"""
Modèles de données pour les messages LoRa et MQTT
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum
import json
from datetime import datetime


class MessageType(Enum):
    """Types de messages supportés"""
    DATA = "D"           # Données capteurs
    PAIRING = "P"        # Demande de pairing
    UNPAIR = "U"         # Demande de désappariement
    ALERT_CONFIG = "A"   # Configuration d'alerte
    ALERT_TRIGGER = "T"  # Alerte déclenchée
    ACK = "PA"           # Accusé de réception
    COMMAND = "C"        # Commande générale


@dataclass
class LoRaMessage:
    """Message au format LoRa"""
    message_type: MessageType
    timestamp: str
    uid: str
    data: str
    raw: Optional[str] = None
    
    def to_lora_format(self) -> str:
        """Convertit en format LoRa: B|TYPE|TIMESTAMP|UID|DATAS|E"""
        return f"B|{self.message_type.value}|{self.timestamp}|{self.uid}|{self.data}|E"
    
    @classmethod
    def from_lora_format(cls, raw_message: str) -> Optional['LoRaMessage']:
        """Parse un message LoRa brut"""
        if not raw_message.startswith("B|") or not raw_message.endswith("|E"):
            return None
        
        try:
            parts = raw_message[2:-2].split("|")
            if len(parts) < 3:
                return None
            
            msg_type = MessageType(parts[0])
            timestamp = parts[1] if len(parts) > 1 else ""
            uid = parts[2] if len(parts) > 2 else ""
            data = parts[3] if len(parts) > 3 else ""
            
            return cls(
                message_type=msg_type,
                timestamp=timestamp,
                uid=uid,
                data=data,
                raw=raw_message
            )
        except (ValueError, IndexError):
            return None


@dataclass
class MqttMessage:
    """Message au format MQTT"""
    topic: str
    payload: Dict[str, Any]
    qos: int = 1
    retain: bool = False
    
    def to_json(self) -> str:
        """Convertit le payload en JSON"""
        return json.dumps(self.payload)
    
    @classmethod
    def from_mqtt(cls, topic: str, payload: str, qos: int = 1) -> 'MqttMessage':
        """Crée un message à partir de données MQTT"""
        try:
            payload_dict = json.loads(payload)
            return cls(topic=topic, payload=payload_dict, qos=qos)
        except json.JSONDecodeError:
            return cls(topic=topic, payload={"raw": payload}, qos=qos)


@dataclass
class SensorData:
    """Données capteurs parsées - conserve les codes originaux"""
    raw_data: str  # Format original: "1TA25;1HA60;1TS23..."
    parsed_values: Dict[str, float]  # Dictionnaire des valeurs parsées {code: valeur}
    
    def __init__(self, raw_data: str = ""):
        self.raw_data = raw_data
        self.parsed_values = self._parse_sensor_data(raw_data)
    
    def _parse_sensor_data(self, data_str: str) -> Dict[str, float]:
        """Parse les données capteurs avec support des formats 1TA:25, 2HB:60, etc.
        
        Format attendu: INDEXCODE:VALUE où:
        - INDEX: 1-9 (index du capteur)
        - CODE: 2+ caractères (type de capteur)
        - VALUE: valeur numérique
        - Séparateur: ':' entre CODE et VALUE
        
        Exemples valides:
        - 1TA:25 (index 1, code TA, valeur 25)
        - 2HB:60 (index 2, code HB, valeur 60)
        - 1TEMPERATURE:23.5 (index 1, code TEMPERATURE, valeur 23.5)
        """
        sensors = {}
        
        for item in data_str.split(";"):
            if len(item) < 5:  # Minimum: 1A:0 (index + 1 char code + : + 1 char value)
                continue
            
            try:
                # Extraire l'index (premier caractère)
                index = item[0]
                
                # Trouver la position du séparateur ':'
                colon_pos = item.find(':')
                
                if colon_pos == -1:
                    # Ancien format sans ':' - ignorer pour l'instant
                    # (pourrait être ajouté si besoin pour compatibilité)
                    continue
                
                # Extraire le code (entre index et :)
                code = item[1:colon_pos]
                
                # Extraire la valeur (après :)
                value_str = item[colon_pos+1:]
                
                # Convertir en float
                value = float(value_str)
                
                # Stocker avec la clé CODE:INDEX pour gérer les multiples capteurs
                # Ex: "TA:1", "HB:2", etc.
                sensor_key = f"{code}:{index}"
                sensors[sensor_key] = value
                
            except (ValueError, IndexError):
                continue
        
        return sensors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour JSON - conserve le format original"""
        return {
            "raw": self.raw_data,  # Format original pour le backend
            "sensors": self.parsed_values,  # Valeurs parsées
            "timestamp": datetime.now().isoformat()
        }
    
    @classmethod
    def from_lora_data(cls, data_str: str) -> 'SensorData':
        """Crée un SensorData à partir des données LoRa brutes"""
        return cls(raw_data=data_str)


@dataclass
class AlertConfig:
    """Configuration d'alerte - correspond au modèle backend"""
    alert_id: str  # UUID de l'alerte
    title: str
    is_active: bool = True
    warning_enabled: bool = False
    cell_ids: list = None  # Liste des UID des cellules concernées
    sensors: list = None  # Liste des configurations de capteurs
    
    def to_lora_data(self) -> str:
        """Convertit en format pour envoi LoRa"""
        # Format: ID|TITLE|ACTIVE|WARNING|CELL1,CELL2|SENSOR1,SENSOR2
        cells = ",".join(self.cell_ids) if self.cell_ids else ""
        
        # Convertir les sensors en format LoRa
        sensor_configs = []
        for sensor in self.sensors or []:
            sensor_type = sensor.get("type", "")
            index = sensor.get("index", 0)
            critical = sensor.get("criticalRange", [0, 100])
            warning = sensor.get("warningRange", [0, 100])
            
            # Format: TYPE:INDEX:CRIT_MIN:CRIT_MAX:WARN_MIN:WARN_MAX
            config_str = f"{sensor_type}:{index}:{critical[0]}:{critical[1]}:{warning[0]}:{warning[1]}"
            sensor_configs.append(config_str)
        
        sensors_str = "|".join(sensor_configs)
        
        return f"{self.alert_id}|{self.title}|{int(self.is_active)}|{int(self.warning_enabled)}|{cells}|{sensors_str}"
    
    @classmethod
    def from_mqtt_payload(cls, payload: Dict[str, Any]) -> 'AlertConfig':
        """Crée une config à partir d'un payload MQTT (format backend)"""
        return cls(
            alert_id=str(payload.get("id", "")),
            title=payload.get("title", "Nouvelle alerte"),
            is_active=payload.get("is_active", True),
            warning_enabled=payload.get("warning_enabled", False),
            cell_ids=payload.get("cell_ids", []),
            sensors=payload.get("sensors", [])
        )
    
    @classmethod
    def from_backend_model(cls, alert: 'Alert') -> 'AlertConfig':
        """Crée une config à partir du modèle SQLAlchemy Alert"""
        return cls(
            alert_id=str(alert.id),
            title=alert.title,
            is_active=alert.is_active,
            warning_enabled=alert.warning_enabled,
            cell_ids=alert.cell_ids,
            sensors=alert.sensors
        )


@dataclass
class AlertTrigger:
    """Alerte déclenchée - envoyée par les ESP32"""
    alert_id: str  # ID de l'alerte
    cell_uid: str  # UID de la cellule
    sensor_type: str  # Type de capteur (TA, HA, etc.)
    sensor_index: int = 0  # Index du capteur
    value: float = 0.0  # Valeur mesurée
    trigger_type: str = "critical"  # "critical" ou "warning"
    timestamp: str = ""  # Timestamp du déclenchement
    
    def to_lora_data(self) -> str:
        """Convertit en format LoRa: ALERT_ID|CELL_UID|SENSOR|INDEX|VALUE|TYPE|TIMESTAMP"""
        return f"{self.alert_id}|{self.cell_uid}|{self.sensor_type}|{self.sensor_index}|{self.value}|{self.trigger_type}|{self.timestamp}"
    
    @classmethod
    def from_lora_data(cls, data_str: str) -> 'AlertTrigger':
        """Parse les données d'alerte depuis le format LoRa"""
        parts = data_str.split("|")
        if len(parts) >= 7:
            return cls(
                alert_id=parts[0],
                cell_uid=parts[1],
                sensor_type=parts[2],
                sensor_index=int(parts[3]),
                value=float(parts[4]),
                trigger_type=parts[5],
                timestamp=parts[6]
            )
        return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour MQTT"""
        return {
            "alert_id": self.alert_id,
            "cell_uid": self.cell_uid,
            "sensor_type": self.sensor_type,
            "sensor_index": self.sensor_index,
            "value": self.value,
            "trigger_type": self.trigger_type,
            "timestamp": self.timestamp
        }
