from machine import Pin
import dht
import time

class DTH22Sensor:
    def __init__(self, pin=2):
        self.pin = Pin(pin, Pin.IN)
        self.dht = dht.DHT22(self.pin)
    
    def read_temp(self):
        self.dht.measure()
        return self.dht.temperature()
    
    def read_humidity(self):
        self.dht.measure()
        return self.dht.humidity()

if __name__ == "__main__":
    sensor = DTH22Sensor(pin=2)
    
    while True:
        temps = sensor.read_temp()
        humidite = sensor.read_humidity()
        print(f'Températures: {temps}')
        print(f'Humidite: {humidite}')
        time.sleep_ms(2000)