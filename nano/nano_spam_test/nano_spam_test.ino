/*
 * Arduino Nano LoRa SPAM Test
 * Envoie en continu pour tester la réception
 */

#include <SPI.h>
#include <LoRa.h>

// LoRa pins
#define NSS   10
#define RST   9
#define DIO0  2

unsigned long msgCount = 0;
bool waitingForAck = false;
unsigned long lastSendTime = 0;
unsigned long currentMsgId = 0;
const unsigned long ACK_RETRY_INTERVAL = 1000;  // 1 second retry
const unsigned long NORMAL_INTERVAL = 10000;    // 10 seconds normal

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000) delay(10);
  
  Serial.println("=== NANO SPAM TEST ===");
  
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
  LoRa.setCodingRate4(5);        // This was missing!
  LoRa.setPreambleLength(8);     // This was missing!
  LoRa.setSyncWord(0x12);        // This was missing!
  
  Serial.println("LoRa configured with v3 settings:");
  Serial.println("  Freq: 433MHz, Power: 14dBm");
  Serial.println("  SF: 7, BW: 125kHz, CR: 4/5");
  Serial.println("  Preamble: 8, Sync: 0x12");
  Serial.println("Starting SPAM...");
  Serial.println("====================");
}

void sendMessage() {
  msgCount++;
  currentMsgId = msgCount;
  
  // Add 4 chars padding + proper format for Pi5 parser
  String msg = String("XXXXTEST|") + String(msgCount) + String("|nano1");
  
  Serial.print("TX #");
  Serial.print(msgCount);
  Serial.print(": ");
  Serial.println(msg);
  
  // Send
  LoRa.beginPacket();
  LoRa.print(msg);
  int result = LoRa.endPacket();
  
  Serial.print("  Result: ");
  Serial.println(result);
  
  if (result == 1) {
    waitingForAck = true;
    lastSendTime = millis();
    Serial.println("  Waiting for ACK...");
  }
}

void checkForAck() {
  int packetSize = LoRa.parsePacket();
  if (packetSize > 0) {
    String received = "";
    while (LoRa.available()) {
      char c = LoRa.read();
      if (c >= 32 && c <= 126) { // Printable chars only
        received += c;
      }
    }
    
    Serial.print("RX: ");
    Serial.println(received);
    
    // Check if it's ACK for current message: ACK|msgId|nano1
    String expectedAck = String("ACK|") + String(currentMsgId) + String("|nano1");
    if (received == expectedAck) {
      Serial.println("  ✓ ACK received! Next message in 10 seconds");
      waitingForAck = false;
    } else {
      Serial.println("  ⚠ Unknown or wrong ACK");
    }
  }
}

void loop() {
  // Always check for incoming ACKs
  checkForAck();
  
  unsigned long currentTime = millis();
  unsigned long interval = waitingForAck ? ACK_RETRY_INTERVAL : NORMAL_INTERVAL;
  
  // Send message based on current state
  if (currentTime - lastSendTime >= interval) {
    if (waitingForAck) {
      Serial.print("⚠ ACK timeout - retry #");
      Serial.println(msgCount);
      
      // Resend same message (don't increment msgCount)
      String msg = String("XXXXTEST|") + String(currentMsgId) + String("|nano1");
      
      Serial.print("RETRY: ");
      Serial.println(msg);
      
      LoRa.beginPacket();
      LoRa.print(msg);
      int result = LoRa.endPacket();
      
      Serial.print("  Result: ");
      Serial.println(result);
      
      lastSendTime = currentTime;
    } else {
      // Send new message
      sendMessage();
    }
  }
  
  delay(50); // Small delay for responsiveness
}