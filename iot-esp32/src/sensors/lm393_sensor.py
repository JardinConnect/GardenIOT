from sensors.base_sensor import BaseSensor
from machine import Pin, ADC

class LM393Sensor(BaseSensor):
    def __init__(self, name="lm393", pin=35, dry_value=3500, wet_value=900, **kwargs):
        super().__init__(name, pin, **kwargs)
        self._adc = ADC(Pin(self.pin))
        self._adc.atten(ADC.ATTN_11DB)
        self._adc.width(ADC.WIDTH_12BIT)
        self._dry = dry_value
        self._wet = wet_value

    def _read_raw(self):
        raw = self._adc.read()
        pct = (self._dry - raw) / (self._dry - self._wet) * 100
        return {'soil_moisture': max(0, min(100, round(pct, 1)))}

    def _validate(self, data):
        m = data.get('soil_moisture')
        return m is not None and 0 <= m <= 100
