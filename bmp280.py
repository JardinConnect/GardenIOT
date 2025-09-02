from machine import I2C, Pin
import time
import struct
import math

# Constantes pour les registres BMP280
BMP280_REG_DIG_T1 = 0x88
BMP280_REG_DIG_T2 = 0x8A
BMP280_REG_DIG_T3 = 0x8C
BMP280_REG_DIG_P1 = 0x8E
BMP280_REG_DIG_P2 = 0x90
BMP280_REG_DIG_P3 = 0x92
BMP280_REG_DIG_P4 = 0x94
BMP280_REG_DIG_P5 = 0x96
BMP280_REG_DIG_P6 = 0x98
BMP280_REG_DIG_P7 = 0x9A
BMP280_REG_DIG_P8 = 0x9C
BMP280_REG_DIG_P9 = 0x9E
BMP280_REG_CHIPID = 0xD0
BMP280_REG_RESET = 0xE0
BMP280_REG_STATUS = 0xF3
BMP280_REG_CTRL_MEAS = 0xF4
BMP280_REG_CONFIG = 0xF5
BMP280_REG_TEMP_DATA = 0xFA
BMP280_REG_PRESS_DATA = 0xF7

# Constantes pour les modes
BMP280_CHIPID = 0x58
BMP280_RESET_VALUE = 0xB6

# Modes de puissance
BMP280_SLEEP_MODE = 0x00
BMP280_FORCED_MODE = 0x01
BMP280_NORMAL_MODE = 0x03

# Oversampling
BMP280_OS_NONE = 0x00
BMP280_OS_1X = 0x01
BMP280_OS_2X = 0x02
BMP280_OS_4X = 0x03
BMP280_OS_8X = 0x04
BMP280_OS_16X = 0x05

# Filtres
BMP280_FILTER_OFF = 0x00
BMP280_FILTER_2 = 0x01
BMP280_FILTER_4 = 0x02
BMP280_FILTER_8 = 0x03
BMP280_FILTER_16 = 0x04

# Standby
BMP280_STANDBY_0_5 = 0x00
BMP280_STANDBY_62_5 = 0x01
BMP280_STANDBY_125 = 0x02
BMP280_STANDBY_250 = 0x03
BMP280_STANDBY_500 = 0x04
BMP280_STANDBY_1000 = 0x05
BMP280_STANDBY_2000 = 0x06
BMP280_STANDBY_4000 = 0x07

# Cas d'utilisation prédéfinis
BMP280_CASE_HANDHELD_LOW = 0x00
BMP280_CASE_HANDHELD_DYN = 0x01
BMP280_CASE_WEATHER = 0x02
BMP280_CASE_FLOOR = 0x03
BMP280_CASE_DROP = 0x04
BMP280_CASE_INDOOR = 0x05

class BMP280:
    """
    Classe de base pour le capteur BMP280
    Gère la communication I2C et les calculs de température et pression
    """
    
    def __init__(self, i2c_bus, addr=0x76):
        """
        Initialise le capteur BMP280
        
        Args:
            i2c_bus: Bus I2C à utiliser
            addr: Adresse I2C du capteur (0x76 par défaut, parfois 0x77)
        """
        self._i2c = i2c_bus
        self._addr = addr
        
        # Vérifier l'ID du capteur
        chip_id = self._read_byte(BMP280_REG_CHIPID)
        if chip_id != BMP280_CHIPID:
            raise RuntimeError(f"BMP280 non détecté, ID incorrect: 0x{chip_id:02x}")
        
        # Lire les coefficients de calibration
        self._read_coefficients()
        
        # Configuration par défaut
        self.oversample_temp = BMP280_OS_4X
        self.oversample_pres = BMP280_OS_4X
        self.mode = BMP280_NORMAL_MODE
        self.filter = BMP280_FILTER_8
        self.standby = BMP280_STANDBY_500
        
        # Appliquer la configuration
        self._write_config()
        
        # Variables pour les calculs
        self._t_fine = 0
        self._temperature = 0
        self._pressure = 0
    
    def _read_byte(self, reg):
        """Lit un octet depuis un registre"""
        return self._i2c.readfrom_mem(self._addr, reg, 1)[0]
    
    def _read_word(self, reg):
        """Lit un mot (2 octets) depuis un registre"""
        data = self._i2c.readfrom_mem(self._addr, reg, 2)
        return data[0] | (data[1] << 8)
    
    def _read_signed_word(self, reg):
        """Lit un mot signé depuis un registre"""
        val = self._read_word(reg)
        if val >= 0x8000:
            return val - 0x10000
        return val
    
    def _write_byte(self, reg, value):
        """Écrit un octet dans un registre"""
        self._i2c.writeto_mem(self._addr, reg, bytes([value]))
    
    def _read_coefficients(self):
        """Lit les coefficients de calibration du capteur"""
        self.dig_T1 = self._read_word(BMP280_REG_DIG_T1)
        self.dig_T2 = self._read_signed_word(BMP280_REG_DIG_T2)
        self.dig_T3 = self._read_signed_word(BMP280_REG_DIG_T3)
        
        self.dig_P1 = self._read_word(BMP280_REG_DIG_P1)
        self.dig_P2 = self._read_signed_word(BMP280_REG_DIG_P2)
        self.dig_P3 = self._read_signed_word(BMP280_REG_DIG_P3)
        self.dig_P4 = self._read_signed_word(BMP280_REG_DIG_P4)
        self.dig_P5 = self._read_signed_word(BMP280_REG_DIG_P5)
        self.dig_P6 = self._read_signed_word(BMP280_REG_DIG_P6)
        self.dig_P7 = self._read_signed_word(BMP280_REG_DIG_P7)
        self.dig_P8 = self._read_signed_word(BMP280_REG_DIG_P8)
        self.dig_P9 = self._read_signed_word(BMP280_REG_DIG_P9)
    
    def _write_config(self):
        """Applique la configuration au capteur"""
        # Mode et oversampling
        ctrl_meas = (self.oversample_temp << 5) | (self.oversample_pres << 2) | self.mode
        self._write_byte(BMP280_REG_CTRL_MEAS, ctrl_meas)
        
        # Filtre et standby
        config = (self.standby << 5) | (self.filter << 2)
        self._write_byte(BMP280_REG_CONFIG, config)
    
    def reset(self):
        """Réinitialise le capteur"""
        self._write_byte(BMP280_REG_RESET, BMP280_RESET_VALUE)
        time.sleep(0.2)  # Attendre la réinitialisation
        self._read_coefficients()
        self._write_config()
    
    def _calc_t_fine(self):
        """Calcule t_fine et la température"""
        # Lire les données brutes de température
        data = self._i2c.readfrom_mem(self._addr, BMP280_REG_TEMP_DATA, 3)
        raw_temp = (data[0] << 16 | data[1] << 8 | data[2]) >> 4
        
        # Calcul selon la datasheet
        var1 = ((raw_temp >> 3) - (self.dig_T1 << 1)) * self.dig_T2 >> 11
        var2 = (((((raw_temp >> 4) - self.dig_T1) * ((raw_temp >> 4) - self.dig_T1)) >> 12) * self.dig_T3) >> 14
        
        self._t_fine = var1 + var2
        self._temperature = ((self._t_fine * 5 + 128) >> 8) / 100.0
    
    def _calc_pressure(self):
        """Calcule la pression"""
        # Lire les données brutes de pression
        data = self._i2c.readfrom_mem(self._addr, BMP280_REG_PRESS_DATA, 3)
        raw_press = (data[0] << 16 | data[1] << 8 | data[2]) >> 4
        
        # Calcul selon la datasheet
        var1 = self._t_fine - 128000
        var2 = var1 * var1 * self.dig_P6
        var2 = var2 + ((var1 * self.dig_P5) << 17)
        var2 = var2 + (self.dig_P4 << 35)
        var1 = ((var1 * var1 * self.dig_P3) >> 8) + ((var1 * self.dig_P2) << 12)
        var1 = (((1 << 47) + var1) * self.dig_P1) >> 33
        
        if var1 == 0:
            return 0  # Éviter la division par zéro
        
        p = 1048576 - raw_press
        p = (((p << 31) - var2) * 3125) // var1
        var1 = (self.dig_P9 * (p >> 13) * (p >> 13)) >> 25
        var2 = (self.dig_P8 * p) >> 19
        
        p = ((p + var1 + var2) >> 8) + (self.dig_P7 << 4)
        self._pressure = p / 256.0
    
    @property
    def temperature(self):
        """
        Lit la température en degrés Celsius
        
        Returns:
            float: Température en °C
        """
        self._calc_t_fine()
        return self._temperature
    
    @property
    def pressure(self):
        """
        Lit la pression atmosphérique en Pascals
        
        Returns:
            float: Pression en Pa
        """
        self._calc_t_fine()
        self._calc_pressure()
        return self._pressure
    
    def use_case(self, use_case):
        """
        Configure le capteur pour un cas d'utilisation spécifique
        
        Args:
            use_case: Cas d'utilisation prédéfini
        """
        if use_case == BMP280_CASE_HANDHELD_LOW:
            self.oversample_temp = BMP280_OS_2X
            self.oversample_pres = BMP280_OS_16X
            self.mode = BMP280_NORMAL_MODE
            self.filter = BMP280_FILTER_4
            self.standby = BMP280_STANDBY_62_5
        elif use_case == BMP280_CASE_HANDHELD_DYN:
            self.oversample_temp = BMP280_OS_1X
            self.oversample_pres = BMP280_OS_4X
            self.mode = BMP280_NORMAL_MODE
            self.filter = BMP280_FILTER_16
            self.standby = BMP280_STANDBY_0_5
        elif use_case == BMP280_CASE_WEATHER:
            self.oversample_temp = BMP280_OS_1X
            self.oversample_pres = BMP280_OS_1X
            self.mode = BMP280_FORCED_MODE
            self.filter = BMP280_FILTER_OFF
            self.standby = BMP280_STANDBY_0_5
        elif use_case == BMP280_CASE_FLOOR:
            self.oversample_temp = BMP280_OS_4X
            self.oversample_pres = BMP280_OS_4X
            self.mode = BMP280_NORMAL_MODE
            self.filter = BMP280_FILTER_4
            self.standby = BMP280_STANDBY_125
        elif use_case == BMP280_CASE_DROP:
            self.oversample_temp = BMP280_OS_1X
            self.oversample_pres = BMP280_OS_2X
            self.mode = BMP280_NORMAL_MODE
            self.filter = BMP280_FILTER_OFF
            self.standby = BMP280_STANDBY_0_5
        elif use_case == BMP280_CASE_INDOOR:
            self.oversample_temp = BMP280_OS_1X
            self.oversample_pres = BMP280_OS_16X
            self.mode = BMP280_NORMAL_MODE
            self.filter = BMP280_FILTER_16
            self.standby = BMP280_STANDBY_0_5
        
        self._write_config()
    
    def oversample(self, os_temp=None, os_pres=None):
        """
        Configure l'oversampling pour la température et la pression
        
        Args:
            os_temp: Oversampling pour la température
            os_pres: Oversampling pour la pression
        """
        if os_temp is not None:
            self.oversample_temp = os_temp
        if os_pres is not None:
            self.oversample_pres = os_pres
        
        self._write_config()


class BMP280Sensor:
    """
    Classe de haut niveau pour gérer le capteur BMP280 de température, pression et altitude
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
            # Initialiser la communication I2C
            self.i2c = I2C(i2c_id, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=freq)
            
            # Vérifier si le capteur est présent
            devices = self.i2c.scan()
            if address not in devices:
                raise RuntimeError(f"BMP280 non trouvé à l'adresse 0x{address:02x}")
            
            # Configurer le capteur BMP280
            self.bmp = BMP280(self.i2c, addr=address)
            self.bmp.use_case(BMP280_CASE_INDOOR)
            
            # Référence de pression au niveau de la mer (Pa)
            self.sea_level_pressure = 101325.0
            
            print(f"BMP280 initialisé avec succès à l'adresse 0x{address:02x}")
            
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
