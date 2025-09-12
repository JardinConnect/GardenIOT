/*
 * Garden IoT - Arduino Nano LoRa v3
 * Version: 3.0 - ACK Support
 * 
 * Features:
 * - RTC DS3231 support with timestamp
 * - Protocol format: XXXXB|Type|Timestamp|UID|Data|E
 * - DS18B20 for real soil temperature
 * - Bidirectional communication with ACK system
 * - Message retransmission on timeout
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
#define MSG_TYPE_ACK 2
#define MSG_TYPE_ALERT 3
#define MSG_TYPE_CONFIG 4
#define MSG_TYPE_ERROR 5

// === ACK Configuration ===
#define ACK_TIMEOUT 10000  // 10 seconds to wait for ACK
#define MAX_RETRIES 3      // Maximum retransmission attempts

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

// ACK system variables
unsigned long lastMessageId = 0;
unsigned long lastTransmitTime = 0;
bool waitingForAck = false;
int retryCount = 0;
String lastMessage = "";

// Function to generate unique message ID
unsigned long generateMessageId() {
  return ++lastMessageId;
}

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
    if (tempSoil == -127.0 || tempSoil == 85.0) {
      tempSoil = -999.0;
    }
  }
  
  // Read soil sensor
  int soilRaw1 = analogRead(SOIL_SENSOR_1);
  int soilPercent1 = map(soilRaw1, 1023, 0, 0, 100);
  
  // Get battery (fixed at 100%)
  int battery = getBatteryPercent();
  
  // Format data string: 1B100:1TA21:1TS22:1HA65:1HS45:1L114
  char dataStr[100] = "";
  char temp[20];
  bool firstSensor = true;
  
  // Battery
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
  
  // Temperature Sol
  if (!firstSensor) strcat(dataStr, ":");
  if (tempSoil != -999.0 && !isnan(tempSoil)) {
    snprintf(temp, sizeof(temp), "1TS%d", (int)round(tempSoil));
  } else if (hasDS18B20) {
    snprintf(temp, sizeof(temp), "1TSERR");
  } else {
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
  
  // Humidity Sol
  if (!firstSensor) strcat(dataStr, ":");
  snprintf(temp, sizeof(temp), "1HS%d", soilPercent1);
  strcat(dataStr, temp);
  
  // Luminosity
  if (!firstSensor) strcat(dataStr, ":");
  if (light >= 0) {
    snprintf(temp, sizeof(temp), "1L%d", (int)round(light));
  } else {
    snprintf(temp, sizeof(temp), "1LERR");
  }
  strcat(dataStr, temp);
  
  strncpy(buffer, dataStr, bufferSize - 1);
  buffer[bufferSize - 1] = '\0';
}

// Function to send message with ACK system
bool sendMessageWithAck(int msgType, const char* data, unsigned long msgId) {
  char message[200];
  snprintf(message, sizeof(message), 
    "XXXXB|%d|%lu|%s|%lu|%s|E",
    msgType, getTimestamp(), NODE_UID, msgId, data);
  
  Serial.print(F("TX: "));
  Serial.println(message);
  
  LoRa.beginPacket();
  LoRa.print(message);
  int result = LoRa.endPacket(false);
  
  if (result == 1) {
    Serial.println(F("Sent successfully"));
    return true;
  } else {
    Serial.print(F("Send failed ("));
    Serial.print(result);
    Serial.println(F(")"));
    return false;
  }
}

// Function to parse incoming messages (ACK and ERROR)
int parseIncomingMessage(String message, unsigned long* msgId, String* errorType) {
  // Expected formats: 
  // ACK: XXXXB|2|timestamp|pi5|msgId|E
  // ERROR: XXXXB|5|timestamp|pi5|msgId|errorData|E
  
  int firstPipe = message.indexOf('|');
  if (firstPipe == -1) return 0;
  
  int secondPipe = message.indexOf('|', firstPipe + 1);
  if (secondPipe == -1) return 0;
  
  String msgTypeStr = message.substring(firstPipe + 1, secondPipe);
  int msgType = msgTypeStr.toInt();
  
  if (msgType == MSG_TYPE_ACK) {
    // Find the message ID (5th field for ACK)
    int pipeCount = 0;
    int startPos = 0;
    for (int i = 0; i < message.length() && pipeCount < 4; i++) {
      if (message.charAt(i) == '|') {
        pipeCount++;
        if (pipeCount == 4) startPos = i + 1;
      }
    }
    
    if (pipeCount == 4) {
      int endPos = message.indexOf('|', startPos);
      if (endPos == -1) endPos = message.indexOf('E', startPos);
      if (endPos > startPos) {
        *msgId = message.substring(startPos, endPos).toInt();
        return MSG_TYPE_ACK;
      }
    }
  }
  else if (msgType == MSG_TYPE_ERROR) {
    // Find the error data (6th field for ERROR)
    int pipeCount = 0;
    int startPos = 0;
    for (int i = 0; i < message.length() && pipeCount < 5; i++) {
      if (message.charAt(i) == '|') {
        pipeCount++;
        if (pipeCount == 5) startPos = i + 1;
      }
    }
    
    if (pipeCount == 5) {
      int endPos = message.indexOf('|', startPos);
      if (endPos == -1) endPos = message.indexOf('E', startPos);
      if (endPos > startPos) {
        *errorType = message.substring(startPos, endPos);
        return MSG_TYPE_ERROR;
      }
    }
  }
  
  return 0; // Unknown or malformed message
}

// Function to check for incoming messages with timeout
bool checkIncomingMessages(unsigned long timeoutMs = 5000) {
  unsigned long startTime = millis();
  
  while (millis() - startTime < timeoutMs) {
    int packetSize = LoRa.parsePacket();
    if (packetSize > 0) {
      String received = "";
      while (LoRa.available()) {
        received += (char)LoRa.read();
      }
      
      Serial.print(F("RX: "));
      Serial.println(received);
      
      // Parse incoming message
      unsigned long msgId;
      String errorType;
      int msgType = parseIncomingMessage(received, &msgId, &errorType);
      
      if (msgType == MSG_TYPE_ACK) {
        if (waitingForAck && msgId == lastMessageId) {
          Serial.print(F("✓ ACK received for message "));
          Serial.println(msgId);
          waitingForAck = false;
          retryCount = 0;
          return true; // ACK received
        } else {
          Serial.print(F("⚠ Unexpected ACK for message "));
          Serial.println(msgId);
        }
      }
      else if (msgType == MSG_TYPE_ERROR) {
        Serial.print(F("❌ ERROR received from Pi5: "));
        Serial.println(errorType);
        
        // If we're waiting for ACK and got an error instead, stop waiting
        if (waitingForAck) {
          Serial.println(F("❌ Stopping ACK wait due to format error"));
          waitingForAck = false;
          retryCount = 0;
          return false;
        }
      }
    }
    delay(10); // Small delay to prevent CPU hogging
  }
  
  return false; // Timeout reached
}

void setup() {
  Serial.begin(9600);
  while (!Serial && millis() < 3000) {
    delay(10);
  }
  
  Serial.println(F("Garden IoT - Arduino Nano v3.0"));
  Serial.println(F("==============================="));
  Serial.print(F("Node UID: "));
  Serial.println(NODE_UID);
  Serial.println(F("Protocol: XXXXB|Type|Timestamp|UID|MsgId|Data|E"));
  Serial.println(F("ACK Support: Enabled"));
  
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
    
    if (rtc.lostPower()) {
      Serial.println(F("RTC lost power, setting to compile time"));
      rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
    }
    
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
  
  // Initialize LoRa
  Serial.println(F("Initializing LoRa..."));
  LoRa.setPins(NSS, RST, DIO0);
  
  if (!LoRa.begin(433E6)) {
    Serial.println(F("LoRa init failed!"));
    while (1) delay(1000);
  }
  
  Serial.println(F("LoRa OK"));
  LoRa.setTxPower(14);
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  
  Serial.println(F("==============================="));
  Serial.println(F("Setup complete!"));
  Serial.println();
}

void loop() {
  unsigned long currentTime = millis();
  
  // Handle ACK timeout and retries
  if (waitingForAck && (currentTime - lastTransmitTime) > ACK_TIMEOUT) {
    Serial.println(F("⚠ ACK timeout"));
    
    if (retryCount < MAX_RETRIES) {
      retryCount++;
      Serial.print(F("🔄 Retry "));
      Serial.print(retryCount);
      Serial.print(F("/"));
      Serial.println(MAX_RETRIES);
      
      // Resend the last message
      LoRa.beginPacket();
      LoRa.print(lastMessage);
      LoRa.endPacket(false);
      lastTransmitTime = currentTime;
    } else {
      Serial.println(F("❌ Max retries reached, giving up"));
      waitingForAck = false;
      retryCount = 0;
    }
  }
  
  // Send new data if not waiting for ACK and interval passed
  if (!waitingForAck && (currentTime - lastSendTime) >= SEND_INTERVAL) {
    lastSendTime = currentTime;
    
    // Format sensor data
    char sensorData[100];
    formatSensorData(sensorData, sizeof(sensorData));
    
    // Generate message ID
    unsigned long msgId = generateMessageId();
    
    // Create message
    char message[200];
    snprintf(message, sizeof(message), 
      "XXXXB|%d|%lu|%s|%lu|%s|E",
      MSG_TYPE_DATA, getTimestamp(), NODE_UID, msgId, sensorData);
    
    lastMessage = String(message);
    
    Serial.println(F("------------------------"));
    if (sendMessageWithAck(MSG_TYPE_DATA, sensorData, msgId)) {
      waitingForAck = true;
      retryCount = 0;
      lastTransmitTime = currentTime;
      
      // Wait for ACK with 5 second timeout
      Serial.println(F("⏰ Waiting for ACK (5s timeout)..."));
      if (checkIncomingMessages(5000)) {
        Serial.println(F("✅ Message acknowledged successfully"));
      } else {
        Serial.println(F("⏰ ACK timeout - retransmitting immediately"));
        
        // Immediate retry on timeout
        if (retryCount < MAX_RETRIES) {
          retryCount++;
          Serial.print(F("🔄 Immediate retry "));
          Serial.print(retryCount);
          Serial.print(F("/"));
          Serial.println(MAX_RETRIES);
          
          // Resend immediately
          LoRa.beginPacket();
          LoRa.print(lastMessage);
          LoRa.endPacket(false);
          
          // Wait again for ACK
          if (checkIncomingMessages(5000)) {
            Serial.println(F("✅ Retry successful - ACK received"));
            waitingForAck = false;
            retryCount = 0;
          } else {
            Serial.println(F("⏰ Retry also timed out"));
          }
        } else {
          Serial.println(F("❌ Max retries reached"));
          waitingForAck = false;
          retryCount = 0;
        }
      }
    }
    
    // Display sensor readings
    Serial.println(F("Sensor readings:"));
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
    
    if (hasDS18B20) {
      ds18b20.requestTemperatures();
      float tempS = ds18b20.getTempCByIndex(0);
      if (tempS != -127.0 && tempS != 85.0) {
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
  
  // Quick check for any pending messages when not actively waiting
  if (!waitingForAck) {
    checkIncomingMessages(100); // Quick 100ms check
  }
}
