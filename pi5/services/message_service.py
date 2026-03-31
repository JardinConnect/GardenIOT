# services/message_parser.py
"""Parser pour les messages LoRa.
"""

from datetime import datetime
from config import SENSOR_TYPE_MAP

class MessageService:
    """Parse les messages au format B|TYPE|TIMESTAMP|UID|DATAS|E"""
    
    @staticmethod
    def parse(msg: str) -> dict | None:
        """Parse un message LoRa"""
        if not msg.startswith("B|") or not msg.endswith("|E"):
            return None
        
        content = msg[2:-2]
        
        parts = content.split("|", 3)
        
        if len(parts) < 3:
            return None
        
        parsed = {
            "type": parts[0],
            "timestamp": parts[1] if len(parts) > 1 else "",
            "uid": parts[2] if len(parts) > 2 else "",
            "datas": parts[3] if len(parts) > 3 else ""
        }
        
        if parsed["type"] == "D" and parsed["datas"]:
            parsed["sensors"] = MessageService._parse_sensor_data(parsed["datas"])
        
        elif parsed["type"] == "AT" and parsed["datas"]:
            parsed["alert"] = MessageService._parse_alert_triggered(parsed["datas"])
        
        return parsed

    @staticmethod
    def parse_alert_ack_datas(datas: str) -> tuple:
        """
        Parse le champ datas des messages AC/AD (ack alerte configurée/supprimée).
        """
        if not datas or not datas.strip():
            return ("UNKNOWN", None, None)
        parts = datas.strip().split("|", 1)
        raw_type = (parts[0] or "").strip()
        sensor_type = MessageService._normalize_sensor_type(raw_type) if raw_type else "UNKNOWN"
        max_val, min_val = None, None
        if len(parts) > 1 and parts[1]:
            max_val, min_val = MessageService._parse_max_min(parts[1].strip())
        return (sensor_type, max_val, min_val)

    @staticmethod
    def _normalize_sensor_type(raw: str) -> str:
        """
        Retourne le type capteur, en conservant l'index s'il est présent.
        """
        if not raw or not raw.strip():
            return "UNKNOWN"
        s = raw.strip().upper()
        i = 0
        while i < len(s) and s[i].isdigit():
            i += 1
        code = s[i:] if i < len(s) else ""
        if code in SENSOR_TYPE_MAP:
            return raw.strip().upper()
        return "UNKNOWN"

    @staticmethod
    def _parse_max_min(threshold_str: str) -> tuple:
        """Extrait max et min d'une chaîne type MAX24MIN0"""
        max_val, min_val = None, None
        if "MAX" in threshold_str:
            start = threshold_str.index("MAX") + 3
            end = threshold_str.index("MIN") if "MIN" in threshold_str else len(threshold_str)
            try:
                max_val = int(threshold_str[start:end])
            except ValueError:
                pass
        if "MIN" in threshold_str:
            start = threshold_str.index("MIN") + 3
            try:
                min_val = int(threshold_str[start:])
            except ValueError:
                pass
        return (max_val, min_val)
    
    @staticmethod
    def _parse_sensor_data(datas: str) -> dict:
        """
        Parse le format: 1TA25;1TS23;1HA62;1HS100;2HS10;1L4;1B100
        """
        sensors = {}
        
        for item in datas.split(";"):
            if not item:
                continue
            i = 1 
            code = ""
            while i < len(item) and item[i].isalpha():
                code += item[i]
                i += 1
            
            value_str = item[i:]
            
            if not code or not value_str:
                continue
            
            try:
                value_int = int(value_str)
                
                code_map = {
                    "TA": "ta",
                    "TS": "ts",
                    "HA": "ha",
                    "HS": "hs",
                    "L": "lx", 
                    "B": "bat"   
                }
                
                if code in code_map:
                    sensors[code_map[code]] = value_int
                    
            except ValueError:
                continue
        
        return sensors
    
    @staticmethod
    def _parse_alert_triggered(datas: str) -> dict:
        """Parse une alerte déclenchée: LUM|VAL30|MAX24MIN0"""
        try:
            parts = datas.split("|")
            if len(parts) < 2:
                return {}

            sensor_type = parts[0]
            val_part = parts[1]
            value_str = val_part.replace("VAL", "") if "VAL" in val_part else "0"
            threshold_str = parts[2] if len(parts) > 2 else ""

            max_val, min_val = MessageService._parse_max_min(threshold_str)

            return {
                "sensor_type": sensor_type,
                "value": int(value_str),
                "max": max_val,
                "min": min_val
            }
        except Exception as e:
            print(f"Erreur parsing alerte: {e}")
            return {}

    @staticmethod
    def build_alert_config(uid: str, sensor_type: str, max_val: int, min_val: int) -> str:
        """Construit l'ordre de création d'alerte (Type 'A')"""
        seuils = ""
        if max_val is not None:
            seuils += f"MAX{max_val}"
        if min_val is not None:
            seuils += f"MIN{min_val}"
            
        datas = f"{sensor_type}|{seuils}"
        
        return f"B|A|0|{uid}|{datas}|E"

    @staticmethod
    def build_alert_delete(uid: str, sensor_type: str, max_val=None, min_val=None) -> str:
        """Construit l'ordre de suppression d'alerte (Type 'AS')."""
        seuils = ""
        if max_val is not None:
            seuils += f"MAX{max_val}"
        if min_val is not None:
            seuils += f"MIN{min_val}"
        datas = f"{sensor_type}|{seuils}" if seuils else sensor_type
        return f"B|AS|0|{uid}|{datas}|E"
    
    @staticmethod
    def format_for_backend(parsed: dict) -> str | None:
        """Convertit au format backend"""
        if parsed["type"] == "D":
            return f"B|D|{parsed['timestamp']}|{parsed['uid']}|{parsed['datas']}|E"
        return None
