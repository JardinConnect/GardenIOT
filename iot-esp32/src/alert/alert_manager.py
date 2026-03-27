"""
Alert Manager - Observer Pattern implementation.
Subscribes to sensor events via EventBus to monitor thresholds.
"""

from alert.alert_registry import AlertRegistry
import time

class AlertManager:
    """
    Observer that monitors sensor thresholds.
    Subscribes to events and checks values against config alerts.
    """

    def __init__(self, config, event_bus):
        """
        Initialize AlertManager and subscribe to events.

        Args:
            config: ConfigManager instance
            event_bus: EventBus instance to subscribe to
        """
        self._config = config
        self._event_bus = event_bus
        self._active_alerts = {}
        self._last_sent_ts = {}  # {alert_key: epoch_seconds}
        self.msg_type = 'A'  # Alert config messages from LoRa
        self.alert_registry = AlertRegistry()
        self.timeout_between_same_alerts = config.get('alert.alert_timeout', 60*60*24)  # 1 day

        # Build thresholds from sensor config
        self._load_alerts_from_config()

        # Subscribe to events (Observer Pattern)
        self._event_bus.subscribe('message.received.{msg_type}'.format(msg_type=self.msg_type), self.handle_incoming_message)
        self._event_bus.subscribe('sensor.data', self.on_sensor_data)
        self._event_bus.subscribe('sensor.read_error', self.on_sensor_error)

        print(f"[AlertManager] Monitoring {len(self.alert_registry.get_all())} sensors")

    def handle_incoming_message(self, message):
        """Handle incoming messages from EventBus"""
        if not message:
            return

        msg_data = message.get('data', '')[0] if message.get('data') else None
        print(f"[AlertManager] Message received: data={msg_data}")

        self.handle_config_message(message)

    def handle_config_message(self, message):
        """Process alert configuration messages from LoRa"""
        try:
            # Extract message data
            data = message.get('data', '')
            if not data:
                print("[AlertManager] No data in message")
                return

            print(f"[AlertManager] Alert config received: {data}")
            # Parse LoRa format
            parts = data.split(':')
            if len(parts) < 3:
                print("[AlertManager] Invalid message format")
                return

            alert_id = parts[0]
            is_active = parts[1] == '1'
            sensors_str = parts[2]

            print(f"[AlertManager] Config for alert {alert_id} (active={is_active})")

            # Update configuration
            self._update_alert_config(alert_id, is_active, sensors_str)

            # Save configuration
            self._config.save()

        except Exception as e:
            print(f"[AlertManager] Error processing message: {e}")

    def _update_alert_config(self, alert_id, is_active, sensors_str):
        """Update alert configuration in config.json"""
        try:
            sensor_configs = sensors_str.split(';')
            for config in sensor_configs:
                if not config:
                    continue

                # Format: INDEXCODE:CRIT_MIN:CRIT_MAX[:WARN_MIN:WARN_MAX]
                parts = config.split(':')
                if len(parts) < 3 or len(parts) > 5:
                    print(f"[AlertManager] Invalid sensor format: {config}")
                    continue

                index, metric_code = self._separate_index_and_code(parts[0])
                crit_min = int(parts[1])
                crit_max = int(parts[2])

                # Handle warning thresholds (optional)
                has_warning = len(parts) == 5
                warn_min = int(parts[3]) if has_warning else None
                warn_max = int(parts[4]) if has_warning else None

                # Find matching sensor and metric
                sensors = self._config.get('sensors', [])
                for sensor in sensors:
                    codes = sensor.get('codes', {})
                    for metric, code in codes.items():
                        if code == metric_code and sensor.get('index', 0) == index:
                            # Find the sensor index in the sensors array
                            sensors_list = self._config.get('sensors', [])
                            sensor_index = next((i for i, s in enumerate(sensors_list) if s.get('name') == sensor['name']), None)
                            if sensor_index is not None:
                                alerts_path = f"sensors.{sensor_index}.alerts.{code}"
                            else:
                                print(f"[AlertManager] Sensor {sensor['name']} not found in sensors list")
                                continue

                            # Build alerts list
                            alerts = []

                            # Add critical alert (always present)
                            alerts.append({
                                "id": alert_id,
                                "level": "C",
                                "enabled": is_active,
                                "min": crit_min,
                                "max": crit_max
                            })

                            # Add warning alert (if present)
                            if has_warning:
                                alerts.append({
                                    "id": alert_id,
                                    "level": "W",
                                    "enabled": is_active,
                                    "min": warn_min,
                                    "max": warn_max
                                })

                            print(f"[AlertManager] Updating config for {sensor['name']} - {metric}: {alerts}")
                            # Update configuration
                            self._config.set(alerts_path, alerts)
                            break

            self._load_alerts_from_config()

        except Exception as e:
            print(f"[AlertManager] Error updating config: {e}")

    def _separate_index_and_code(self, sensor_key):
        """
        Separate index and code from sensor key like "1TA", "2HA", etc.
        Returns: (index, code)
        """
        if not sensor_key or len(sensor_key) < 2:
            return None, None

        # Extract digits from beginning
        index_str = ''
        code_str = ''

        for i, char in enumerate(sensor_key):
            if char.isdigit():
                index_str += char
            else:
                code_str = sensor_key[i:]
                break

        if index_str and code_str:
            return int(index_str), code_str
        return None, None

    def _load_alerts_from_config(self):
        """Charge les alertes depuis la configuration"""
        self.alert_registry = AlertRegistry()
        sensors_config = self._config.get('sensors', [])

        for sensor_cfg in sensors_config:
            if not sensor_cfg.get('enabled', False):
                continue

            sensor_index = sensor_cfg.get('index', 1)
            alerts = sensor_cfg.get('alerts', {})

            # Parcourir directement les codes dans alerts
            for code, alert_list in alerts.items():
                # Créer l'identifiant complet (ex: "1TA")
                identifier = f"{sensor_index}{code}"

                # Ajouter chaque alerte pour cet identifiant
                for alert in alert_list:
                    if not isinstance(alerts, dict):
                        print(f"[AlertManager] Invalid alerts config for sensor {sensor_cfg.get('name')}")
                        continue
                    if not alert.get('enabled', False):
                        continue

                    level = alert.get('level', 'C')  # C=Critical, W=Warning
                    self.alert_registry.add_alert(identifier, level, {
                        'min': alert.get('min'),
                        'max': alert.get('max'),
                        'id': alert.get('id'),
                        'level': level
                    })

    def on_sensor_data(self, data):
        """
        Callback déclenché quand un capteur publie des données

        Args:
            data: {
                'sensor': 'air',
                'data': {
                    'identifiants': '1TA',  # Identifiant complet
                    'readings': [
                        {'value': 25.3}  # Valeur seule (le code est dans l'identifiant)
                    ]
                }
            }
        """
        print(f"[AlertManager] Received sensor data")
        sensor_name = data.get('sensor')
        sensor_data = data.get('data', {})
        timestamp = data.get('timestamp')  # Timestamp from SensorManager
        # Récupérer l'identifiant complet (ex: "1TA")
        codes = sensor_data.get('codes', {})
        for metric, code in codes.items():
            identifier = f"{sensor_data.get('index')}{code}"
            if not identifier:
                return

            # Récupérer la valeur correspondant au code
            readings = sensor_data.get('readings', [])
            if not readings:
                return

            # Trouver la lecture correspondant au code
            value = None
            for reading in readings:
                if reading.get('code') == code:
                    value = reading.get('value')
                    break
            
            if value is None:
                print(f"[AlertManager] No value found for code {code}")
                continue
            
            # Récupérer les alertes pour cet identifiant
            alerts = self.alert_registry.get(identifier)
            if not alerts:
                print(f"[AlertManager] No alerts configured for {identifier}")
                continue
            
            print(f"[AlertManager] Alerts for {identifier}: {alerts}")

            # Vérifier les seuils
            self._check_thresholds(sensor_name, identifier, value, alerts, timestamp)

    def on_sensor_error(self, data):
        """
        Callback triggered when a sensor read fails.

        Args:
            data: { 'sensor': 'air', 'error': 'Read timeout' }
        """
        sensor_name = data.get('sensor')
        error = data.get('error')
        print(f"[AlertManager] Sensor error on '{sensor_name}': {error}")

    def _check_thresholds(self, sensor_name, identifier, value, alerts, timestamp):
        """
        Vérifie les seuils pour un identifiant donné.
        Priorité : Critical > Warning. Si C est déclenché, W est ignoré.

        Args:
            sensor_name: Nom du capteur
            identifier: Identifiant complet (ex: "1TA")
            value: Valeur mesurée
            alerts: Dict des alertes {"C": {...}, "W": {...}}
        """
        print(f"[AlertManager] Checking thresholds for {identifier}: {value}")
        
        alert_key = f"{sensor_name}.{identifier}"
        triggered_level = None
        triggered_threshold = None

        # Vérifier Critical en premier
        level_map = {'critical': 'C', 'warning': 'W'}
        for key in ['critical', 'warning']:
            threshold = alerts.get(key)
            if not threshold:
                continue
            print(f"[AlertManager] Checking {level_map[key]}: {threshold}")
            if (threshold.get('max') is not None and value > threshold['max']) or \
               (threshold.get('min') is not None and value < threshold['min']):
                triggered_level = level_map[key]
                triggered_threshold = threshold
                print(f"[AlertManager] Threshold {threshold} {level_map[key]} triggered")
                if key == 'critical':
                    break  # Critical trouvé, pas besoin de vérifier Warning

        if triggered_level:
            if alert_key not in self._active_alerts:
                self._active_alerts[alert_key] = {
                    'timestamp': timestamp,
                    'epoch': time.time(),
                    'sensor': sensor_name,
                    'identifier': identifier,
                    'value': value,
                    'threshold': triggered_threshold,
                    'level': triggered_level
                }
                print(f"[AlertManager] ALERT: {sensor_name}/{identifier} = {value} (level: {triggered_level})")
            else:
                self._active_alerts[alert_key]['value'] = value
                self._active_alerts[alert_key]['level'] = triggered_level
                self._active_alerts[alert_key]['threshold'] = triggered_threshold
        else:
            # Value is back to normal → clear alert
            if alert_key in self._active_alerts:
                del self._active_alerts[alert_key]
                if alert_key in self._last_sent_ts:
                    del self._last_sent_ts[alert_key]
                print(f"[AlertManager] Alert cleared: {sensor_name}/{identifier} = {value}")

    def get_alerts_to_send(self):
        """
        Retourne les alertes actives qui n'ont pas été envoyées depuis le timeout.
        Utilise time.time() (epoch seconds) pour la comparaison.
        
        Returns:
            list: Alertes à envoyer
        """
        now = time.time()
        alerts_to_send = []

        for alert_key, alert_data in self._active_alerts.items():
            last_sent = self._last_sent_ts.get(alert_key)

            if last_sent is None:
                # Jamais envoyée → toujours envoyer
                alerts_to_send.append(alert_data)
                self._last_sent_ts[alert_key] = now
                print(f"[AlertManager] Alert {alert_key} ready to send (first time)")
            else:
                elapsed = now - last_sent
                if elapsed >= self.timeout_between_same_alerts:
                    alerts_to_send.append(alert_data)
                    self._last_sent_ts[alert_key] = now
                    print(f"[AlertManager] Alert {alert_key} ready to send (last sent {elapsed}s ago)")
                else:
                    print(f"[AlertManager] Alert {alert_key} skipped (sent {elapsed}s ago, timeout={self.timeout_between_same_alerts}s)")

        return alerts_to_send

    def get_active_alerts(self):
        """Return list of currently active alerts"""
        return list(self._active_alerts.values())

    def has_alerts(self):
        """Check if there are any active alerts"""
        return len(self._active_alerts) > 0