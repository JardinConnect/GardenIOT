/*
 * Arduino Nano LoRa Bidirectional Test
 * Version: Full Duplex Communication Test
 * 
 * Features:
 * - Sends periodic messages to Pi5
 * - Listens for messages from Pi5
 * - No ACK logic - pure bidirectional testing
 * - SX1278 @ 433 MHz
 */

#include <SPI.h>
#include <LoRa.h>

// LoRa pins
#define NSS   10
#define RST   9
#define DIO0  2

// Node info
#define NODE_ID "nano1"

// Timing
unsigned long lastSendTime = 0;
unsigned long sendInterval = 500;  // Send every 5 seconds
unsigned long msgCount = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000) delay(10);
  
  Serial.println("=================================");
  Serial.println("Arduino Nano LoRa Bidirectional");
  Serial.println("=================================");
  Serial.print("Node ID: ");
  Serial.println(NODE_ID);
  
  // Initialize LoRa with exact same config as Pi5
  LoRa.setPins(NSS, RST, DIO0);
  
  if (!LoRa.begin(433E6)) {
    Serial.println("❌ LoRa init failed!");
    while (1) delay(1000);
  }
  
  // Configuration matching Pi5
  LoRa.setTxPower(14);
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);
  LoRa.setPreambleLength(8);
  LoRa.setSyncWord(0x12);
  
  Serial.println("✅ LoRa configured:");
  Serial.println("   Freq: 433MHz, Power: 14dBm");
  Serial.println("   SF: 7, BW: 125kHz, CR: 4/5");
  Serial.println("=================================");
  Serial.println("🔄 Starting bidirectional test...");
  Serial.println();
}

void sendMessage() {
  msgCount++;
  
  // Format: NANO_MSG|count|nodeId|timestamp
  // Add padding for LoRa offset compensation
  String message = String("XXXXNANO_MSG|") + 
                  String(msgCount) + "|" + 
                  String(NODE_ID) + "|" + 
                  String(millis());
  
  Serial.print("📤 TX: ");
  Serial.println(message);
  
  // Send message
  LoRa.beginPacket();
  LoRa.print(message);
  int result = LoRa.endPacket(false); // Non-blocking
  
  if (result == 1) {
    Serial.println("   ✅ Sent successfully");
  } else {
    Serial.print("   ❌ Send failed: ");
    Serial.println(result);
  }
  
  lastSendTime = millis();
}

void listenForMessages() {
  int packetSize = LoRa.parsePacket();
  
  if (packetSize > 0) {
    String received = "";
    
    // Read all available bytes
    while (LoRa.available()) {
      char c = LoRa.read();
      if (c >= 32 && c <= 126) { // Only printable characters
        received += c;
      }
    }
    
    if (received.length() > 0) {
      int rssi = LoRa.packetRssi();
      float snr = LoRa.packetSnr();
      
      Serial.print("📥 RX: ");
      Serial.println(received);
      Serial.print("   📶 RSSI: ");
      Serial.print(rssi);
      Serial.print(" dBm, SNR: ");
      Serial.print(snr);
      Serial.println(" dB");
      
      // Parse message if it's from Pi5
      if (received.startsWith("PI5_MSG|")) {
        Serial.println("   ✅ Valid Pi5 message received!");
        
        // Extract parts: PI5_MSG|count|nodeId|timestamp
        int firstPipe = received.indexOf('|');
        int secondPipe = received.indexOf('|', firstPipe + 1);
        int thirdPipe = received.indexOf('|', secondPipe + 1);
        
        if (firstPipe > 0 && secondPipe > 0 && thirdPipe > 0) {
          String msgNum = received.substring(firstPipe + 1, secondPipe);
          String nodeId = received.substring(secondPipe + 1, thirdPipe);
          String timestamp = received.substring(thirdPipe + 1);
          
          Serial.print("   📊 Message #");
          Serial.print(msgNum);
          Serial.print(" from ");
          Serial.print(nodeId);
          Serial.print(" at ");
          Serial.println(timestamp);
        }
      } else {
        Serial.println("   ⚠️ Unknown message format");
      }
      Serial.println();
    }
  }
}

void loop() {
  // Always listen for incoming messages
  listenForMessages();
  
  // Send periodic messages
  if (millis() - lastSendTime >= sendInterval) {
    sendMessage();
    Serial.println();
  }
  
  // Small delay to prevent CPU hogging
  delay(10);
}

// Functions to send different types of messages on demand
void sendHeartbeat() {
  String message = String("XXXXHEARTBEAT|") + String(NODE_ID) + "|" + String(millis());
  
  Serial.print("💓 Heartbeat: ");
  Serial.println(message);
  
  LoRa.beginPacket();
  LoRa.print(message);
  LoRa.endPacket(false);
}

void sendSensorData(float temp, float humidity) {
  String message = String("XXXXSENSOR|") + 
                  String(NODE_ID) + "|" + 
                  String("T:") + String(temp, 1) + "|" + 
                  String("H:") + String(humidity, 1);
  
  Serial.print("🌡️ Sensor data: ");
  Serial.println(message);
  
  LoRa.beginPacket();
  LoRa.print(message);
  LoRa.endPacket(false);
}
