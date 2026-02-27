# services/message_parser.py
"""Parser pour les messages LoRa"""

from datetime import datetime

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
        
        # Parser les données capteurs si type DATA
        if parsed["type"] == "D" and parsed["datas"]:
            parsed["sensors"] = MessageService._parse_sensor_data(parsed["datas"])
        
        # Parser les alertes si type ALERT
        elif parsed["type"] == "AT" and parsed["datas"]:
            parsed["alert"] = MessageService._parse_alert_triggered(parsed["datas"])
        
        return parsed
    
    @staticmethod
    def _parse_sensor_data(datas: str) -> dict:
        """Parse: 1TA25;1TS23;1HA62;1HS100;1L4;1B100"""
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
            
            max_val = None
            min_val = None
            
            if "MAX" in threshold_str:
                # Extraction plus sûre
                start = threshold_str.index("MAX") + 3
                end = threshold_str.index("MIN") if "MIN" in threshold_str else len(threshold_str)
                try:
                    max_val = int(threshold_str[start:end])
                except: pass
            
            if "MIN" in threshold_str:
                start = threshold_str.index("MIN") + 3
                try:
                    min_val = int(threshold_str[start:])
                except: pass
            
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
    def build_ack_pairing(parent_id: str, uid: str) -> str:
        """Construit un ACK de pairing"""
        return f"B|PA|{parent_id}|{uid}||E"
    
    @staticmethod
    def build_alert_config(uid: str, sensor_type: str, max_val=None, min_val=None) -> str:
        """Construit le message de config alerte"""
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        config_str = f"{sensor_type}|"
        
        if max_val is not None:
            config_str += f"MAX{int(max_val)}"
        
        if min_val is not None:
            config_str += f"MIN{int(min_val)}"
            
        return f"B|A|{timestamp}|{uid}|{config_str}|E"
    
    @staticmethod
    def format_for_backend(parsed: dict) -> str | None:
        """Convertit au format backend"""
        if parsed["type"] == "D":
            return f"B|D|{parsed['timestamp']}|{parsed['uid']}|{parsed['datas']}|E"
        return None
