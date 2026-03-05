from machine import Pin
import dht
import time

class DHT22Sensor:
    def __init__(self, pin=33):
        self.pin = Pin(pin, Pin.IN)
        self.dht = dht.DHT22(self.pin)
    
    def read_all(self):
        """Fait une seule mesure et retourne (temp, hum)"""
        try:
            self.dht.measure()
            return (self.dht.temperature(), self.dht.humidity())
        except OSError:
            return (None, None)