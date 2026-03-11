class SensorFactory:
    """
    Factory pour instancier des capteurs à partir de leur type.
    Permet d'ajouter de nouveaux capteurs sans modifier le code existant.
    """
    _registry = {}

    @classmethod
    def register(cls, sensor_type, sensor_class):
        """Enregistre un nouveau type de capteur dans la factory"""
        cls._registry[sensor_type.lower()] = sensor_class

    @classmethod
    def create(cls, sensor_type, **kwargs):
        """Crée une instance de capteur à partir de son type"""
        sensor_class = cls._registry.get(sensor_type.lower())
        if not sensor_class:
            raise ValueError(
                f"Unknown sensor type: '{sensor_type}'. "
                f"Available: {list(cls._registry.keys())}"
            )
        return sensor_class(**kwargs)

    @classmethod
    def create_from_config(cls, config):
        """Crée tous les capteurs définis dans la configuration"""
        sensors = []
        for sensor_cfg in config.get('sensors'):
            if not sensor_cfg.get('enabled', True):
                continue  # Skip les capteurs désactivés
    
            try:
                sensor = cls.create(
                    sensor_cfg['type'],
                    name=sensor_cfg.get('name', sensor_cfg['type']),
                    pin=sensor_cfg.get('pin'),
                    **sensor_cfg.get('params', {})
                )
                sensors.append(sensor)
                print(f" Sensor '{sensor.name}' initialized")
            except Exception as e:
                print(f" Failed to create sensor '{sensor_cfg.get('type')}': {e}")
        return sensors