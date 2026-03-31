import time
from machine import ADC, Pin

class SensorManager:
    """Gestionnaire des capteurs"""
    
    def __init__(self, dht22, ds18b20, lux_sensor, lm393, lm393_2, battery_pin=32):
        self.dht22 = dht22
        self.ds18b20 = ds18b20
        self.lux = lux_sensor
        self.lm393 = lm393
        self.lm393_2 = lm393_2
        
        self.batt_adc = ADC(Pin(battery_pin))
        self.batt_adc.atten(ADC.ATTN_11DB)
        self.batt_adc.width(ADC.WIDTH_12BIT)     
    
    def lire_all_capteurs(self):
        """
        Lit tous les capteurs et retourne le format standard
        Returns: "1TA23;1TS24;1HA55;1HS100;2HS80;1L5;1B45"
        """
        t_sol = self._temp_sol()
        t_air, h_air = self._dht22()
        lux = self._luminosite()
        h_sol = self._humidite_sol(self.lm393)
        h_sol_2 = self._humidite_sol(self.lm393_2)
        batterie = self._niveau_batterie()
        
        return f"1TA{t_air};1TS{t_sol};1HA{h_air};1HS{h_sol};2HS{h_sol_2};1L{lux};1B{batterie}"
    
    def _niveau_batterie(self):
        """Calcule le pourcentage de batterie sur GPIO 34"""
        try:
            valeur_brute = self.batt_adc.read()
            if valeur_brute == 0: return 0
            
            tension_batterie = (valeur_brute / 4095) * 3.54 * 2
            
            pourcentage = (tension_batterie - 3.2) / (4.2 - 3.2) * 100
            
            return int(max(0, min(100, pourcentage)))
        except:
            return 0

    def _temp_sol(self):
        """Température sol (DS18B20)"""
        try:
            temp = self.ds18b20.read_temp()
            return int(round(temp)) if temp else 0
        except:
            return 0
    
    def _dht22(self):
        for _ in range(3):
            time.sleep(1)
            temp, hum = self.dht22.read_all()
            if temp is not None and hum is not None and -40 <= temp <= 80 and 0 <= hum <= 100:
                return (int(round(temp)), int(round(hum)))
        return (0, 0)
    
    def _luminosite(self):
        try:
            valeur_lux = self.lux.read_luminance()
            return int(round(valeur_lux)) if valeur_lux is not None else 0
        except:
            return 0
    
    def _humidite_sol(self, capteur):
        if capteur is None:
            return 0
        try:
            hum = capteur.read_percent()
            return int(round(hum)) if hum else 0
        except:
            return 0