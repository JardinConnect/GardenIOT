"""
Alert Manager - Observer Pattern implementation.
Subscribes to sensor events via EventBus to monitor thresholds.
"""


class AlertManager:
    """
    Observer that monitors sensor thresholds.
    Subscribes to 'sensor.data' events and checks values against config alerts.
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
        
        # Subscribe to sensor events (Observer Pattern)
        self._event_bus.subscribe('sensor.data', self.on_sensor_data)
        self._event_bus.subscribe('sensor.read_error', self.on_sensor_error)
        
        print(f"[AlertManager] Monitoring {len(self._thresholds)} sensors")
    
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
            data: { 'sensor': 'air', 'data': { 'temperature': 35.2, 'humidity': 80 } }
        """
        sensor_name = data.get('sensor')
        readings = data.get('data', {})
        
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
        print(f"[AlertManager] ⚠ Sensor error on '{sensor_name}': {error}")

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
                print(f"[AlertManager] 🚨 ALERT: {sensor}/{metric} = {value} > {max_val}")
                
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
                print(f"[AlertManager] 🚨 ALERT: {sensor}/{metric} = {value} < {min_val}")
                
                # Publish alert event
                self._event_bus.publish('alert.triggered', self._active_alerts[alert_key])
            return
        
        # Value is back to normal → clear alert
        if alert_key in self._active_alerts:
            del self._active_alerts[alert_key]
            print(f"[AlertManager] ✅ Alert cleared: {sensor}/{metric} = {value}")
            
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