from machine import I2C, Pin
import time
from bh1750 import BH1750

class BH1750Sensor:
    """
    Classe pour gérer le capteur BH1750 de luminosité
    """
    
    def __init__(self, i2c_id=0, sda_pin=20, scl_pin=21, freq=400000, address=0x23):
        """
        Initialise le capteur BH1750
        
        Args:
            i2c_id (int): ID du bus I2C (0 ou 1)
            sda_pin (int): Numéro de la broche GPIO pour SDA
            scl_pin (int): Numéro de la broche GPIO pour SCL
            freq (int): Fréquence I2C en Hz
            address (int): Adresse I2C du capteur (0x23 par défaut, 0x5C si ADDR est connecté à VCC)
        """
        try:
            # Initialiser la communication I2C
            self.i2c = I2C(i2c_id, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=freq)
            # self.i2c = SoftI2C(scl=Pin(5), sda=Pin(4), freq=400000)

            
            # Vérifier si le capteur est présent
            devices = self.i2c.scan()
            if address not in devices:
                raise RuntimeError(f"BH1750 non trouvé à l'adresse 0x{address:02x}")
            
            # Configurer le capteur BH1750
            self.sensor = BH1750(bus=self.i2c, addr=address)
            
            # Mode de mesure par défaut
            self.mode = BH1750.CONT_HIRES_1
            
            print(f"BH1750 initialisé avec succès à l'adresse 0x{address:02x}")
            
        except Exception as e:
            print(f"Erreur d'initialisation du BH1750: {e}")
            raise
    
    def read_luminance(self, mode=None):
        """
        Lit la luminosité en lux
        
        Args:
            mode (int, optional): Mode de mesure. Si None, utilise le mode par défaut
            
        Returns:
            float: Luminosité en lux ou None en cas d'erreur
        """
        try:
            if mode is None:
                mode = self.mode
                
            return self.sensor.luminance(mode)
        except Exception as e:
            print(f"Erreur de lecture de luminosité: {e}")
            return None
    
    def set_mode(self, mode):
        """
        Définit le mode de mesure du capteur
        
        Args:
            mode: Mode de mesure (voir les constantes BH1750.CONT_*)
            
        Returns:
            bool: True si le changement a réussi, False sinon
        """
        try:
            self.mode = mode
            self.sensor.set_mode(mode)
            return True
        except Exception as e:
            print(f"Erreur de changement de mode: {e}")
            return False
    
    def power_on(self):
        """
        Allume le capteur
        
        Returns:
            bool: True si l'opération a réussi, False sinon
        """
        try:
            self.sensor.on()
            return True
        except Exception as e:
            print(f"Erreur lors de l'allumage du capteur: {e}")
            return False
    
    def power_off(self):
        """
        Éteint le capteur
        
        Returns:
            bool: True si l'opération a réussi, False sinon
        """
        try:
            self.sensor.off()
            return True
        except Exception as e:
            print(f"Erreur lors de l'extinction du capteur: {e}")
            return False
    
    def reset(self):
        """
        Réinitialise le capteur
        
        Returns:
            bool: True si l'opération a réussi, False sinon
        """
        try:
            self.sensor.reset()
            return True
        except Exception as e:
            print(f"Erreur lors de la réinitialisation du capteur: {e}")
            return False


# Exemple d'utilisation si ce fichier est exécuté directement
if __name__ == "__main__":
    try:
        # Créer une instance du capteur
        sensor = BH1750Sensor(0, 20, 21)
        
        print("Mesure de la luminosité...")
        print("Appuyez sur Ctrl+C pour arrêter")
        
        # Tester différents modes
        print("\nMode haute résolution (1 lux):")
        sensor.set_mode(BH1750.CONT_HIRES_1)
        
        while True:
            # Lire la luminosité
            lux = sensor.read_luminance()
            
            # Afficher le résultat
            print(f"Luminosité: {lux:.2f} lux")
            
            # Attendre avant la prochaine lecture
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nProgramme arrêté par l'utilisateur")
    except Exception as e:
        print(f"Erreur: {e}")