# Arduino Nano - Garden IoT Sensor Node

This directory contains the Arduino Nano implementation of the Garden IoT sensor node, translated from the Pico2W MicroPython code.

## Hardware Requirements

- Arduino Nano (or compatible board)
- LoRa SX1278 module (for wireless communication)
- DHT22 temperature and humidity sensor
- BH1750 light intensity sensor (I2C)
- BMP280 pressure/temperature/altitude sensor (I2C)
- LM393 soil moisture sensor

## Pin Connections

### LoRa Module (SX1278)
- SS/NSS → Pin 10
- RST → Pin 9
- DIO0 → Pin 2
- MOSI → Pin 11
- MISO → Pin 12
- SCK → Pin 13
- VCC → 3.3V
- GND → GND

### DHT22 Sensor
- Data → Pin 3
- VCC → 5V
- GND → GND
- 10kΩ pull-up resistor between Data and VCC

### I2C Sensors (BH1750 & BMP280)
- SDA → A4
- SCL → A5
- VCC → 3.3V (or 5V if module has voltage regulator)
- GND → GND

### LM393 Soil Moisture Sensor
- Analog Out → A0
- Digital Out → Pin 4
- VCC → 5V
- GND → GND

## Required Libraries

Install these libraries via Arduino IDE Library Manager:

1. **LoRa** by Sandeep Mistry
2. **DHT sensor library** by Adafruit
3. **Adafruit Unified Sensor** by Adafruit
4. **BH1750** by Christopher Laws
5. **Adafruit BMP280 Library** by Adafruit

## Files

- `nano_main.ino` - Main program with LoRa communication and all sensors
- `nano_sensors_test.ino` - Test program for sensors without LoRa (for debugging)

## Usage

### Testing Sensors
1. Upload `nano_sensors_test.ino` to test all sensors individually
2. Open Serial Monitor at 9600 baud
3. Verify all sensors are working correctly

### Main Program
1. Upload `nano_main.ino` for full functionality with LoRa
2. Configure LoRa parameters if needed (frequency, addresses)
3. Monitor via Serial at 9600 baud

## LoRa Configuration

Default settings:
- Frequency: 433 MHz
- TX Power: 15 dBm
- Client Address: 1
- Server Address: 2

Modify these constants in the code if needed for your region/application.

## Data Format

The sensor data is sent as a comma-separated string:
```
Count:X,Temp:XX.X,Hum:XX.X,Light:XXX.X,BMP_T:XX.X,Soil:XXX
```

## Troubleshooting

1. **I2C devices not found**: Check wiring and pull-up resistors
2. **DHT22 reading errors**: Ensure proper pull-up resistor and stable power supply
3. **LoRa fails to initialize**: Check SPI connections and module power
4. **Soil moisture readings inverted**: Adjust the mapping in `readLM393()` function

## Power Considerations

- Use external 5V power supply for stable operation
- Consider sleep modes for battery-powered applications
- LoRa module requires 3.3V (use level shifters if needed)