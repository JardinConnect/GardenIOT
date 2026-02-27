from machine import I2C, Pin
import time
import sys
sys.path.append('/lib')
from bh1750 import BH1750
from sensors.base_sensor import BaseSensor


class BH1750Sensor(BaseSensor):
    def __init__(self, name="bh1750", i2c_id=0, sda_pin=21, scl_pin=22, freq=400000, address=0x23, **kwargs):
        super().__init__(name=name, **kwargs)
        self.i2c = I2C(i2c_id, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=freq)
        devices = self.i2c.scan()
        self.sensor = BH1750(bus=self.i2c, addr=address)
        self.mode = BH1750.CONT_HIRES_1


    def _read_raw(self, mode=None):
        if mode is None:
            mode = self.mode
        return {'luminance': self.sensor.luminance(mode)}

    def _validate(self, data):
        l = data.get('luminance')
        return l is not None and 0 <= l <= 65535