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
unsigned long ackWaitStart = 0;     // When we started waiting for ACK
unsigned long currentMsgId = 0;
const unsigned long ACK_RETRY_INTERVAL = 1000;  // 1 second retry
const unsigned long NORMAL_INTERVAL = 10000;    // 10 seconds normal
const unsigned long ACK_TIMEOUT = 5000;         // 5 seconds timeout for ACK

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
  Serial.println("Starting smart ACK test...");
  Serial.println("- New messages every 10s");
  Serial.println("- Retries every 1s until ACK");
  Serial.println("====================");
  
  // Initialize timing
  lastSendTime = millis();
  waitingForAck = false;
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
    
    Serial.print("RX: '");
    Serial.print(received);
    Serial.print("' (");
    Serial.print(received.length());
    Serial.println(" chars)");
    
    // Check if it's ACK for current message: ACK|msgId|nano1
    String expectedAck = String("ACK|") + String(currentMsgId) + String("|nano1");
    Serial.print("  Expected: '");
    Serial.print(expectedAck);
    Serial.println("'");
    
    if (received == expectedAck) {
      Serial.println("  ✓ ACK received! Next message in 10 seconds");
      waitingForAck = false;
      ackWaitStart = 0;  // Reset timeout
    } else {
      Serial.println("  ⚠ ACK mismatch or unknown message");
    }
  }
}

void loop() {
  unsigned long currentTime = millis();
  
  // Always check for ACKs
  checkForAck();
  
  // TIMEOUT CHECK: Reset waitingForAck if no ACK received in time
  if (waitingForAck && (currentTime - ackWaitStart) > ACK_TIMEOUT) {
    Serial.println("⏰ ACK timeout - giving up, sending new message");
    waitingForAck = false;
    ackWaitStart = 0;
  }
  
  // Send timing logic
  unsigned long interval = waitingForAck ? ACK_RETRY_INTERVAL : NORMAL_INTERVAL;
  
  if (currentTime - lastSendTime >= interval) {
    // Decide what to send
    if (!waitingForAck) {
      // New message
      msgCount++;
      currentMsgId = msgCount;
      Serial.print("TX #");
    } else {
      // Retry same message
      Serial.print("RETRY #");
    }
    
    String msg = String("XXXXTEST|") + String(currentMsgId) + String("|nano1");
    Serial.print(currentMsgId);
    Serial.print(": ");
    Serial.println(msg);
    
    // Send message
    LoRa.beginPacket();
    LoRa.print(msg);
    int result = LoRa.endPacket();
    
    Serial.print("  Result: ");
    Serial.println(result);
    
    if (result == 1) {
      if (!waitingForAck) {
        // First time sending this message
        waitingForAck = true;
        ackWaitStart = currentTime;  // Start timeout counter
        Serial.println("  Waiting for ACK...");
      }
      lastSendTime = currentTime;
    }
  }
  
  delay(50);
}