from sensors.base_sensor import BaseSensor
from machine import Pin
import dht

class DHT22Sensor(BaseSensor):
    def __init__(self, name="dht22", pin=27, **kwargs):
        super().__init__(name=name, pin=pin, **kwargs)
        self.pin = Pin(pin, Pin.IN)
        self.dht = dht.DHT22(self.pin)
    
    def _read_raw(self):
        self.dht.measure()
        return {
            'temperature': self.dht.temperature(),
            'humidity': self.dht.humidity()
        }

    
    def _validate(self, data):
        t = data.get('temperature')
        h = data.get('humidity')
        return (t is not None and -40 <= t <= 80 and
                h is not None and 0 <= h <= 100)