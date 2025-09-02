from time import sleep
from ulora import LoRa, SPIConfig
from machine import Pin
import dht

# LoRa Parameters
SX1278_RST = 4
CONFIG_SPIBUS = SPIConfig.rp2_0
SX1278_CS = 1
SX1278_INT = 5
SX1278_FREQ = 433
SX1278_POW = 15
CLIENT_ADDRESS = 1
SERVER_ADDRESS = 2

# initialise radio
lora = LoRa(CONFIG_SPIBUS, SX1278_INT, CLIENT_ADDRESS, SX1278_CS, reset_pin=SX1278_RST, freq=SX1278_FREQ, tx_power=SX1278_POW, acks=True)


count = 0
# loop and send data
while True:
    try:
        lora.send(f'lorem ipsum dolor sit amet this is a test{count}', SERVER_ADDRESS)
        print('Hello world')
        count = count + 1
    except OSError as e:
        print("Błąd odczytu z czujnika.")
    sleep(5)