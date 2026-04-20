"""
Modèles de données pour les messages LoRa et MQTT
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
import json
from datetime import datetime


def extract_sensor_index_and_code(identifier: str) -> Tuple[int, str]:
    """
    Extrait l'index et le code d'un identifiant de capteur.
    
    Args:
        identifier: Format "1TA", "2HA", etc.
        
    Returns:
        Tuple[int, str]: (index, code) ex: (1, "TA")
        
    Examples:
        >>> extract_sensor_index_and_code("1TA")
        (1, "TA")
        >>> extract_sensor_index_and_code("2HS")
        (2, "HS")
    """
    if not identifier or len(identifier) < 2:
        return 0, "UNKNOWN"
    
    # Extraire les chiffres du début
    index_str = ''
    code_str = ''
    
    for i, char in enumerate(identifier):
        if char.isdigit():
            index_str += char
        else:
            code_str = identifier[i:]
            break
    
    if index_str and code_str:
        return int(index_str), code_str
    return 0, "UNKNOWN"


class MessageType(Enum):
    """Types de messages supportés"""
    DATA = "D"           # Données capteurs
    STATUS = "S"         # Message de status (fin de cycle, avec compte)
    PAIRING = "PA"        # Demande de pairing
    UNPAIR = "U"         # Demande de désappariement
    ALERT_CONFIG = "A"   # Configuration d'alerte
    ALERT_TRIGGER = "T"  # Alerte déclenchée
    ACK = "ACK"           # Accusé de réception
    PA_ACK = "PA_ACK"     # Accusé de réception du pairing
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
        """Parse les données capteurs.
        
        Format: 1TA25;1TS18;1HA60;1HS45;1L450
        
        Structure: {index}{code}{value}
        - index: 1 chiffre (1-9)
        - code: lettres (TA, TS, HA, HS, L, etc.)
        - value: nombre (entier ou décimal, peut être négatif)
        
        Exemples:
        - 1TA25   -> code=TA, index=1, value=25
        - 1HS45   -> code=HS, index=1, value=45
        - 1L450   -> code=L,  index=1, value=450
        - 1TA-5   -> code=TA, index=1, value=-5
        """
        sensors = {}
        
        for item in data_str.split(";"):
            item = item.strip()
            if len(item) < 3:
                continue
            
            try:
                # Premier caractère = index
                index = item[0]
                if not index.isdigit():
                    continue
                
                rest = item[1:]
                
                # Séparer lettres (code) et chiffres/signe (valeur)
                code = ''
                value_str = ''
                
                for i, char in enumerate(rest):
                    if char.isalpha():
                        code += char
                    else:
                        value_str = rest[i:]
                        break
                
                if code and value_str:
                    value = float(value_str)
                    sensor_key = f"{index}{code}"
                    sensors[sensor_key] = value
                    
            except (ValueError, IndexError):
                continue
        
        return sensors

    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour JSON - conserve le format original"""
        return {
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
    def __init__(self, alert_id: str, is_active: bool, cell_ids: List[str], sensors: dict):
        self.alert_id = alert_id
        self.is_active = is_active
        self.cell_ids = cell_ids
        self.sensors = sensors
    
    def to_lora_data(self) -> str:
        """Convertit en format pour envoi LoRa"""
        # Format: ID:ACTIVE:SENSOR1;SENSOR2
        
        # Convertir les sensors en format LoRa
        sensor_configs = []
        for sensor in self.sensors or []:
            sensor_id = sensor.get("sensorId", "")
            critical = sensor.get("criticalRange", [0, 100])
            warning = sensor.get("warningRange", [0, 100])
            
            # Format: TYPE:INDEX:CRIT_MIN:CRIT_MAX:WARN_MIN:WARN_MAX
            config_str = f"{sensor_id}:{critical[0]}:{critical[1]}:{warning[0]}:{warning[1]}"
            sensor_configs.append(config_str)
        
        sensors_str = ";".join(sensor_configs)
        
        return f"{self.alert_id}:{int(self.is_active)}:{sensors_str}"
    
    @classmethod
    def from_mqtt_payload(cls, payload: Dict[str, Any]) -> 'AlertConfig':
        """Crée une config à partir d'un payload MQTT (format backend)"""
        return cls(
            alert_id=str(payload.get("id", "")),
            is_active=payload.get("is_active", True),
            cell_ids=payload.get("cell_ids", []),
            sensors=payload.get("sensors", {})
        )


@dataclass
class AlertTrigger:
    """Alerte déclenchée - envoyée par les ESP32"""
    alert_id: str  # ID de l'alerte
    cell_uid: str  # UID de la cellule
    sensor_type: str  # Type de capteur (TA, HA, etc.)
    sensor_index: int = 0  # Index du capteur
    value: float = 0.0  # Valeur mesurée
    trigger_type: str = "C"  # "critical" ou "warning"
    timestamp: str = ""  # Timestamp du déclenchement
    
    @classmethod
    def from_lora_data(cls, data_str: str, uid: str = None, timestamp: str = None) -> 'AlertTrigger':
        """Parse les données d'alerte depuis le format LoRa
        
        Format standardisé avec ; :
        - ESP32: alert-123;W;1HA;54.3
        """
        parts = data_str.split(';')
        
        # Format ESP32 : alert-123;W;1HA;54.3
        if len(parts) == 4 and uid and timestamp:
            alert_id, level, identifier, value = parts[:4]
            sensor_index, sensor_type = extract_sensor_index_and_code(identifier)
            
            return cls(
                alert_id=alert_id,
                cell_uid=uid,
                sensor_type=sensor_type,
                sensor_index=sensor_index,
                value=float(value),
                trigger_type=level,
                timestamp=timestamp
            )
        else:
            raise ValueError("Error parsing alert trigger")
            
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
