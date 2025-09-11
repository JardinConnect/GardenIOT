from time import sleep, time
from library.ulora import LoRa, SPIConfig
from machine import Pin
import dht
from sensor import bh1750_sensor, dth22_sensor, lm393_sensor

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
        # Lire les valeurs des capteurs
        lux = bh1750_sensor.read_luminance()
        temp = dth22_sensor.read_temp()
        humidite = dth22_sensor.read_humidity()
        humidite_sol = lm393_sensor.read_temps_sol()

        datas = lux + temp + humidite + humidite_sol
        type = 1
        timestamps = time()
        uid = 1


        
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