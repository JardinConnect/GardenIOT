"""
Hardware Manager - Handles low-level hardware initialization.
Responsible for I2C, SPI buses and LoRa module setup.
"""

from machine import SPI, Pin, I2C


class HardwareManager:
    """
    Manages hardware initialization (I2C, SPI, LoRa).
    Separates hardware concerns from business logic.
    """
    
    def __init__(self, config):
        self.config = config
        self.i2c = None
        self.spi = None
        self.lora = None

    def init_i2c(self):
        i2c_config = self.config.get('i2c', {})
        sda = i2c_config.get('sda', 21)
        scl = i2c_config.get('scl', 22)
        freq = i2c_config.get('freq', 400000)
        bus_id = i2c_config.get('id', 0)
        
        self.i2c = I2C(bus_id, scl=Pin(scl), sda=Pin(sda), freq=freq)
        print(f"[HardwareManager] I2C bus ready (SDA={sda}, SCL={scl})")
        return self.i2c

    def init_spi(self):
        lora_pins = self.config.get('lora.pins', {})
        sck = lora_pins.get('sck', 18)
        mosi = lora_pins.get('mosi', 23)
        miso = lora_pins.get('miso', 19)
        baudrate = self.config.get('lora.spi_baudrate', 5000000)
        
        self.spi = SPI(
            1,
            baudrate=baudrate,
            polarity=0,
            phase=0,
            sck=Pin(sck),
            mosi=Pin(mosi),
            miso=Pin(miso)
        )
        print(f"[HardwareManager] SPI bus ready")
        return self.spi

    def init_lora_hardware(self):
        """Initialize LoRa radio module"""
        lora_config = self.config.get('lora', {})
        print(f"[HardwareManager] Initializing LoRa hardware with config: {lora_config}")
        pins = lora_config.get('pins', {})
        
        if not self.spi:
            self.init_spi()
        
        from lib.Lora import LoRa

        print(f"[HardwareManager] SPI initialized: {self.spi}")
        
        # Create Pin objects (comme dans pins.py)
        cs = Pin(pins.get('cs', 5), Pin.OUT)
        rst = Pin(pins.get('rst', 14), Pin.OUT)
        rx_irq = Pin(pins.get('dio0', 26), Pin.IN)
        
        self.lora = LoRa(
            self.spi,
            cs=cs,
            rx=rx_irq,  # Réactiver les interruptions
            rs=rst,
            frequency=lora_config.get('frequency', 433.1),
            bandwidth=lora_config.get('bandwidth', 500000),
            spreading_factor=lora_config.get('spreading_factor', 10),
            coding_rate=lora_config.get('coding_rate', 5),
            preamble_length=lora_config.get('preamble_length', 8),
            crc=lora_config.get('crc', False),
            tx_power=lora_config.get('tx_power', 14),
            sync_word=lora_config.get('sync_word', 0x12)
        )
        
        print(f"[HardwareManager] LoRa module ready (freq={lora_config.get('frequency')}MHz, SF={lora_config.get('spreading_factor')})")
        return self.lora

    def init_rtc(self):
        if not self.i2c:
            self.init_i2c()
        
        try:
            from lib.ds3231 import DS3231
            rtc = DS3231(self.i2c)
            print("[HardwareManager] RTC (DS3231) ready")
            return rtc
        except Exception as e:
            print(f"[HardwareManager] RTC init failed: {e}")
            return None