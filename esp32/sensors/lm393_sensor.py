from machine import Pin, ADC

class SoilMoistureSensor:
    def __init__(self, analog_pin=35, dry_value=3500, wet_value=900):
        """
        Capteur d'humidité du sol LM393 avec sortie analogique (AO).
        
        Args:
            analog_pin (int): GPIO ADC de l'ESP32 (ex: 32, 33, 34, 35)
            dry_value (int): Valeur ADC mesurée quand le sol est sec
            wet_value (int): Valeur ADC mesurée quand le sol est humide
        """
        self.adc = ADC(Pin(analog_pin))
        self.adc.atten(ADC.ATTN_11DB)      # plage 0–3.3V
        self.adc.width(ADC.WIDTH_12BIT)   # 0–4095
        
        self.dry_value = dry_value
        self.wet_value = wet_value

    def read_raw(self):
        """Valeur brute du capteur (0-4095)."""
        return self.adc.read()

    def read_percent(self):
        """Retourne un pourcentage d'humidité entre 0 et 100."""
        raw = self.read_raw()

        # Protection : évite division par zéro
        if self.dry_value == self.wet_value:
            return 0

        # Convertit en pourcentage
        percent = (self.dry_value - raw) / (self.dry_value - self.wet_value) * 100

        # Borne le résultat
        return max(0, min(100, percent))

    def is_wet(self, threshold=50):
        """
        Retourne True si le sol est considéré comme humide.
        """
        return self.read_percent() > threshold
