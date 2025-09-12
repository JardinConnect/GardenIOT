/*
 * Arduino Nano LoRa Alternative Config Test
 * Test avec paramètres différents pour éviter l'offset
 */

#include <SPI.h>
#include <LoRa.h>

// LoRa pins
#define NSS   10
#define RST   9
#define DIO0  2

unsigned long msgCount = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000) delay(10);
  
  Serial.println("=== NANO ALTERNATE CONFIG TEST ===");
  
  // Initialize LoRa
  LoRa.setPins(NSS, RST, DIO0);
  
  if (!LoRa.begin(433E6)) {
    Serial.println("LoRa init failed!");
    while (1) delay(1000);
  }
  
  // Alternative configuration to avoid offset bug
  LoRa.setTxPower(14);           
  LoRa.setSpreadingFactor(8);     // SF8 instead of SF7
  LoRa.setSignalBandwidth(125E3); 
  LoRa.setCodingRate4(8);         // CR 4/8 instead of 4/5
  LoRa.setPreambleLength(12);     // 12 instead of 8
  LoRa.setSyncWord(0x34);         // Different sync word
  
  Serial.println("Alternative LoRa config:");
  Serial.println("  SF: 8, CR: 4/8, Preamble: 12");
  Serial.println("  Sync: 0x34");
  Serial.println("==================================");
}

void loop() {
  msgCount++;
  
  // Simple message without padding
  String msg = "TEST" + String(msgCount);
  
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
  
  // Wait 3 seconds
  delay(3000);
}