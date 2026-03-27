class AlertRegistry:
    """Registry for managing sensor alerts with easy access by threshold key"""

    def __init__(self):
        self._alerts = {}  # Format: {"1TA": {"C": {...}, "W": {...}}}

    def add_alert(self, threshold_key, level, alert_data):
        """Add an alert to the registry"""
        if threshold_key not in self._alerts:
            self._alerts[threshold_key] = {}

        self._alerts[threshold_key][level] = alert_data

    def get(self, threshold_key):
        """
        Get both critical and warning alerts for a threshold key
        Returns: dict with 'critical' and 'warning' keys, or None if not found
        """
        if threshold_key not in self._alerts:
            return None

        alerts = self._alerts[threshold_key]
        return {
            'critical': alerts.get('C'),
            'warning': alerts.get('W')
        }

    def get_all(self):
        """Get all alerts in the registry"""
        return self._alerts

    def clear(self):
        """Clear all alerts"""
        self._alerts.clear()