import machine
import ubinascii

# ============================================
# UID UNIQUE DE L'ESP32
# ============================================
# Génère automatiquement un UID basé sur l'adresse MAC
UID = ubinascii.hexlify(machine.unique_id()).decode()

# ============================================
# PINS LORA (RFM9x)
# ============================================
LORA_SCK = 18      
LORA_MISO = 19     
LORA_MOSI = 23     
LORA_CS = 5        
LORA_RST = 27      
LORA_IRQ = 25    

# ============================================
# PARAMÈTRES RADIO LORA
# ============================================
LORA_FREQ = 433.1          # Fréquence en MHz
LORA_SF = 10               # Spreading Factor (7-12)
LORA_BW = 500000           # Bandwidth en Hz
LORA_CR = 5                # Coding Rate (5 = 4/5)
LORA_PREAMBLE = 8          # Longueur préambule
LORA_CRC = False           # CRC activé/désactivé
LORA_SYNC_WORD = 0x12      # Sync Word
LORA_TX_POWER = 14         # Puissance TX (dBm)
LORA_SPI_BAUDRATE = 5000000  # Vitesse SPI (5 MHz)

# ============================================
# PINS CAPTEURS
# ============================================
DHT22_PIN = 26          
DS18B20_PIN = 14            
LM393_PIN = 35
LM393_2_PIN = 36

# ============================================
# PINS I2C (BH1750 + DS3231)
# ============================================
I2C_ID = 0                 
I2C_SDA = 21               
I2C_SCL = 22               
I2C_FREQ = 400000          

# ============================================
# PINS BOUTON
# ============================================
BTN_PIN = 13               

# ============================================
# TIMEOUTS & DURÉES
# ============================================
PAIRING_TIMEOUT = 5000     
LISTEN_TIMEOUT = 3000      
SLEEP_INTERVAL = 15        
RESET_DURATION = 10000     

# ============================================
# CAPTEURS - RETRY & DELAYS
# ============================================
DHT22_RETRY = 3           
DHT22_DELAY = 2000         
SENSOR_TIMEOUT = 5000      

# ============================================
# FONCTION D'INITIALISATION
# ============================================
def init_hardware():
    """
    Initialise tout le matériel
    Retourne: (lora, capteurs_dict, btn)
    """
    import sys
    sys.path.append('/modules')
    sys.path.append('/config')
    sys.path.append('/sensors')
    from machine import Pin, SPI, I2C
    from Lora import LoRa
    
    from bh1750_sensor import BH1750Sensor
    from ds18b20 import DS18B20Sensor
    from ds3231 import DS3231
    from dth22_sensor import DHT22Sensor
    from lm393_sensor import SoilMoistureSensor
    
    # -------------------- SPI + LoRa --------------------
    spi = SPI(
        2,
        baudrate=LORA_SPI_BAUDRATE,
        polarity=0,
        phase=0,
        sck=Pin(LORA_SCK),
        mosi=Pin(LORA_MOSI),
        miso=Pin(LORA_MISO)
    )
    
    cs = Pin(LORA_CS, Pin.OUT)
    rst = Pin(LORA_RST, Pin.OUT)
    rx_irq = Pin(LORA_IRQ, Pin.IN)
    
    # Initialisation LoRa avec votre bibliothèque custom
    try:
        lora = LoRa(
            spi,
            cs=cs,
            rx=rx_irq,
            rs=rst,
            frequency=LORA_FREQ,
            bandwidth=LORA_BW,
            spreading_factor=LORA_SF,
            coding_rate=LORA_CR,
            preamble_length=LORA_PREAMBLE,
            crc=LORA_CRC,
            tx_power=LORA_TX_POWER,
            sync_word=LORA_SYNC_WORD
        )
    except Exception as e:
        print(f"Erreur LoRa: {e}")
        lora = None
    
    # -------------------- I2C --------------------
    try:
        i2c = I2C(I2C_ID, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA), freq=I2C_FREQ)
    except Exception as e:
        print(f"Erreur I2C: {e}")
        i2c = None
    
    # -------------------- RTC (DS3231) --------------------
    rtc = None
    if i2c:
        try:
            from ds3231 import DS3231
            rtc = DS3231(i2c)
            # Afficher l'heure actuelle pour vérification
            dt = rtc.datetime()
        except Exception as e:
            print(f"RTC: {e}")
    
    # -------------------- Pins capteurs --------------------
    dht22 = None
    ds18b20 = None
    lux_sensor = None
    lm393 = None
    lm393_2 = None
    
    # DHT22
    try:
        from dth22_sensor import DHT22Sensor
        dht22 = DHT22Sensor(pin=DHT22_PIN)
    except Exception as e:
        print(f"DHT22: {e}")
    
    # DS18B20
    try:
        from ds18b20 import DS18B20Sensor
        ds18b20 = DS18B20Sensor(pin=DS18B20_PIN)
    except Exception as e:
        print(f"DS18B20: {e}")
    
    # BH1750
    try:
        from bh1750_sensor import BH1750Sensor
        lux_sensor = BH1750Sensor(i2c_id=I2C_ID, sda_pin=I2C_SDA, scl_pin=I2C_SCL)
    except Exception as e:
        print(f"BH1750: {e}")
    
    # LM393
    try:
        from lm393_sensor import SoilMoistureSensor
        lm393 = SoilMoistureSensor(analog_pin=LM393_PIN)
        lm393_2 = SoilMoistureSensor(analog_pin=LM393_2_PIN)
    except Exception as e:
        print(f"LM393: {e}")
    
    capteurs = {
        'dht22': dht22,
        'ds18b20': ds18b20,
        'lux_sensor': lux_sensor,
        'lm393': lm393,
        'lm393_2' : lm393_2
    }
    
    # -------------------- Bouton --------------------
    btn = Pin(BTN_PIN, Pin.IN, Pin.PULL_UP)
    
    return lora, capteurs, btn, rtc