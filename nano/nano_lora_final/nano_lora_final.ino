#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <BH1750.h>
#include <DHT.h>

// === Pin Configuration ===
#define DHTPIN        4     // DHT22 on pin D4
#define DHTTYPE       DHT22
#define SOIL_SENSOR   A0    // Soil moisture sensor on A0

// LoRa SX1278 pins
#define NSS   10  // CS
#define RST   9   // Reset
#define DIO0  2   // Interrupt

// === Sensor instances ===
DHT dht(DHTPIN, DHTTYPE);
BH1750 lightMeter;

// === Variables ===
unsigned long count = 0;

void setup() {
  Serial.begin(9600);
  while (!Serial) {
    delay(10);
  }
  
  Serial.println(F("Garden IoT - Arduino Nano"));
  Serial.println(F("========================="));
  
  // Initialize I2C
  Wire.begin();
  Serial.println(F("I2C initialized"));
  
  // Initialize BH1750
  if (!lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
    Serial.println(F("BH1750 not detected!"));
  } else {
    Serial.println(F("BH1750 OK"));
  }
  
  // Initialize DHT22
  dht.begin();
  Serial.println(F("DHT22 OK"));
  
  // Initialize SPI for LoRa
  Serial.println(F("Initializing SPI..."));
  SPI.begin();
  pinMode(NSS, OUTPUT);
  digitalWrite(NSS, HIGH);
  
  // Reset LoRa module
  Serial.println(F("Resetting LoRa..."));
  pinMode(RST, OUTPUT);
  digitalWrite(RST, LOW);
  delay(10);
  digitalWrite(RST, HIGH);
  delay(10);
  
  // Initialize LoRa
  Serial.println(F("Initializing LoRa..."));
  LoRa.setPins(NSS, RST, DIO0);
  
  if (!LoRa.begin(433E6)) {
    Serial.println(F("LoRa init failed!"));
    Serial.println(F("Check wiring:"));
    Serial.println(F("  MISO -> D12"));
    Serial.println(F("  MOSI -> D11"));
    Serial.println(F("  SCK  -> D13"));
    Serial.println(F("  NSS  -> D10"));
    Serial.println(F("  RST  -> D9"));
    Serial.println(F("  DIO0 -> D2"));
    while (1) {
      delay(1000);
    }
  }
  
  Serial.println(F("LoRa OK"));
  
  // Configure LoRa
  LoRa.setTxPower(14);
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  
  Serial.println(F("========================="));
  Serial.println(F("Setup complete!"));
  Serial.println();
}

void loop() {
  // Read DHT22
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  
  // Read BH1750
  float light = lightMeter.readLightLevel();
  
  // Read soil moisture
  int soilRaw = analogRead(SOIL_SENSOR);
  // Convert to percentage (0-100%)
  int soilPercent = map(soilRaw, 1023, 0, 0, 100);
  
  // Check for sensor errors and set default values
  if (isnan(temperature)) {
    temperature = -999.0;
  }
  if (isnan(humidity)) {
    humidity = -999.0;
  }
  if (light < 0) {
    light = -999.0;
  }
  
  // Create message in the format
  // Format: Count:X,Temp:XX.X,Hum:XX.X,Light:XXX.X,BMP_T:XX.X,Soil:XXX
  char message[100];
  
  // Using dtostrf for float to string conversion
  char tempStr[8], humStr[8], lightStr[8];
  dtostrf(temperature, 5, 1, tempStr);
  dtostrf(humidity, 5, 1, humStr);
  dtostrf(light, 6, 1, lightStr);
  
  snprintf(message, sizeof(message), 
    "Count:%lu,Temp:%s,Hum:%s,Light:%s,BMP_T:0.0,Soil:%d",
    count, tempStr, humStr, lightStr, soilPercent);
  
  // Display on serial
  Serial.print(F("TX: "));
  Serial.println(message);
  
  // Send via LoRa
  Serial.print(F("Sending..."));
  LoRa.beginPacket();
  LoRa.print(message);
  int result = LoRa.endPacket(false); // Non-blocking mode
  
  if (result == 1) {
    Serial.println(F(" SUCCESS"));
  } else {
    Serial.print(F(" FAILED ("));
    Serial.print(result);
    Serial.println(F(")"));
  }
  
  Serial.println(F("------------------------"));
  
  count++;
  delay(5000); // Send every 5 seconds
}