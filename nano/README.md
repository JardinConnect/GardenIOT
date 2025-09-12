# Arduino Nano - Garden IoT Sensor Node v2.2

This directory contains the Arduino Nano implementation of the Garden IoT sensor node with LoRa transmission using a custom protocol format.

## Hardware Requirements

- Arduino Nano (or compatible board)
- LoRa SX1278 module (for wireless communication)
- DHT22 temperature and humidity sensor
- DS18B20 temperature sensor (for soil temperature)
- BH1750 light intensity sensor (I2C)
- RTC DS3231 module (I2C)
- Soil moisture sensor (analog)

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
- Data → Pin 4
- VCC → 5V
- GND → GND
- 10kΩ pull-up resistor between Data and VCC

### DS18B20 Sensor
- Data → Pin 3
- VCC → 3.3V or 5V
- GND → GND
- 4.7kΩ pull-up resistor between Data and VCC

### BH1750 Light Sensor
- SDA → A4
- SCL → A5
- VCC → 3.3V (or 5V if module has voltage regulator)
- GND → GND

### RTC DS3231 Module
- SDA → A4
- SCL → A5
- VCC → 5V
- GND → GND

### Soil Moisture Sensor
- Analog Out → A0
- VCC → 5V
- GND → GND

## Required Libraries

Install these libraries via Arduino IDE Library Manager:

1. **LoRa** by Sandeep Mistry
2. **DHT sensor library** by Adafruit
3. **BH1750** by Christopher Laws
4. **RTClib** by Adafruit
5. **OneWire** by Paul Stoffregen
6. **DallasTemperature** by Miles Burton

## Files

- `garden_iot_nano_v2.2.ino` - Main program with LoRa communication and all sensors

## Usage

### Configuration

1. Set the node unique identifier in the code:
   ```cpp
   #define NODE_UID "nano1"  // Change this for each node
   ```

2. Adjust transmission interval if needed (default 30 seconds):
   ```cpp
   const unsigned long SEND_INTERVAL = 30000; // milliseconds
   ```

### Upload and Monitor

1. Connect Arduino Nano via USB
2. Select **Tools > Board > Arduino Nano**
3. Select appropriate processor (Old/New Bootloader)
4. Upload the code
5. Open Serial Monitor at **115200 baud** (changed from 9600)

## LoRa Configuration

Default settings:
- Frequency: 433 MHz
- TX Power: 14 dBm
- Spreading Factor: 7
- Bandwidth: 125 kHz

Modify these parameters in the code if needed for your region/application.

## Data Format

### Protocol Structure
```
XXXXB|TYPE|TIMESTAMP|UID|DATA|E
```

- `XXXX`: 4-character offset prefix
- `B`: Begin marker
- `TYPE`: Message type (1=Data, 2=Alert, 3=Error)
- `TIMESTAMP`: Unix timestamp
- `UID`: Node identifier (4 characters)
- `DATA`: Sensor readings separated by `:`
- `E`: End marker

### Sensor Data Format
```
1B100:1TA25:1TS22:1HA68:1HS41:1L114
```

- `1B100`: Battery 100% (fixed value)
- `1TA25`: Air temperature 25°C
- `1TS22`: Soil temperature 22°C (from DS18B20)
- `1HA68`: Air humidity 68%
- `1HS41`: Soil humidity 41%
- `1L114`: Light 114 lux

### Error Codes
- `1TAERR`: Air temperature sensor error
- `1TSERR`: Soil temperature sensor error
- `1HAERR`: Air humidity sensor error
- `1LERR`: Light sensor error

## Troubleshooting

1. **I2C devices not found**: 
   - Check wiring and pull-up resistors
   - Verify I2C addresses (RTC: 0x68, BH1750: 0x23)

2. **DHT22 reading errors**: 
   - Ensure proper pull-up resistor (10kΩ)
   - Check stable power supply
   - Allow 2 seconds between readings

3. **DS18B20 shows -127°C or 85°C**: 
   - Check 4.7kΩ pull-up resistor
   - Verify OneWire connection on Pin 3
   - These are error codes indicating connection issues

4. **LoRa fails to initialize**: 
   - Check SPI connections
   - Verify 3.3V power to module
   - Ensure NSS is on Pin 10

5. **Soil moisture readings incorrect**: 
   - Calibrate by adjusting the `map()` function parameters
   - Dry soil = high resistance (1023), Wet soil = low resistance (0)

6. **RTC lost time**: 
   - Replace CR2032 battery
   - Code auto-sets to compile time if power lost

## Power Considerations

- Use external 5V power supply for stable operation
- LoRa module requires 3.3V (Arduino Nano has onboard regulator)
- Current consumption:
  - Idle: ~20mA
  - Transmitting: ~120mA peak
  - Average: ~25-30mA with 30s interval

## New Features in v2.2

- **Protocol with XXXX prefix** for message offset handling
- **DS18B20 support** for accurate soil temperature
- **RTC integration** for precise timestamps
- **Improved error handling** with specific error codes
- **Fixed battery value** (100%) as battery monitoring not implemented
- **Raw lux values** instead of percentages for light readings

## Migration Notes

If upgrading from previous versions:
- Baud rate changed from 9600 to 115200
- DHT22 moved from Pin 3 to Pin 4
- DS18B20 added on Pin 3
- Protocol format completely changed
- BMP280 removed from this version
