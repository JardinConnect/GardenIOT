from time import sleep
from ulora import LoRa, SPIConfig
from machine import Pin
import dht
from ds18b20 import DS18B20Sensor  # Importer notre module DS18B20
from sensor import *

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
        
        #construction du message         
        message = f'count: {count}'
        # Envoyer la température via LoRa
        if message is not None:
            # lora.send(message, SERVER_ADDRESS)
            print(message)
        else:
            message = f'Aucun capteur trouve (count: {count})'
            # lora.send(message, SERVER_ADDRESS)
            print(message)
            
        count = count + 1
    except OSError as e:
        print(f"Erreur: {e}")
    sleep(5)