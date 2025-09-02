from time import sleep
# from ulora import LoRa, SPIConfig
from machine import Pin
import dht
from ds18b20 import DS18B20Sensor  # Importer notre module DS18B20

# # LoRa Parameters
# SX1278_RST = 4
# CONFIG_SPIBUS = SPIConfig.rp2_0
# SX1278_CS = 1
# SX1278_INT = 5
# SX1278_FREQ = 433
# SX1278_POW = 15
# CLIENT_ADDRESS = 1
# SERVER_ADDRESS = 2

# Initialiser le capteur DS18B20 sur la broche GPIO 12
ds18b20_sensor = DS18B20Sensor(pin=12)
print(f'DS18B20 capteurs trouvés: {ds18b20_sensor.get_device_count()}')

# initialise radio
# lora = LoRa(CONFIG_SPIBUS, SX1278_INT, CLIENT_ADDRESS, SX1278_CS, reset_pin=SX1278_RST, freq=SX1278_FREQ, tx_power=SX1278_POW, acks=True)

count = 0
# loop and send data
while True:
    try:
        # Lire la température du capteur DS18B20
        temperature = ds18b20_sensor.read_temp()
        print('nombre de capteur: ' + str(ds18b20_sensor.get_device_count()))
        
        # Envoyer la température via LoRa
        if temperature is not None:
            message = f'Temperature: {temperature:.2f}C (count: {count})'
            # lora.send(message, SERVER_ADDRESS)
            print(message)
        else:
            message = f'Aucun capteur DS18B20 trouve (count: {count})'
            # lora.send(message, SERVER_ADDRESS)
            print(message)
            
        count = count + 1
    except OSError as e:
        print(f"Erreur: {e}")
    sleep(5)