from time import sleep
from ulora import LoRa, SPIConfig
from machine import Pin
from sensor.bh1750_sensor import BH1750Sensor
from sensor.bmp280_sensor import BMP280Sensor
from sensor.dth22_sensor import DTH22Sensor
from sensor.lm393_sensor import LM393Sensor

# # LoRa Parameters
# SX1278_RST = 4
# CONFIG_SPIBUS = SPIConfig.rp2_0
# SX1278_CS = 1
# SX1278_INT = 5
# SX1278_FREQ = 433
# SX1278_POW = 15
# CLIENT_ADDRESS = 1
# SERVER_ADDRESS = 2

# Initialiser les capteurs
bh1750_sensor = BH1750Sensor()
bmp280_sensor = BMP280Sensor()
dth22_sensor = DTH22Sensor()
lm393_sensor = LM393Sensor()

# initialise radio
# lora = LoRa(CONFIG_SPIBUS, SX1278_INT, CLIENT_ADDRESS, SX1278_CS, reset_pin=SX1278_RST, freq=SX1278_FREQ, tx_power=SX1278_POW, acks=True)

count = 0
# loop and send data
while True:
    try:
        # Lire les valeurs des capteurs
        lux = bh1750_sensor.read_luminance()
        
        # Envoyer la valeur brute du capteur (0-65535)
        if lux is not None:
            light_value = int(lux)
        else:
            light_value = 0
        
        #construction du message         
        message = f'L:{light_value},count:{count}'
        
        # Afficher avec la valeur en lux pour debug
        print(f"Sending - Light: {light_value} lux, Count: {count}")
        
        # Envoyer la température via LoRa
        if message is not None:
            # lora.send(message, SERVER_ADDRESS)
            print(f"Message: {message}")
        else:
            message = f'Aucun capteur trouve (count: {count})'
            # lora.send(message, SERVER_ADDRESS)
            print(message)
            
        count = count + 1
    except OSError as e:
        print(f"Erreur: {e}")
    sleep(5)