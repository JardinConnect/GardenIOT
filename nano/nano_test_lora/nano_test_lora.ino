/*
 * Arduino Nano LoRa Communication Test
 * Simple bidirectional test without sensors
 */

#include <SPI.h>
#include <LoRa.h>

// LoRa pins
#define NSS   10
#define RST   9
#define DIO0  2

// Test parameters
#define NODE_ID "nano1"
unsigned long msgCount = 0;
unsigned long lastSend = 0;
const unsigned long SEND_INTERVAL = 10000; // 10 seconds

void setup() {
  Serial.begin(9600);
  while (!Serial && millis() < 3000) delay(10);
  
  Serial.println("=== Nano LoRa Test ===");
  
  // Initialize LoRa
  LoRa.setPins(NSS, RST, DIO0);
  
  if (!LoRa.begin(433E6)) {
    Serial.println("LoRa init failed!");
    while (1) delay(1000);
  }
  
  // EXACT same configuration as Pi5
  LoRa.setTxPower(14);           // Same power
  LoRa.setSpreadingFactor(7);    
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);        
  LoRa.setPreambleLength(8);     
  LoRa.setSyncWord(0x12);        
  
  Serial.println("LoRa configured:");
  Serial.println("  Freq: 433MHz, Power: 14dBm");
  Serial.println("  SF: 7, BW: 125kHz, CR: 4/5");
  Serial.println("========================");
}

void sendTestMessage() {
  msgCount++;
  
  // Simple message format: TEST|msgId|nodeId
  String message = "TEST|" + String(msgCount) + "|" + NODE_ID;
  
  Serial.print("TX: ");
  Serial.println(message);
  Serial.print("Length: ");
  Serial.println(message.length());
  
  // Check LoRa is available
  if (!LoRa.beginPacket()) {
    Serial.println("  -> Cannot begin packet");
    return;
  }
  
  LoRa.print(message);
  int result = LoRa.endPacket(false); // non-blocking
  
  Serial.print("  -> Result: ");
  Serial.println(result);
  
  if (result == 1) {
    Serial.println("  -> Sent OK");
  } else {
    Serial.print("  -> Failed with code: ");
    Serial.println(result);
  }
  
  // Wait a bit after sending
  delay(100);
}

void checkForMessages() {
  int packetSize = LoRa.parsePacket();
  if (packetSize > 0) {
    Serial.print("RX size: ");
    Serial.println(packetSize);
    
    String received = "";
    while (LoRa.available()) {
      char c = LoRa.read();
      if (c >= 32 && c <= 126) { // Printable only
        received += c;
      }
    }
    
    Serial.print("RX: ");
    Serial.println(received);
    Serial.print("RSSI: ");
    Serial.println(LoRa.packetRssi());
    
    // Check if it's an ACK for our message
    if (received.startsWith("ACK|")) {
      Serial.println("  -> ACK received!");
    }
    
    Serial.println("---");
  }
}

void loop() {
  // Check for incoming messages
  checkForMessages();
  
  // Send test message every 10 seconds
  if (millis() - lastSend >= SEND_INTERVAL) {
    lastSend = millis();
    sendTestMessage();
    
    // Wait a bit for potential ACK
    Serial.println("Waiting for ACK...");
    unsigned long ackStart = millis();
    while (millis() - ackStart < 3000) { // 3 second timeout
      checkForMessages();
      delay(50);
    }
    Serial.println("---");
  }
  
  delay(100);
}