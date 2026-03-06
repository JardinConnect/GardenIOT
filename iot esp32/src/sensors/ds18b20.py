from sensors.base_sensor import BaseSensor
from machine import Pin
import onewire
import ds18x20
import time

class DS18B20Sensor(BaseSensor):
    def __init__(self, name="ds18b20", pin=4, **kwargs):
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
        
        if not self.roms:
            print("No DS18B20 sensors found on pin {}".format(pin))
    
    def _read_raw(self):
        if not self.roms:
            print("No DS18B20 sensors found, cannot read temperature.")
            return []
        
        # Conversion de température (attendre que le capteur mesure)
        self.ds.convert_temp()
        time.sleep_ms(750)
        
        # Lecture de chaque capteur
        return {'temperature': self.ds.read_temp(0)}  # Lit le premier capteur trouvé (index 0)
    
    def _read_raws(self):
        if not self.roms:
            print("No DS18B20 sensors found, cannot read temperature.")
            return None        
        self.ds.convert_temp()
        time.sleep_ms(750)
        return {'temperature' + str(rom): self.ds.read_temp(rom) for rom in self.roms}  # Lit tous les capteurs et retourne un dict {rom: temp}