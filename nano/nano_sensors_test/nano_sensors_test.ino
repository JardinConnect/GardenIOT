// Simple sensor test for Arduino Nano
// Tests each sensor individually without LoRa

#include <DHT.h>
#include <Wire.h>
#include <BH1750.h>
#include <Adafruit_BMP280.h>

// Sensor Pins
#define DHT22_PIN 3
#define LM393_ANALOG_PIN A0
#define LM393_DIGITAL_PIN 4

// Sensor Objects
DHT dht(DHT22_PIN, DHT22);
BH1750 lightMeter;
Adafruit_BMP280 bmp;

void setup() {
  Serial.begin(9600);
  while (!Serial);
  
  Serial.println("Arduino Nano - Sensor Test Program");
  Serial.println("==================================");
  
  // Initialize I2C
  Wire.begin();
  Serial.println("I2C initialized");
  
  // Scan for I2C devices
  Serial.println("Scanning for I2C devices...");
  scanI2C();
  
  // Initialize sensors
  initializeSensors();
  
  Serial.println("\nStarting sensor readings...\n");
}

void loop() {
  Serial.println("----------------------------------------");
  Serial.println("Sensor Readings:");
  Serial.println("----------------------------------------");
  
  // Test DHT22
  testDHT22();
  
  // Test BH1750
  testBH1750();
  
  // Test LM393
  testLM393();
  
  Serial.println("----------------------------------------\n");
  
  delay(5000); // Wait 5 seconds before next reading
}

void scanI2C() {
  byte error, address;
  int nDevices = 0;
  
  for(address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();
    
    if (error == 0) {
      Serial.print("I2C device found at address 0x");
      if (address < 16) Serial.print("0");
      Serial.print(address, HEX);
      
      // Identify known devices
      if (address == 0x23 || address == 0x5C) {
        Serial.print(" (BH1750 Light Sensor)");
      }
      if (address == 0x76 || address == 0x77) {
        Serial.print(" (BMP280 Pressure Sensor)");
      }
      
      Serial.println();
      nDevices++;
    }
  }
  
  if (nDevices == 0) {
    Serial.println("No I2C devices found");
  } else {
    Serial.print("Found ");
    Serial.print(nDevices);
    Serial.println(" I2C device(s)");
  }
}

void initializeSensors() {
  Serial.println("\nInitializing sensors...");
  
  // Initialize DHT22
  dht.begin();
  Serial.println("✓ DHT22 initialized");
  
  // Initialize BH1750
  if (lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
    Serial.println("✓ BH1750 light sensor initialized");
  } else {
    Serial.println("✗ BH1750 initialization failed");
  }
  
  // Initialize BMP280
  if (bmp.begin(0x76)) {
    Serial.println("✓ BMP280 initialized at address 0x76");
  } else if (bmp.begin(0x77)) {
    Serial.println("✓ BMP280 initialized at address 0x77");
  } else {
    Serial.println("✗ BMP280 initialization failed");
  }
  
  // Configure BMP280 if initialized
  if (bmp.begin(0x76) || bmp.begin(0x77)) {
    bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,
                    Adafruit_BMP280::SAMPLING_X2,
                    Adafruit_BMP280::SAMPLING_X16,
                    Adafruit_BMP280::FILTER_X16,
                    Adafruit_BMP280::STANDBY_MS_500);
  }
  
  // Initialize LM393
  pinMode(LM393_DIGITAL_PIN, INPUT);
  Serial.println("✓ LM393 soil moisture sensor initialized");
}

void testDHT22() {
  Serial.println("\nDHT22 Sensor:");
  
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();
  
  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("  Error: Failed to read from DHT22");
  } else {
    Serial.print("  Temperature: ");
    Serial.print(temperature);
    Serial.println(" °C");
    
    Serial.print("  Humidity: ");
    Serial.print(humidity);
    Serial.println(" %");
    
    // Calculate heat index
    float heatIndex = dht.computeHeatIndex(temperature, humidity, false);
    Serial.print("  Heat Index: ");
    Serial.print(heatIndex);
    Serial.println(" °C");
  }
}

void testBH1750() {
  Serial.println("\nBH1750 Light Sensor:");
  
  float lux = lightMeter.readLightLevel();
  
  if (lux < 0) {
    Serial.println("  Error: Failed to read light level");
  } else {
    Serial.print("  Light Level: ");
    Serial.print(lux);
    Serial.println(" lux");
    
    // Interpret light level
    Serial.print("  Condition: ");
    if (lux < 10) {
      Serial.println("Very Dark");
    } else if (lux < 50) {
      Serial.println("Dark");
    } else if (lux < 200) {
      Serial.println("Dim");
    } else if (lux < 500) {
      Serial.println("Normal Indoor");
    } else if (lux < 10000) {
      Serial.println("Bright Indoor");
    } else {
      Serial.println("Outdoor/Direct Sunlight");
    }
  }
}

void testBMP280() {
  Serial.println("\nBMP280 Pressure Sensor:");
  
  float temperature = bmp.readTemperature();
  float pressure = bmp.readPressure() / 100.0F; // Convert to hPa
  float altitude = bmp.readAltitude(1013.25); // Standard sea level pressure
  
  Serial.print("  Temperature: ");
  Serial.print(temperature);
  Serial.println(" °C");
  
  Serial.print("  Pressure: ");
  Serial.print(pressure);
  Serial.println(" hPa");
  
  Serial.print("  Altitude: ");
  Serial.print(altitude);
  Serial.println(" meters");
}

void testLM393() {
  Serial.println("\nLM393 Soil Moisture Sensor:");
  
  int analogValue = analogRead(LM393_ANALOG_PIN);
  int digitalValue = digitalRead(LM393_DIGITAL_PIN);
  
  Serial.print("  Analog Value: ");
  Serial.print(analogValue);
  Serial.println(" (0-1023)");
  
  Serial.print("  Digital Value: ");
  Serial.println(digitalValue == HIGH ? "HIGH (Dry)" : "LOW (Wet)");
  
  // Calculate percentage (inverse - higher value = drier)
  int moisturePercent = map(analogValue, 1023, 0, 0, 100);
  Serial.print("  Moisture Level: ");
  Serial.print(moisturePercent);
  Serial.println(" %");
  
  // Interpret moisture level
  Serial.print("  Soil Condition: ");
  if (moisturePercent < 30) {
    Serial.println("Very Dry - Water needed!");
  } else if (moisturePercent < 60) {
    Serial.println("Moderately Moist");
  } else if (moisturePercent < 80) {
    Serial.println("Well Watered");
  } else {
    Serial.println("Very Wet - Risk of overwatering");
  }
}
