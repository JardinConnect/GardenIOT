from machine import Pin
import onewire
import time
import ds18x20

class DS18B20Sensor:
    """
    Classe pour interfacer le capteur de température DS18B20
    avec un Raspberry Pi Pico 2 W via OneWire
    """
    
    def __init__(self, data_pin=3, use_percent=False):
        """
        Initialise le capteur DS18B20 sur la broche spécifiée
        
        Args:
            data_pin (int): Numéro de la broche GPIO à utiliser (par défaut: 3)
            use_percent (bool): Utiliser des pourcentages au lieu de degrés (par défaut: False)
        """
        # Configurer le bus OneWire
        self.ow = onewire.OneWire(Pin(data_pin))
        
        # Créer une instance DS18X20
        self.ds = ds18x20.DS18X20(self.ow)
        
        # Rechercher les appareils DS18X20 sur le bus
        self.roms = self.ds.scan()
        
        # Paramètres pour la conversion des valeurs (comme les autres capteurs)
        self.min_temp = -10.0    # Température minimale de référence
        self.max_temp = 50.0     # Température maximale de référence
        self.use_percent = use_percent
        
        # Vérifier si des capteurs sont trouvés
        if not self.roms:
            raise RuntimeError("Aucun capteur DS18B20 trouvé sur le bus OneWire")
        
        print(f"DS18B20 trouvé: {len(self.roms)} capteur(s)")
    
    def calibrate(self, min_temp, max_temp):
        """
        Calibre le capteur avec des valeurs de référence
        
        Args:
            min_temp (float): Température minimale de référence
            max_temp (float): Température maximale de référence
        """
        self.min_temp = min_temp
        self.max_temp = max_temp
    
    def get_device_count(self):
        """
        Retourne le nombre de capteurs DS18B20 détectés
        
        Returns:
            int: Nombre de capteurs trouvés
        """
        return len(self.roms)
    
    def read_raw(self):
        """
        Lit la valeur brute du capteur (première ROM trouvée)
        
        Returns:
            float: Température brute en degrés Celsius ou None en cas d'erreur
        """
        if not self.roms:
            return None
            
        try:
            # Démarrer le processus de conversion de température
            self.ds.convert_temp()
            
            # Attendre la fin de la conversion (750 ms pour DS18X20)
            time.sleep_ms(750)
            
            # Lire la température du premier capteur
            temp = self.ds.read_temp(self.roms[0])
            return temp
            
        except Exception as e:
            print(f"Erreur lecture DS18B20: {e}")
            return None
    
    def read_temp(self):
        """
        Lit la température en degrés Celsius
        
        Returns:
            float: Température en °C ou None en cas d'erreur
        """
        temp = self.read_raw()
        return {"TS": temp}
    
    def read_all_temperatures(self):
        """
        Lit la température de tous les capteurs DS18B20 connectés
        
        Returns:
            list: Liste de tuples (index, température) pour chaque capteur
        """
        try:
            # Démarrer le processus de conversion de température
            self.ds.convert_temp()
            
            # Attendre la fin de la conversion
            time.sleep_ms(750)
            
            # Lire la température de chaque capteur
            temps = []
            for i, rom in enumerate(self.roms):
                try:
                    temp = self.ds.read_temp(rom)
                    temps.append((i, temp))
                except:
                    temps.append((i, None))
            
            return temps
            
        except Exception as e:
            print(f"Erreur lecture multiple: {e}")
            return [(i, None) for i in range(len(self.roms))]
    
    def read_temperature_by_index(self, index=0):
        """
        Lit la température d'un capteur DS18B20 spécifique
        
        Args:
            index (int): Index du capteur à lire (par défaut: 0)
            
        Returns:
            float: Température en degrés Celsius ou None si l'index est invalide
        """
        if not self.roms or index >= len(self.roms):
            return None
            
        try:
            # Démarrer le processus de conversion de température
            self.ds.convert_temp()
            
            # Attendre la fin de la conversion
            time.sleep_ms(750)
            
            # Lire et retourner la température du capteur spécifié
            return self.ds.read_temp(self.roms[index])
            
        except Exception as e:
            print(f"Erreur lecture capteur {index}: {e}")
            return None
    
    def get_temperature_description(self, temp_value=None):
        """
        Retourne une description textuelle de la température
        
        Args:
            temp_value (float): Valeur de température (si None, lit automatiquement)
            
        Returns:
            str: Description de la température
        """
        if temp_value is None:
            temp_value = self.read_temperature()
        
        if temp_value is None:
            return "Erreur de lecture"
        
        if temp_value < 0:
            return "Très froid"
        elif temp_value < 10:
            return "Froid"
        elif temp_value < 20:
            return "Frais"
        elif temp_value < 25:
            return "Température ambiante"
        elif temp_value < 30:
            return "Chaud"
        else:
            return "Très chaud"
    
    def get_rom_addresses(self):
        """
        Retourne les adresses ROM de tous les capteurs détectés
        
        Returns:
            list: Liste des adresses ROM en format hexadécimal
        """
        return [':'.join(['%02x' % b for b in rom]) for rom in self.roms]

# Exemple d'utilisation si ce fichier est exécuté directement
if __name__ == "__main__":
    # Créer une instance du capteur sur GP3
    sensor = DS18B20Sensor(data_pin=3)
    
    # Calibration optionnelle (à faire selon votre plage de mesure)
    # sensor.calibrate(min_temp=0, max_temp=40)
    
    print("Mesure de la température DS18B20...")
    print("Appuyez sur Ctrl+C pour arrêter")
    
    try:
        count = 0
        while True:
            count += 1
            
            # Lecture de base
            temp = sensor.read_temperature()
            
            if temp is not None:
                print(f"Température: {temp:.2f} °C")
                
                # Si plusieurs capteurs
                if sensor.get_device_count() > 1:
                    all_temps = sensor.read_all_temperatures()
                    print(f"Toutes les températures: {all_temps}")
            else:
                print("Erreur de lecture du capteur")
            
            print("-" * 30)
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("Programme arrêté par l'utilisateur")
        print(f"Adresses ROM détectées: {sensor.get_rom_addresses()}")