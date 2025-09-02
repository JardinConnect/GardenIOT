from machine import I2C, Pin
import time
from bmp280 import BMP280Sensor

class BMP280Sensor:
    """
    Classe pour gérer le capteur BMP280 de température, pression et altitude
    Nécessite le module bmp280 de MicroPython
    """
    
    def __init__(self, i2c_id=0, sda_pin=20, scl_pin=21, freq=100000, address=0x76):
        """
        Initialise le capteur BMP280
        
        Args:
            i2c_id (int): ID du bus I2C (0 ou 1)
            sda_pin (int): Numéro de la broche GPIO pour SDA
            scl_pin (int): Numéro de la broche GPIO pour SCL
            freq (int): Fréquence I2C en Hz
            address (int): Adresse I2C du capteur (0x76 par défaut, parfois 0x77)
        """
        try:
            # Importer le module bmp280 ici pour gérer l'erreur si non disponible
            
            
            # Initialiser la communication I2C
            self.i2c = I2C(i2c_id, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=freq)
            
            # Vérifier si le capteur est présent
            devices = self.i2c.scan()
            if address not in devices:
                raise RuntimeError(f"BMP280 non trouvé à l'adresse 0x{address:02x}")
            
            # Configurer le capteur BMP280
            self.bmp = bmp280.BMP280(self.i2c, addr=address)
            self.bmp.oversample(bmp280.BMP280_OS_HIGH)
            self.bmp.use_case(bmp280.BMP280_CASE_WEATHER)
            
            # Référence de pression au niveau de la mer (Pa)
            self.sea_level_pressure = 101325.0
            
            print(f"BMP280 initialisé avec succès à l'adresse 0x{address:02x}")
            
        except ImportError:
            print("Module bmp280 non disponible. Installez-le avec 'micropip install bmp280'")
            raise
        except Exception as e:
            print(f"Erreur d'initialisation du BMP280: {e}")
            raise
    
    def read_temperature(self):
        """
        Lit la température en degrés Celsius
        
        Returns:
            float: Température en °C ou None en cas d'erreur
        """
        try:
            return self.bmp.temperature
        except Exception as e:
            print(f"Erreur de lecture de température: {e}")
            return None
    
    def read_pressure(self):
        """
        Lit la pression atmosphérique en Pascals
        
        Returns:
            float: Pression en Pa ou None en cas d'erreur
        """
        try:
            return self.bmp.pressure
        except Exception as e:
            print(f"Erreur de lecture de pression: {e}")
            return None
    
    def set_sea_level_pressure(self, pressure):
        """
        Définit la pression au niveau de la mer pour le calcul d'altitude
        
        Args:
            pressure (float): Pression au niveau de la mer en Pa
        """
        self.sea_level_pressure = pressure
    
    def calculate_altitude(self, pressure=None):
        """
        Calcule l'altitude approximative basée sur la pression atmosphérique
        
        Args:
            pressure (float, optional): Pression en Pa. Si None, utilise la valeur actuelle
            
        Returns:
            float: Altitude approximative en mètres ou None en cas d'erreur
        """
        try:
            if pressure is None:
                pressure = self.read_pressure()
                
            if pressure is None:
                return None
                
            # Formule barométrique pour l'altitude
            altitude = 44330 * (1 - (pressure / self.sea_level_pressure) ** (1/5.255))
            return altitude
        except Exception as e:
            print(f"Erreur de calcul d'altitude: {e}")
            return None
    
    def read_all(self):
        """
        Lit toutes les valeurs du capteur
        
        Returns:
            dict: Dictionnaire contenant température, pression et altitude
        """
        temp = self.read_temperature()
        pressure = self.read_pressure()
        altitude = self.calculate_altitude(pressure) if pressure is not None else None
        
        return {
            "temperature": temp,
            "pressure": pressure,
            "altitude": altitude
        }


# Exemple d'utilisation si ce fichier est exécuté directement
if __name__ == "__main__":
    try:
        # Créer une instance du capteur
        sensor = BMP280Sensor()
        
        print("Mesure des données BMP280...")
        print("Appuyez sur Ctrl+C pour arrêter")
        
        while True:
            # Lire toutes les valeurs
            data = sensor.read_all()
            
            # Afficher les résultats
            print(f"Température: {data['temperature']:.2f} °C")
            print(f"Pression: {data['pressure']:.2f} Pa")
            print(f"Altitude: {data['altitude']:.2f} m")
            print("-" * 30)
            
            # Attendre avant la prochaine lecture
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("Programme arrêté par l'utilisateur")
    except Exception as e:
        print(f"Erreur: {e}")