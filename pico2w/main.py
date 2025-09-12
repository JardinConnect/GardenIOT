from time import sleep, time
from library.ulora import LoRa, SPIConfig
from machine import Pin
import dht
from sensor import bh1750_sensor, dth22_sensor, lm393_sensor, ds18b20_sensor

# # LoRa Parameters
SX1278_RST = 4
CONFIG_SPIBUS = SPIConfig.rp2_0
SX1278_CS = 1
SX1278_INT = 5
SX1278_FREQ = 433
SX1278_POW = 15
CLIENT_ADDRESS = 1
SERVER_ADDRESS = 2

# Initialiser les capteurs
bh1750_sensor = bh1750_sensor.BH1750Sensor()
dth22_sensor = dth22_sensor.DTH22Sensor()
lm393_sensor = lm393_sensor.LM393Sensor()
ds18b20_sensor = ds18b20_sensor.DS18B20Sensor()

# initialise radio
lora = LoRa(CONFIG_SPIBUS, SX1278_INT, CLIENT_ADDRESS, SX1278_CS, reset_pin=SX1278_RST, freq=SX1278_FREQ, tx_power=SX1278_POW, acks=True)

count = 0
# loop and send data
while True:
    try:
        # tester si les capteurs sont initialisés
        if bh1750_sensor is None:
            raise Exception("Capteurs bh1750_sensor non initialisés")
        if dth22_sensor is None:
            raise Exception("Capteurs dth22_sensor non initialisés")
        if lm393_sensor is None:
            raise Exception("Capteurs lm393_sensor non initialisés")
        if ds18b20_sensor is None:
            raise Exception("Capteurs ds18b20_sensor non initialisés")
        # Read sensor values
        light = bh1750_sensor.read_luminance()
        air_temp = dth22_sensor.read_temp()
        air_humidity = dth22_sensor.read_humidity()
        soil_humidity = lm393_sensor.read_humidity()
        soil_temp = ds18b20_sensor.read_temp()

        datas = light + ':' + air_temp + ':' + air_humidity + ':' + soil_humidity + ':' + soil_temp
        type = 1
        timestamps = time()
        uid = 1234


        
        #construction du message         
        message = 'B|' + str(type) + '|' + str(timestamps) + '|' + str(uid) + '|' + str(datas) + '|E'
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