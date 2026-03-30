from sensors.base_sensor import BaseSensor
from max17043 import MAX17043

class MAX17043Sensor(BaseSensor):
    def __init__(self, name="battery", i2c=None, address=0x36, **kwargs):
        super().__init__(name=name, **kwargs)
        if i2c is None:
            raise ValueError("I2C bus is required for MAX17043")
        self.i2c = i2c
        self._address = address
        self.sensor = MAX17043(self.i2c, address=address)
        self.init_hardware()

    def _check_hardware(self):
        return self._address in self.i2c.scan()

    def _read_raw(self):
        return {
            "VB": self.sensor.voltage,  # voltage batterie
            "SB": self.sensor.soc       # state of charge
        }

    def _validate(self, data):
        vb = data.get("VB")
        sb = data.get("SB")
        return vb is not None and 2.5 <= vb <= 5.0 and sb is not None and 0 <= sb <= 100