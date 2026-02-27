"""Gestionnaire d'alertes pour capteurs"""

import time
import json

def log(message):
    """Affiche un message avec l'heure courante (HH:MM:SS)"""
    t = time.localtime()
    timestamp = "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])
    print(f"[{timestamp}] {message}")

class AlertManager:
    """
    Gère les alertes sur les valeurs des capteurs
    """
    
    def __init__(self, lora_manager, config_file='/config/config.json'):
        self.lora_manager = lora_manager
        self.config_file = config_file
        self.alerts = {} 
        
        self.check_interval = 5000 
        self.cooldown = 30000

        
        self.last_check = 0
        self._load_alerts()
    
    def _load_alerts(self):
        """Charge les alertes mais réinitialise les timers"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                loaded_alerts = config.get('alerts', {})
                
                self.alerts = {}
                past_time = time.ticks_ms() - self.cooldown - 1000
                
                for sensor, data in loaded_alerts.items():
                    self.alerts[sensor] = {
                        "max": data.get("max"),
                        "min": data.get("min"),
                        "last_trigger": past_time 
                    }
        except Exception as e:
            self.alerts = {}
    
    def _save_alerts(self):
        """Sauvegarde les alertes dans le fichier config"""
        try:
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            except:
                config = {}
            
            config['alerts'] = self.alerts
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
            
        except Exception as e:
            log(f"Erreur sauvegarde alerte: {e}")
    
    def configure_alert(self, sensor_type: str, max_val: int, min_val: int):
        """Configure une alerte"""
        fake_last_trigger = time.ticks_ms() - self.cooldown - 1000
        
        self.alerts[sensor_type] = {
            "max": max_val,
            "min": min_val,
            "last_trigger": fake_last_trigger 
        }
        self._save_alerts()
    
    def parse_alert_config(self, threshold_str: str):
        """Parse une config d'alerte"""
        try:
            max_val = None
            min_val = None
            
            if "MAX" in threshold_str:
                start = threshold_str.index("MAX") + 3
                end = threshold_str.index("MIN") if "MIN" in threshold_str else len(threshold_str)
                max_val = int(threshold_str[start:end])
            
            if "MIN" in threshold_str:
                start = threshold_str.index("MIN") + 3
                min_val = int(threshold_str[start:])
            
            return max_val, min_val
        except Exception as e:
            log(f"Erreur parsing alerte: {e}")
            return None, None
    
    def parse_sensor_data(self, datas: str) -> dict:
        """Parse la string de données capteurs"""
        sensors = {}
        try:
            items = datas.split(";")
            for item in items:
                if not item: continue
                
                code = ""
                value_str = ""
                i = 1
                while i < len(item) and item[i].isalpha():
                    code += item[i]
                    i += 1
                value_str = item[i:]
                
                if code and value_str:
                    if code == "L": code = "L"
                    elif code == "B": code = "B"
                    sensors[code] = int(value_str)
        except Exception as e:
            log(f"Erreur parse sensors alerte: {e}")
        return sensors
    
    def should_check(self) -> bool:
        """Retourne True si il faut vérifier les alertes"""
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_check) >= self.check_interval:
            self.last_check = now
            return True
        return False
    
    def check_and_send_alerts(self, sensor_data_str: str):
        """Vérifie les alertes et envoie les messages si déclenchées"""
        sensor_data = self.parse_sensor_data(sensor_data_str)
        
        for sensor_type, alert_config in self.alerts.items():
            if sensor_type not in sensor_data:
                continue
            
            value = sensor_data[sensor_type]
            exceeded = False
            
            if alert_config["max"] is not None and value > alert_config["max"]:
                exceeded = True
                log(f"Alerte déclenchée: {sensor_type}={value} > MAX={alert_config['max']}")
            elif alert_config["min"] is not None and value < alert_config["min"]:
                exceeded = True
                log(f"Alerte déclenchée: {sensor_type}={value} < MIN={alert_config['min']}")
            
            if not exceeded:
                continue
            
            now = time.ticks_ms()
            last_trigger = alert_config.get("last_trigger", 0)
            
            if time.ticks_diff(now, last_trigger) < self.cooldown:
                # Calcul en secondes
                remaining_ms = self.cooldown - time.ticks_diff(now, last_trigger)
                remaining_sec = remaining_ms // 1000
                log(f"Alerte {sensor_type} non envoyé ({remaining_sec}s restants avant nouvel envoi)")
                continue
            
            # Mise à jour du timestamp
            alert_config["last_trigger"] = now
            self._save_alerts()
            
            # Envoyer l'alerte
            self._send_alert_message(sensor_type, value, alert_config)
    
    def _send_alert_message(self, sensor_type: str, value: int, alert_config: dict):
        """Construit et envoie un message d'alerte"""
        max_val = alert_config['max'] if alert_config['max'] is not None else 999
        min_val = alert_config['min'] if alert_config['min'] is not None else 0
        
        datas = f"{sensor_type}|VAL{value}|MAX{max_val}MIN{min_val}"
        alert_msg = self.lora_manager.construire_message("AT", datas)
        
        log(f"Envoi Message Alerte: {sensor_type}={value}")
        self.lora_manager.envoyer_rafale(alert_msg)
    
    def traiter_config_lora(self, ordre: dict):
        """Traite une commande de configuration d'alerte reçue en LoRa"""
        try:
            datas = ordre.get('datas', '')
            if not datas or '|' not in datas:
                log("Config de l'alerte invalide")
                return
            
            parts = datas.split('|')
            sensor_type = parts[0]
            threshold_str = parts[1] if len(parts) > 1 else ""
            
            max_val, min_val = self.parse_alert_config(threshold_str)
            
            if max_val is None and min_val is None:
                log("Seuils invalides")
                return
            
            self.configure_alert(sensor_type, max_val, min_val)
            log(f"Alerte Configurée: {sensor_type} (min={min_val}, max={max_val})")
            
        except Exception as e:
            log(f"Erreur alerte: {e}")
            
    def get_active_alerts(self) -> list:
        return list(self.alerts.keys())
    
    def remove_alert(self, sensor_type: str):
        if sensor_type in self.alerts:
            del self.alerts[sensor_type]
            self._save_alerts()
            log(f"Suppression alerte: {sensor_type}")