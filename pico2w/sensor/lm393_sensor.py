from machine import Pin, ADC
import time

class LM393Sensor:
    def __init__(self, analog_pin=26, digital_pin=16, use_digital=False):
        """
        Initialise le capteur d'humidité du sol LM393
        
        Args:
            analog_pin (int): Numéro de la broche GPIO ADC à utiliser (par défaut: 26 - ADC0)
            digital_pin (int): Numéro de la broche GPIO pour la sortie numérique (par défaut: 16)
            use_digital (bool): Utiliser la sortie numérique au lieu de l'analogique (par défaut: False)
        """
        # Configurer la broche analogique (ADC)
        self.adc = ADC(Pin(analog_pin))
        
        # Configurer la broche numérique (optionnelle)
        self.digital_pin = Pin(digital_pin, Pin.IN) if use_digital else None
        
        # Paramètres pour la conversion des valeurs
        self.dry_value = 65535  # Valeur ADC pour sol sec (à calibrer)
        self.wet_value = 30000  # Valeur ADC pour sol humide (à calibrer)
        self.use_digital = use_digital
    
    def calibrate(self, dry_value, wet_value):
        """
        Calibre le capteur avec des valeurs de référence
        
        Args:
            dry_value (int): Valeur ADC pour un sol sec
            wet_value (int): Valeur ADC pour un sol humide
        """
        self.dry_value = dry_value
        self.wet_value = wet_value
    
    def read_raw(self):
        """
        Lit la valeur brute du capteur
        
        Returns:
            int: Valeur brute du capteur (0-65535)
        """
        return self.adc.read_u16()

    def read_percent(self):
        """
        Lit l'humidité du sol en pourcentage
        
        Returns:
            float: Pourcentage d'humidité (0-100%)
        """
        raw = self.read_raw()
        
        # Protection contre division par zéro
        if self.dry_value <= self.wet_value:
            return 0
            
        # Calculer le pourcentage (0-100%)
        # La valeur brute diminue quand l'humidité augmente
        percent = ((self.dry_value - raw) / (self.dry_value - self.wet_value)) * 100
        
        # Limiter entre 0 et 100%
        return max(0, min(100, percent))

    def read_humidity(self):
        return {"HS": self.read_percent()}

# Exemple d'utilisation si ce fichier est exécuté directement
if __name__ == "__main__":
    # Créer une instance du capteur sur la broche ADC0 (GPIO 26)
    sensor = LM393Sensor(analog_pin=26)
    
    # Calibration optionnelle (à faire avec le capteur dans l'air puis dans l'eau)
    # sensor.calibrate(dry_value=65000, wet_value=20000)
    
    print("Mesure de l'humidité du sol...")
    print("Appuyez sur Ctrl+C pour arrêter")
    
    try:
        while True:
            raw = sensor.read_raw()
            percent = sensor.read_percent()
            
            print(f"Valeur brute: {raw}")
            print(f"Humidité: {percent:.1f}%")
            print("-" * 20)
            
            time.sleep(2)
    except KeyboardInterrupt:
        print("Programme arrêté par l'utilisateur")