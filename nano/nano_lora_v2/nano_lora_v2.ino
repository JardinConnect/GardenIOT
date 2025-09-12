/*
 * Garden IoT - Arduino Nano LoRa v2
 * Version: 2.2 - Final
 * 
 * Features:
 * - RTC DS3231 support with timestamp
 * - Modified protocol format: XXXXB|Type|Timestamp|UID|Data|E
 * - DS18B20 for real soil temperature
 * - Single soil moisture sensor support
 * - Fixed battery at 100%
 * - Luminosity in lux
 */

#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <BH1750.h>
#include <DHT.h>
#include <RTClib.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// === Configuration ===
#define NODE_UID "nano1"  // Unique identifier for this node

// === Pin Configuration ===
#define DHTPIN        4     // DHT22 on pin D4
#define DHTTYPE       DHT22
#define SOIL_SENSOR_1 A0    // Soil moisture sensor 1 on A0
#define ONE_WIRE_BUS  3     // DS18B20 on D3

// LoRa SX1278 pins
#define NSS   10  // CS
#define RST   9   // Reset
#define DIO0  2   // Interrupt

// === Message Types ===
#define MSG_TYPE_DATA 1
#define MSG_TYPE_ALERT 2
#define MSG_TYPE_CONFIG 3

// === Sensor instances ===
DHT dht(DHTPIN, DHTTYPE);
BH1750 lightMeter;
RTC_DS3231 rtc;
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature ds18b20(&oneWire);

// === Variables ===
unsigned long lastSendTime = 0;
const unsigned long SEND_INTERVAL = 5000; // Send every 30 seconds
bool hasRTC = false;
bool hasDS18B20 = false;

// Function to get Unix timestamp
unsigned long getTimestamp() {
  if (!hasRTC) {
    return millis() / 1000; // Use seconds since boot if no RTC
  }
  
  DateTime now = rtc.now();
  return now.unixtime();
}

// Function to get battery percentage (fixed at 100%)
int getBatteryPercent() {
  return 100; // Fixed at 100% as no battery monitoring available
}

// Function to format sensor data in protocol format
void formatSensorData(char* buffer, size_t bufferSize) {
  // Read all sensors
  float tempAir = dht.readTemperature();
  float humAir = dht.readHumidity();
  float light = lightMeter.readLightLevel();
  
  // Read soil temperature from DS18B20
  float tempSoil = -999.0;
  if (hasDS18B20) {
    ds18b20.requestTemperatures();
    tempSoil = ds18b20.getTempCByIndex(0);
    // Check if reading is valid (-127.0 is the error value)
    if (tempSoil == -127.0 || tempSoil == 85.0) {  // 85.0 is also an error reading
      tempSoil = -999.0;
    }
  }
  
  // Read soil sensor
  int soilRaw1 = analogRead(SOIL_SENSOR_1);
  int soilPercent1 = map(soilRaw1, 1023, 0, 0, 100);
  
  // Get battery (fixed at 100%)
  int battery = getBatteryPercent();
  
  // Format data string
  // Example: 1B100:1TA21:1TS22:1HA65:1HS45:1L114
  char dataStr[100] = "";
  char temp[20];
  bool firstSensor = true;
  
  // Battery (always 100)
  snprintf(temp, sizeof(temp), "1B%d", battery);
  strcat(dataStr, temp);
  firstSensor = false;
  
  // Temperature Air
  if (!firstSensor) strcat(dataStr, ":");
  if (!isnan(tempAir)) {
    snprintf(temp, sizeof(temp), "1TA%d", (int)round(tempAir));
  } else {
    snprintf(temp, sizeof(temp), "1TAERR");
  }
  strcat(dataStr, temp);
  
  // Temperature Sol (from DS18B20)
  if (!firstSensor) strcat(dataStr, ":");
  if (tempSoil != -999.0 && !isnan(tempSoil)) {
    snprintf(temp, sizeof(temp), "1TS%d", (int)round(tempSoil));
  } else if (hasDS18B20) {
    snprintf(temp, sizeof(temp), "1TSERR");
  } else {
    // If no DS18B20, use air temperature as fallback
    if (!isnan(tempAir)) {
      snprintf(temp, sizeof(temp), "1TS%d", (int)round(tempAir));
    } else {
      snprintf(temp, sizeof(temp), "1TSERR");
    }
  }
  strcat(dataStr, temp);
  
  // Humidity Air
  if (!firstSensor) strcat(dataStr, ":");
  if (!isnan(humAir)) {
    snprintf(temp, sizeof(temp), "1HA%d", (int)round(humAir));
  } else {
    snprintf(temp, sizeof(temp), "1HAERR");
  }
  strcat(dataStr, temp);
  
  // Humidity Sol 1
  if (!firstSensor) strcat(dataStr, ":");
  snprintf(temp, sizeof(temp), "1HS%d", soilPercent1);
  strcat(dataStr, temp);
  
  // Luminosity - send raw lux value
  if (!firstSensor) strcat(dataStr, ":");
  if (light >= 0) {
    snprintf(temp, sizeof(temp), "1L%d", (int)round(light));
  } else {
    snprintf(temp, sizeof(temp), "1LERR");
  }
  strcat(dataStr, temp);
  
  // Copy to buffer
  strncpy(buffer, dataStr, bufferSize - 1);
  buffer[bufferSize - 1] = '\0';
}

void setup() {
  Serial.begin(9600);
  while (!Serial && millis() < 3000) {
    delay(10);
  }
  
  Serial.println(F("Garden IoT - Arduino Nano v2.2"));
  Serial.println(F("=============================="));
  Serial.print(F("Node UID: "));
  Serial.println(NODE_UID);
  Serial.println(F("Protocol: XXXXB|Type|Timestamp|UID|Data|E"));
  
  // Initialize I2C
  Wire.begin();
  Serial.println(F("I2C initialized"));
  
  // Initialize RTC
  if (!rtc.begin()) {
    Serial.println(F("RTC not detected - using millis()"));
    hasRTC = false;
  } else {
    Serial.println(F("RTC OK"));
    hasRTC = true;
    
    // Check if RTC lost power
    if (rtc.lostPower()) {
      Serial.println(F("RTC lost power, setting to compile time"));
      rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
    }
    
    // Display current time
    DateTime now = rtc.now();
    Serial.print(F("RTC Time: "));
    Serial.print(now.year());
    Serial.print('-');
    if (now.month() < 10) Serial.print('0');
    Serial.print(now.month());
    Serial.print('-');
    if (now.day() < 10) Serial.print('0');
    Serial.print(now.day());
    Serial.print(' ');
    if (now.hour() < 10) Serial.print('0');
    Serial.print(now.hour());
    Serial.print(':');
    if (now.minute() < 10) Serial.print('0');
    Serial.print(now.minute());
    Serial.print(':');
    if (now.second() < 10) Serial.print('0');
    Serial.println(now.second());
  }
  
  // Initialize BH1750
  if (!lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
    Serial.println(F("BH1750 not detected!"));
  } else {
    Serial.println(F("BH1750 OK"));
  }
  
  // Initialize DHT22
  dht.begin();
  Serial.println(F("DHT22 OK"));
  
  // Initialize DS18B20
  ds18b20.begin();
  int deviceCount = ds18b20.getDeviceCount();
  if (deviceCount > 0) {
    hasDS18B20 = true;
    Serial.print(F("DS18B20 OK - Found "));
    Serial.print(deviceCount);
    Serial.println(F(" device(s)"));
  } else {
    hasDS18B20 = false;
    Serial.println(F("DS18B20 not detected - using DHT22 for soil temp"));
  }
  
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
  
  Serial.println(F("=============================="));
  Serial.println(F("Setup complete!"));
  Serial.println();
}

void loop() {
  unsigned long currentTime = millis();
  
  // Check if it's time to send
  if (currentTime - lastSendTime >= SEND_INTERVAL) {
    lastSendTime = currentTime;
    
    // Get timestamp
    unsigned long timestamp = getTimestamp();
    
    // Format sensor data
    char sensorData[100];
    formatSensorData(sensorData, sizeof(sensorData));
    
    // Create message in protocol format
    // XXXXB|Type|Timestamp|UID|Data|E
    char message[200];
    snprintf(message, sizeof(message), 
      "XXXXB|%d|%lu|%s|%s|E",
      MSG_TYPE_DATA, timestamp, NODE_UID, sensorData);
    
    // Display on serial
    Serial.println(F("------------------------"));
    Serial.print(F("TX: "));
    Serial.println(message);
    
    // Send via LoRa
    Serial.print(F("Sending... "));
    LoRa.beginPacket();
    LoRa.print(message);
    int result = LoRa.endPacket(false);
    
    if (result == 1) {
      Serial.println(F("SUCCESS"));
    } else {
      Serial.print(F("FAILED ("));
      Serial.print(result);
      Serial.println(F(")"));
    }
    
    // Display parsed data for debugging
    Serial.println(F("Sensor readings:"));
    Serial.print(F("  Battery: "));
    Serial.print(getBatteryPercent());
    Serial.println(F("% (fixed)"));
    
    float temp = dht.readTemperature();
    float hum = dht.readHumidity();
    if (!isnan(temp)) {
      Serial.print(F("  Temp Air: "));
      Serial.print(temp);
      Serial.println(F("°C"));
    }
    if (!isnan(hum)) {
      Serial.print(F("  Humidity Air: "));
      Serial.print(hum);
      Serial.println(F("%"));
    }
    
    // Soil temperature
    if (hasDS18B20) {
      ds18b20.requestTemperatures();
      float tempS = ds18b20.getTempCByIndex(0);
      if (tempS != -127.0 && tempS != 85.0) {  // Check for error values
        Serial.print(F("  Temp Soil: "));
        Serial.print(tempS);
        Serial.println(F("°C"));
      }
    }
    
    float lux = lightMeter.readLightLevel();
    if (lux >= 0) {
      Serial.print(F("  Light: "));
      Serial.print(lux);
      Serial.println(F(" lux"));
    }
    
    int soil1 = map(analogRead(SOIL_SENSOR_1), 1023, 0, 0, 100);
    Serial.print(F("  Soil Moisture: "));
    Serial.print(soil1);
    Serial.println(F("%"));
  }
}
