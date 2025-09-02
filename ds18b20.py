from machine import Pin
import onewire
import time
import ds18x20

class DS18B20Sensor:
    def __init__(self, pin=12):
        """
        Initialise le capteur DS18B20 sur la broche spécifiée
        
        Args:
            pin (int): Numéro de la broche GPIO à utiliser (par défaut: 12)
        """
        # Initialiser le bus OneWire sur la broche GPIO spécifiée
        self.ow = onewire.OneWire(Pin(pin))
        
        # Créer une instance DS18X20 en utilisant le bus OneWire
        self.ds = ds18x20.DS18X20(self.ow)
        
        # Rechercher les appareils DS18X20 sur le bus
        self.roms = self.ds.scan()
        
    def get_device_count(self):
        """
        Retourne le nombre de capteurs DS18B20 détectés
        
        Returns:
            int: Nombre de capteurs trouvés
        """
        return len(self.roms)
    
    def read_temps(self):
        """
        Lit la température de tous les capteurs DS18B20 connectés
        
        Returns:
            list: Liste des températures en degrés Celsius
        """
        # Démarrer le processus de conversion de température
        self.ds.convert_temp()
        
        # Attendre la fin de la conversion (750 ms pour DS18X20)
        time.sleep_ms(750)
        
        # Lire la température de chaque capteur trouvé sur le bus
        temps = []
        for rom in self.roms:
            temps.append(self.ds.read_temp(rom))
        
        return temps
    
    def read_temp(self, index=0):
        """
        Lit la température d'un capteur DS18B20 spécifique
        
        Args:
            index (int): Index du capteur à lire (par défaut: 0)
            
        Returns:
            float: Température en degrés Celsius ou None si l'index est invalide
        """
        if not self.roms or index >= len(self.roms):
            return None
            
        # Démarrer le processus de conversion de température
        self.ds.convert_temp()
        
        # Attendre la fin de la conversion (750 ms pour DS18X20)
        time.sleep_ms(750)
        
        # Lire et retourner la température du capteur spécifié
        return self.ds.read_temp(self.roms[index])

# Exemple d'utilisation si ce fichier est exécuté directement
if __name__ == "__main__":
    sensor = DS18B20Sensor(pin=12)
    print(f'Capteurs trouvés: {sensor.get_device_count()}')
    
    while True:
        temps = sensor.read_temps()
        print(f'Températures: {temps}')
        time.sleep_ms(2000)