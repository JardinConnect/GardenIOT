from sensors.base_sensor import BaseSensor
from machine import Pin
import onewire
import ds18x20
import time

class DS18B20Sensor(BaseSensor):
    def __init__(self, name="ds18b20", pin=14, **kwargs):
        super().__init__(name=name, pin=pin, **kwargs)
        """
        Initialise le capteur DS18B20 sur la broche spécifiée
        
        Args:
            pin (int): Numéro du GPIO à utiliser (par défaut: 4)
        """
        # Initialisation du bus OneWire sur la broche GPIO spécifiée
        self.ow = onewire.OneWire(Pin(pin))
        # Création de l'instance DS18X20 avec ce bus
        self.ds = ds18x20.DS18X20(self.ow)
        # Recherche des capteurs DS18B20 connectés
        self.roms = self.ds.scan()
        self.init_hardware()

    def _check_hardware(self):
        return len(self.roms) > 0

    def _read_raw(self):
        if not self.roms:
            print("No DS18B20 sensors found, cannot read temperature.")
            return None
        
        try:
            # Conversion de température (attendre que le capteur mesure)
            self.ds.convert_temp()
            time.sleep_ms(750)
            
            # Lecture de chaque capteur
            return {'TS': self.ds.read_temp(self.roms[0])}  # Lit le premier capteur trouvé
        except Exception as e:
            print(f"  [{self.name}] DS18B20 read failed: {e}")
            return None
    
    def _validate(self, data):
        if data is None:
            return False
            
        temp = data.get('TS')
        return temp is not None and -55 <= temp <= 125  # Plage valide pour DS18B20
    
    def _read_raws(self):
        if not self.roms:
            print("No DS18B20 sensors found, cannot read temperature.")
            return None        
        self.ds.convert_temp()
        time.sleep_ms(750)
        return {'TS': self.ds.read_temp(rom) for rom in self.roms}  # Lit tous les capteurs et retourne un dict {rom: temp}