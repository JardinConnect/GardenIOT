from sensors.base_sensor import BaseSensor
from machine import Pin
import dht
import time

class DHT22Sensor(BaseSensor):
    def __init__(self, name="dht22", pin=27, **kwargs):
        super().__init__(name=name, pin=pin, **kwargs)
        self.pin = Pin(pin, Pin.IN)
        self.dht = dht.DHT22(self.pin)
        self._retry_count = kwargs.get('retry_count', 3)
        self._retry_delay = kwargs.get('retry_delay', 100)  # ms
    
    def _read_raw(self):
        for attempt in range(self._retry_count):
            try:
                self.dht.measure()
                temperature = self.dht.temperature()
                humidity = self.dht.humidity()
                
                return {
                    'temperature': temperature,
                    'humidity': humidity
                }
            except OSError as e:
                if attempt < self._retry_count - 1:
                    time.sleep_ms(self._retry_delay)
                    continue
                else:
                    print(f"  [{self.name}] DHT22 read failed after {self._retry_count} attempts: {e}")
                    return None
        
        return None
    
    def _validate(self, data):
        if data is None:
            return False
            
        t = data.get('temperature')
        h = data.get('humidity')
        return (t is not None and -40 <= t <= 80 and
                h is not None and 0 <= h <= 100)