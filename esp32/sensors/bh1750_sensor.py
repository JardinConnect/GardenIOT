from machine import I2C, Pin
import time
import sys
sys.path.append('/lib')
from bh1750 import BH1750


class BH1750Sensor:
    def __init__(self, i2c_id=0, sda_pin=21, scl_pin=22, freq=400000, address=0x23):
        try:
            self.i2c = I2C(i2c_id, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=freq)

            devices = self.i2c.scan()

            self.sensor = BH1750(bus=self.i2c, addr=address)
            self.mode = BH1750.CONT_HIRES_1

        except Exception as e:
            print(f"Erreur init BH1750: {e}")
            raise

    def read_luminance(self, mode=None):
        try:
            if mode is None:
                mode = self.mode
            return self.sensor.luminance(mode)
        except Exception as e:
            print(f"Erreur lecture luminosité: {e}")
            return None


if __name__ == "__main__":
    try:
        sensor = BH1750Sensor(i2c_id=0, sda_pin=21, scl_pin=22)
        while True:
            lux = sensor.read_luminance()
            print(f"Luminosité: {lux:.2f} lux")
            time.sleep(2)
    except KeyboardInterrupt:
        print("Arrêt du programme")
