from machine import I2C

class MAX17043:
    def __init__(self, i2c, address=0x36):
        self.i2c = i2c
        self.addr = address

    def _read_reg(self, reg):
        data = self.i2c.readfrom_mem(self.addr, reg, 2)
        return (data[0] << 8) | data[1]

    def quick_start(self):
        # Réinitialise pour une mesure immédiate
        self.i2c.writeto_mem(self.addr, 0x06, b'\x40\x00')

    @property
    def voltage(self):
        # Le registre 0x02 contient la tension (VCELL)
        # La valeur est sur les 12 bits de poids fort
        res = self._read_reg(0x02)
        return (res >> 4) * 0.00125  # Unité de 1.25mV

    @property
    def soc(self):
        # Le registre 0x04 contient le State of Charge (%)
        # L'octet de poids fort est le pourcentage entier
        # L'octet de poids faible est la fraction (1/256)
        res = self._read_reg(0x04)
        percentage = (res >> 8) + (res & 0xFF) / 256.0
        return percentage

    def reset(self):
        # Envoie une commande de reset logiciel
        self.i2c.writeto_mem(self.addr, 0xFE, b'\x00\x54')