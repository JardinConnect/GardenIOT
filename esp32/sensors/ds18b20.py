from machine import Pin
import onewire
import ds18x20
import time

class DS18B20Sensor:
    def __init__(self, pin):
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
            print(" Aucun capteur détecté - vérifie ton câblage et la résistance pull-up.")
    
    def get_device_count(self):
        """Retourne le nombre de capteurs DS18B20 détectés"""
        return len(self.roms)
    
    def read_temps(self):
        """
        Lit la température de tous les capteurs DS18B20 connectés.
        Returns:
            list[float]: Liste des températures en degrés Celsius.
        """
        if not self.roms:
            print(" Aucun capteur trouvé.")
            return []
        
        # Conversion de température (attendre que le capteur mesure)
        self.ds.convert_temp()
        time.sleep_ms(750)
        
        # Lecture de chaque capteur
        return [self.ds.read_temp(rom) for rom in self.roms]
    
    def read_temp(self, index=0):
        """
        Lit la température d'un capteur DS18B20 spécifique.
        Args:
            index (int): Index du capteur (par défaut: 0)
        Returns:
            float: Température en °C ou None si invalide
        """
        if not self.roms or index >= len(self.roms):
            print(" Aucun capteur ou index invalide.")
            return None
        
        self.ds.convert_temp()
        time.sleep_ms(750)
        return self.ds.read_temp(self.roms[index])


# Exemple d'utilisation
if __name__ == "__main__":
    sensor = DS18B20Sensor(pin=4)  # GPIO 4 (celui que tu utilises)
    print(f"Nombre de capteurs détectés : {sensor.get_device_count()}")
    
    while True:
        temps = sensor.read_temps()
        if temps:
            for i, t in enumerate(temps):
                print(f"Capteur {i+1} : {t:.2f} °C")
        else:
            print("Aucune donnée de température.")
        time.sleep(2)
