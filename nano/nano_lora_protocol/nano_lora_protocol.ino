#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <BH1750.h>
#include <DHT.h>

// === Configuration ===
#define NODE_UID "nano"  // 4 octets UID

// === Pin Configuration ===
#define DHTPIN        4     // DHT22 on pin D4
#define DHTTYPE       DHT22
#define SOIL_SENSOR   A0    // Soil moisture sensor on A0

// LoRa SX1278 pins
#define NSS   10  // CS
#define RST   9   // Reset
#define DIO0  2   // Interrupt

// === Message Types ===
#define MSG_TYPE_DATA  1
#define MSG_TYPE_ALERT 2
#define MSG_TYPE_ERROR 3

// === Sensor Types ===
#define SENSOR_TA "TA"  // Température Air
#define SENSOR_TS "TS"  // Température Sol
#define SENSOR_HA "HA"  // Humidité Air
#define SENSOR_HS "HS"  // Humidité Sol
#define SENSOR_B  "B"   // Batterie
#define SENSOR_L  "L"   // Luminosité

// === Sensor instances ===
DHT dht(DHTPIN, DHTTYPE);
BH1750 lightMeter;

// === Variables ===
unsigned long timestamp = 0;

void setup() {
  Serial.begin(9600);
  while (!Serial) {
    delay(10);
  }
  
  Serial.println(F("Garden IoT - Protocol LoRa"));
  Serial.println(F("==========================="));
  
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
  SPI.begin();
  pinMode(NSS, OUTPUT);
  digitalWrite(NSS, HIGH);
  
  // Reset LoRa module
  pinMode(RST, OUTPUT);
  digitalWrite(RST, LOW);
  delay(10);
  digitalWrite(RST, HIGH);
  delay(10);
  
  // Initialize LoRa
  LoRa.setPins(NSS, RST, DIO0);
  
  if (!LoRa.begin(433E6)) {
    Serial.println(F("LoRa init failed!"));
    while (1) {
      delay(1000);
    }
  }
  
  Serial.println(F("LoRa OK"));
  
  // Configure LoRa
  LoRa.setTxPower(14);
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  
  Serial.println(F("==========================="));
  Serial.println(F("Setup complete!"));
  Serial.println();
}

void loop() {
  // Generate timestamp (simplified - seconds since boot)
  timestamp = millis() / 1000;
  
  // Read sensors
  float tempAir = dht.readTemperature();
  float humAir = dht.readHumidity();
  float light = lightMeter.readLightLevel();
  int soilRaw = analogRead(SOIL_SENSOR);
  
  // Convert soil moisture to percentage (0-100%)
  int soilPercent = map(soilRaw, 1023, 0, 0, 100);
  
  // Convert light to percentage (0-100%)
  // Assuming max 10000 lux for outdoor conditions
  int lightPercent = constrain(map((int)light, 0, 10000, 0, 100), 0, 100);
  
  // Build message according to protocol
  char message[150];
  char dataSection[100];
  
  // Initialize data section
  strcpy(dataSection, "");
  
  // Add Battery (simulate at 85%)
  strcat(dataSection, "1B85");
  
  // Add Temperature Air if valid
  if (!isnan(tempAir)) {
    char tempStr[15];
    snprintf(tempStr, sizeof(tempStr), ":1TA%d", (int)tempAir);
    strcat(dataSection, tempStr);
  } else {
    // Send error for temperature
    sendErrorMessage(SENSOR_TA);
    return;
  }
  
  // Add Temperature Sol (using same as air for now)
  if (!isnan(tempAir)) {
    char tempStr[15];
    snprintf(tempStr, sizeof(tempStr), ":1TS%d", (int)tempAir);
    strcat(dataSection, tempStr);
  }
  
  // Add Humidity Air if valid
  if (!isnan(humAir)) {
    char humStr[15];
    snprintf(humStr, sizeof(humStr), ":1HA%d", (int)humAir);
    strcat(dataSection, humStr);
  } else {
    // Send error for humidity
    sendErrorMessage(SENSOR_HA);
    return;
  }
  
  // Add Humidity Sol
  char soilStr[15];
  snprintf(soilStr, sizeof(soilStr), ":1HS%d", soilPercent);
  strcat(dataSection, soilStr);
  
  // Add Light
  if (light >= 0) {
    char lightStr[15];
    snprintf(lightStr, sizeof(lightStr), ":L%d", lightPercent);
    strcat(dataSection, lightStr);
  }
  
  // Check for alerts
  if (soilPercent < 20) {
    // Send alert for dry soil
    sendAlertMessage(SENSOR_HS, soilPercent);
  }
  
  // Build complete message
  // Format: B|TYPE|TIMESTAMP|UID|DATAS|E
  snprintf(message, sizeof(message), 
    "B|%d|%lu|%s|%s|E",
    MSG_TYPE_DATA,
    timestamp,
    NODE_UID,
    dataSection
  );
  
  // Display on serial
  Serial.print(F("TX: "));
  Serial.println(message);
  
  // Send via LoRa
  Serial.print(F("Sending..."));
  LoRa.beginPacket();
  LoRa.print(message);
  int result = LoRa.endPacket(false);
  
  if (result == 1) {
    Serial.println(F(" SUCCESS"));
  } else {
    Serial.print(F(" FAILED ("));
    Serial.print(result);
    Serial.println(F(")"));
  }
  
  Serial.println(F("------------------------"));
  
  delay(10000); // Send every 10 seconds
}

void sendAlertMessage(const char* sensorType, int value) {
  char message[80];
  
  // Format: B|2|TIMESTAMP|UID|SENSOR_VALUE|E
  snprintf(message, sizeof(message), 
    "B|%d|%lu|%s|%s%d|E",
    MSG_TYPE_ALERT,
    timestamp,
    NODE_UID,
    sensorType,
    value
  );
  
  Serial.print(F("ALERT: "));
  Serial.println(message);
  
  LoRa.beginPacket();
  LoRa.print(message);
  LoRa.endPacket(false);
}

void sendErrorMessage(const char* sensorType) {
  char message[80];
  
  // Format: B|3|TIMESTAMP|UID|SENSOR_ERR|E
  snprintf(message, sizeof(message), 
    "B|%d|%lu|%s|%sERR|E",
    MSG_TYPE_ERROR,
    timestamp,
    NODE_UID,
    sensorType
  );
  
  Serial.print(F("ERROR: "));
  Serial.println(message);
  
  LoRa.beginPacket();
  LoRa.print(message);
  LoRa.endPacket(false);
}
