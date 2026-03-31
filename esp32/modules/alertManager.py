"""Gestionnaire d'alertes pour capteurs"""

import time
import json

def log(message):
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
        try:
            with open(self.config_file, 'r') as f:
                raw_content = f.read().strip() 
                if not raw_content:
                    self.alerts = {}
                    return

                config = json.loads(raw_content)
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
            log(f"Erreur de lecture (Fichier ignoré) : {e}")
            self.alerts = {}
    
    def _save_alerts(self) -> bool:
        """Sauvegarde les alertes"""
        try:
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            except:
                config = {}
            
            config['alerts'] = self.alerts
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
            return True # Succès !
        except Exception as e:
            log(f"Erreur sauvegarde PHYSIQUE: {e}")
            return False
    
    def configure_alert(self, sensor_type: str, max_val: int, min_val: int):
        """Configuration d'une alerte"""
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
        """Parser les données des capteurs"""
        sensors = {}
        try:
            items = datas.split(";")
            for item in items:
                if not item: continue
                
                code = ""
                i = 0
                while i < len(item):
                    if item[i:].isdigit() or (item[i] == '-' and item[i+1:].isdigit()):
                        break
                    code += item[i]
                    i += 1
                
                value_str = item[i:]
                
                if code and value_str:
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
                remaining_ms = self.cooldown - time.ticks_diff(now, last_trigger)
                remaining_sec = remaining_ms // 1000
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
        
        self.lora_manager.envoyer_rafale(alert_msg)
    
    def traiter_config_lora(self, ordre: dict):
        """Traite une commande de configuration d'alerte et renvoie la string pour l'ACK."""
        try:
            datas = ordre.get('datas', '')
            if not datas or '|' not in datas:
                log("Config de l'alerte invalide (format incorrect)")
                return None
            
            parts = datas.split('|')
            sensor_type = parts[0].strip()
            threshold_str = parts[1] if len(parts) > 1 else ""
            
            max_val, min_val = self.parse_alert_config(threshold_str)
            
            if max_val is None and min_val is None:
                log("Seuils invalides (ni MAX ni MIN trouvés)")
                return None
            
            self.configure_alert(sensor_type, max_val, min_val)
            
            

            self.alerts[sensor_type] = {
                "max": max_val, "min": min_val,
                "last_trigger": time.ticks_ms() - self.cooldown - 1000
            }
            
            if self._save_alerts():
                log(f"Alerte Configurée: {sensor_type} (min={min_val}, max={max_val})")
                
                seuils = ""
                if max_val is not None: seuils += f"MAX{max_val}"
                if min_val is not None: seuils += f"MIN{min_val}"
                return f"{sensor_type}|{seuils}"
            else:
                log(f"Échec critique de l'écriture disque pour {sensor_type}")
                return None 

        except Exception as e:
            log(f"Erreur: {e}")
            return None

    def remove_alert(self, sensor_type: str):
        """Supprime l'alerte et retourne (max_val, min_val) de l'alerte supprimée."""
        
        if sensor_type in self.alerts:
            data = self.alerts[sensor_type]
            max_val, min_val = data.get("max"), data.get("min")
            del self.alerts[sensor_type]
            self._save_alerts()
            log(f"Suppression alerte confirmée: {sensor_type} (max={max_val}, min={min_val})")
            return (max_val, min_val)
        log(f"Aucune alerte à supprimer pour: {sensor_type}, on confirme quand même.")
        return (None, None)
    
    def remove_alert_and_build_ad_datas(self, sensor_type: str) -> str:
        """
        Supprime l'alerte et retourne la chaîne 'datas' à passer à construire_message("AD", datas)
        """
        max_val, min_val = self.remove_alert(sensor_type)
        datas = sensor_type
        if max_val is not None or min_val is not None:
            seuils = ""
            if max_val is not None:
                seuils += f"MAX{max_val}"
            if min_val is not None:
                seuils += f"MIN{min_val}"
            datas = f"{sensor_type}|{seuils}"
        return datas
            
    def get_active_alerts(self) -> list:
        return list(self.alerts.keys())
    
