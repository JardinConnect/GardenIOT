import time

class SensorManager:
    """Gestionnaire des capteurs"""
    
    def __init__(self, dht22, ds18b20, lux_sensor, lm393):
        self.dht22 = dht22
        self.ds18b20 = ds18b20
        self.lux = lux_sensor
        self.lm393 = lm393
    
    def lire_all_capteurs(self):
        """
        Lit tous les capteurs et retourne le format standard
        Returns: "1TA23;1TS24;1HA55;1HS100;1L5;1B100"
        """

        t_sol = self._temp_sol()
        
        t_air, h_air = self._dht22()
        
        lux = self._luminosite()
        
        h_sol = self._humidite_sol()
        
        return f"1TA{t_air};1TS{t_sol};1HA{h_air};1HS{h_sol};1L{lux};1B100"
    
    def _temp_sol(self):
        """Température sol (DS18B20)"""
        try:
            temp = self.ds18b20.read_temp()
            return int(round(temp)) if temp else 0
        except:
            return 0
    
    def _dht22(self):
        """Température + Humidité air (DHT22)"""
        for _ in range(3):
            try:
                time.sleep(2) 
                temp = self.dht22.read_temp()
                time.sleep(2)  
                hum = self.dht22.read_humidity()
                
                if temp and hum and -40 <= temp <= 80 and 0 <= hum <= 100:
                    return (int(round(temp)), int(round(hum)))
            except:
                pass
        return (0, 0)
    
    def _luminosite(self):
        """Luminosité convertie en niveau 1-9"""
        try:
            lux = self.lux.read_luminance()
            if not lux:
                return 1
            
            if lux < 10: return 1
            elif lux < 50: return 2
            elif lux < 100: return 3
            elif lux < 200: return 4
            elif lux < 500: return 5
            elif lux < 1000: return 6
            elif lux < 5000: return 7
            elif lux < 10000: return 8
            else: return 9
        except:
            return 1
    
    def _humidite_sol(self):
        """Humidité sol (LM393)"""
        try:
            hum = self.lm393.read_percent()
            return int(round(hum)) if hum else 0
        except:
            return 0