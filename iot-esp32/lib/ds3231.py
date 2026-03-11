from machine import I2C
import time

class DS3231:
    DS3231_ADDR = 0x68

    def __init__(self, i2c: I2C):
        self.i2c = i2c

    # --- Conversions BCD <-> décimal ---
    def _bcd2dec(self, b):
        return (b >> 4) * 10 + (b & 0x0F)

    def _dec2bcd(self, d):
        return ((d // 10) << 4) | (d % 10)

    # --- Lecture de la date/heure ---
    def datetime(self):
        """Retourne (année, mois, jour, semaine, heure, minute, seconde)"""
        data = self.i2c.readfrom_mem(self.DS3231_ADDR, 0x00, 7)
        seconde = self._bcd2dec(data[0] & 0x7F)
        minute  = self._bcd2dec(data[1])
        heure   = self._bcd2dec(data[2])
        semaine = self._bcd2dec(data[3])
        jour    = self._bcd2dec(data[4])
        mois    = self._bcd2dec(data[5] & 0x1F)
        annee   = 2000 + self._bcd2dec(data[6])
        return (annee, mois, jour, semaine, heure, minute, seconde)

    # --- Réglage de la date/heure ---
    def set_datetime(self, dt_tuple):
        """
        Définit la date et l'heure sur le DS3231.
        Tuple formaté comme (année, mois, jour, semaine, heure, minute, seconde)
        """
        annee, mois, jour, semaine, heure, minute, seconde = dt_tuple
        data = bytearray([
            self._dec2bcd(seconde),
            self._dec2bcd(minute),
            self._dec2bcd(heure),
            self._dec2bcd(semaine),
            self._dec2bcd(jour),
            self._dec2bcd(mois),
            self._dec2bcd(annee - 2000)
        ])
        self.i2c.writeto_mem(self.DS3231_ADDR, 0x00, data)
        time.sleep_ms(200)
