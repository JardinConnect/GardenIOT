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
        """
        Initialize hardware manager with config.
        
        Args:
            config: ConfigManager instance
        """
        self.config = config
        self.i2c = None
        self.spi = None
        self.lora = None
        self.rtc = None
    
    def init_i2c(self):
        """Initialize I2C bus from config"""
        i2c_config = self.config.get('i2c', {})
        
        self.i2c = I2C(
            i2c_config.get('id', 0),
            scl=Pin(i2c_config.get('scl', 22)),
            sda=Pin(i2c_config.get('sda', 21)),
            freq=i2c_config.get('freq', 400000)
        )
        
        print(f"[HardwareManager] ✓ I2C bus ready (SDA={i2c_config.get('sda')}, SCL={i2c_config.get('scl')})")
        return self.i2c
    
    def init_spi(self):
        """Initialize SPI bus from config"""
        lora_config = self.config.get('lora', {})
        pins = lora_config.get('pins', {})
        
        self.spi = SPI(
            1,
            baudrate=10_000_000,
            sck=Pin(pins.get('sck', 18)),
            mosi=Pin(pins.get('mosi', 23)),
            miso=Pin(pins.get('miso', 19))
        )
        
        print(f"[HardwareManager] ✓ SPI bus ready")
        return self.spi
    
    def init_lora_hardware(self):
        """Initialize LoRa radio module"""
        lora_config = self.config.get('lora', {})
        pins = lora_config.get('pins', {})
        
        # Init SPI if not already done
        if not self.spi:
            self.init_spi()
        
        # Import LoRa driver
        from lib.Lora import LoRa
        
        # Create LoRa hardware
        self.lora = LoRa(
            self.spi,
            cs=Pin(pins.get('cs', 5)),
            reset=Pin(pins.get('rst', 14)),
            freq=lora_config.get('frequency', 433.1)
        )
        
        # Set RF parameters
        self.lora.spreading_factor(lora_config.get('spreading_factor', 10))
        self.lora.bandwidth(lora_config.get('bandwidth', 500000))
        self.lora.coding_rate(lora_config.get('coding_rate', 5))
        self.lora.tx_power(lora_config.get('tx_power', 14))
        
        print(f"[HardwareManager] ✓ LoRa module ready (freq={lora_config.get('frequency')}MHz, SF={lora_config.get('spreading_factor')})")
        return self.lora
    
    def init_rtc(self):
        """Initialize RTC (DS3231) if available"""
        if not self.i2c:
            print("[HardwareManager] RTC requires I2C bus")
            return None
        
        try:
            from lib.ds3231 import DS3231
            self.rtc = DS3231(self.i2c)
            print("[HardwareManager] ✓ RTC (DS3231) initialized")
            return self.rtc
        except Exception as e:
            print(f"[HardwareManager] RTC not available: {e}")
            return None
