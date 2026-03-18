"""
Alert Manager - Observer Pattern implementation.
Subscribes to sensor events via EventBus to monitor thresholds.
"""

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

        # Build thresholds from sensor config
        # config.json has alerts PER sensor:
        # sensors[].alerts = { "temperature": { "min": 0, "max": 45 } }
        self._thresholds = self._build_thresholds()

        # Subscribe to events (Observer Pattern)
        self._event_bus.subscribe('message.received', self.handle_incoming_message)
        self._event_bus.subscribe('sensor.data', self.on_sensor_data)
        self._event_bus.subscribe('sensor.read_error', self.on_sensor_error)

        print(f"[AlertManager] Monitoring {len(self._thresholds)} sensors")

    def handle_incoming_message(self, message):
        """Handle incoming messages from EventBus"""
        if not message:
            return

        msg_type = message.get('type')
        print(f"[AlertManager] Message received: type={msg_type}")

        # Only process alert config messages (type 'A')
        if msg_type == 'A':
            self.handle_config_message(message)

    def handle_config_message(self, message):
        """Process alert configuration messages from LoRa"""
        try:
            # Extract message data
            datas = message.get('datas', '')
            if not datas:
                print("[AlertManager] No data in message")
                return

            print(f"[AlertManager] Alert config received: {datas}")
            # Parse LoRa format
            parts = datas.split(':')
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

                # Format: INDEXCODE,CRIT_MIN,CRIT_MAX[,WARN_MIN,WARN_MAX]
                parts = config.split(',')
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
                                alerts_path = f"sensors.{sensor_index}.alerts.{metric}"
                            else:
                                print(f"[AlertManager] Sensor {sensor['name']} not found in sensors list")
                                continue

                            # Build alerts list
                            alerts = []

                            # Add critical alert (always present)
                            alerts.append({
                                "id": alert_id,
                                "isActive": is_active,
                                "level": "C",
                                "enabled": is_active,
                                "min": crit_min,
                                "max": crit_max
                            })

                            # Add warning alert (if present)
                            if has_warning:
                                alerts.append({
                                    "id": alert_id,
                                    "isActive": is_active,
                                    "level": "W",
                                    "enabled": is_active,
                                    "min": warn_min,
                                    "max": warn_max
                                })

                            print(f"[AlertManager] Updating config for {sensor['name']} - {metric}: {alerts}")
                            # Update configuration
                            self._config.set(alerts_path, alerts)
                            break

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

    def _build_thresholds(self):
        """
        Build thresholds dict from sensors config.

        config.json structure:
            sensors[]: { "name": "air", "alerts": { "temperature": { "min": 0, "max": 45 } } }

        Returns:
            dict: { "air": { "temperature": { "min": 0, "max": 45 }, ... }, ... }
        """
        thresholds = {}
        sensors_config = self._config.get('sensors', [])

        for sensor_cfg in sensors_config:
            if not sensor_cfg.get('enabled', False):
                continue

            alerts = sensor_cfg.get('alerts', {})
            if alerts:
                thresholds[sensor_cfg['name']] = alerts

        return thresholds

    def on_sensor_data(self, data):
        """
        Callback triggered when a sensor publishes data via EventBus.

        Args:
            data: { 'sensor': 'air', 'data': SensorData.to_dict() }
        """
        sensor_name = data.get('sensor')
        sensor_data = data.get('data', {})

        # Extract readings from DTO format
        readings = {}
        for reading in sensor_data.get('readings', []):
            readings[reading['metric']] = reading['value']

        # Get thresholds for this sensor
        sensor_thresholds = self._thresholds.get(sensor_name, {})

        if not sensor_thresholds:
            return

        for metric, value in readings.items():
            threshold = sensor_thresholds.get(metric)
            if threshold:
                self._check_threshold(sensor_name, metric, value, threshold)

    def on_sensor_error(self, data):
        """
        Callback triggered when a sensor read fails.

        Args:
            data: { 'sensor': 'air', 'error': 'Read timeout' }
        """
        sensor_name = data.get('sensor')
        error = data.get('error')
        print(f"[AlertManager] Sensor error on '{sensor_name}': {error}")

    def _check_threshold(self, sensor, metric, value, threshold):
        """
        Check if a value exceeds its threshold.

        Args:
            sensor: sensor name
            metric: metric name (e.g., 'temperature')
            value: current value
            threshold: { 'min': ..., 'max': ... }
        """
        alert_key = f"{sensor}.{metric}"

        max_val = threshold.get('max')
        min_val = threshold.get('min')

        # Check max threshold
        if max_val is not None and value > max_val:
            if alert_key not in self._active_alerts:
                self._active_alerts[alert_key] = {
                    'sensor': sensor,
                    'metric': metric,
                    'value': value,
                    'threshold': f"max={max_val}",
                    'type': 'high'
                }
                print(f"[AlertManager] ALERT: {sensor}/{metric} = {value} > {max_val}")

                # Publish alert event
                self._event_bus.publish('alert.triggered', self._active_alerts[alert_key])
            return

        # Check min threshold
        if min_val is not None and value < min_val:
            if alert_key not in self._active_alerts:
                self._active_alerts[alert_key] = {
                    'sensor': sensor,
                    'metric': metric,
                    'value': value,
                    'threshold': f"min={min_val}",
                    'type': 'low'
                }
                print(f"[AlertManager] ALERT: {sensor}/{metric} = {value} < {min_val}")

                # Publish alert event
                self._event_bus.publish('alert.triggered', self._active_alerts[alert_key])
            return

        # Value is back to normal → clear alert
        if alert_key in self._active_alerts:
            del self._active_alerts[alert_key]
            print(f"[AlertManager] Alert cleared: {sensor}/{metric} = {value}")

            self._event_bus.publish('alert.cleared', {
                'sensor': sensor,
                'metric': metric,
                'value': value
            })

    def get_active_alerts(self):
        """Return list of currently active alerts"""
        return list(self._active_alerts.values())

    def has_alerts(self):
        """Check if there are any active alerts"""
        return len(self._active_alerts) > 0