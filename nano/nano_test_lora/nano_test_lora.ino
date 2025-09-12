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
const unsigned long SEND_INTERVAL = 3000; // 3 seconds - plus fréquent

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000) delay(10);
  
  Serial.println("=== Nano LoRa Test ===");
  
  // Initialize LoRa
  LoRa.setPins(NSS, RST, DIO0);
  
  if (!LoRa.begin(433E6)) {
    Serial.println("LoRa init failed!");
    while (1) delay(1000);
  }
  
  // EXACT same configuration as working v3
  LoRa.setTxPower(14);           
  LoRa.setSpreadingFactor(7);    
  LoRa.setSignalBandwidth(125E3); 
  LoRa.setCodingRate4(5);        
  LoRa.setPreambleLength(8);     
  LoRa.setSyncWord(0x12);        
  
  Serial.println("LoRa configured with v3 settings:");
  Serial.println("  Freq: 433MHz, Power: 14dBm");
  Serial.println("  SF: 7, BW: 125kHz, CR: 4/5");
  Serial.println("  Preamble: 8, Sync: 0x12");
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
  // Check for incoming messages quickly
  checkForMessages();
  
  // Send test message every 3 seconds
  if (millis() - lastSend >= SEND_INTERVAL) {
    lastSend = millis();
    
    Serial.println("==================");
    sendTestMessage();
    
    // Quick check for ACK (no blocking loop)
    Serial.println("Quick ACK check...");
    for (int i = 0; i < 10; i++) {
      checkForMessages();
      delay(100); // Wait 100ms x 10 = 1 second total
    }
    Serial.println("==================");
  }
  
  delay(50); // Shorter delay for more responsive checking
}