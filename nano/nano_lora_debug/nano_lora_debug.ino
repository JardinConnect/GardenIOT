#include <SPI.h>
#include <LoRa.h>

// LoRa SX1278 pins
#define NSS   10  // CS
#define RST   9   // Reset
#define DIO0  2   // Interrupt

unsigned long count = 0;

void setup() {
  Serial.begin(9600);
  while (!Serial) {
    delay(10);
  }
  
  Serial.println(F("LoRa Debug Test"));
  Serial.println(F("==============="));
  
  // Test SPI communication
  Serial.println(F("Testing SPI..."));
  SPI.begin();
  pinMode(NSS, OUTPUT);
  digitalWrite(NSS, HIGH);
  Serial.println(F("SPI initialized"));
  
  // Reset LoRa module
  Serial.println(F("Resetting LoRa module..."));
  pinMode(RST, OUTPUT);
  digitalWrite(RST, LOW);
  delay(10);
  digitalWrite(RST, HIGH);
  delay(10);
  Serial.println(F("Reset complete"));
  
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
      Serial.println(F("Halted"));
    }
  }
  
  Serial.println(F("LoRa init success!"));
  
  // Configure LoRa
  Serial.print(F("Setting TX Power..."));
  LoRa.setTxPower(14); // Lower power for testing
  Serial.println(F(" OK"));
  
  Serial.print(F("Setting Spreading Factor..."));
  LoRa.setSpreadingFactor(7);
  Serial.println(F(" OK"));
  
  Serial.print(F("Setting Bandwidth..."));
  LoRa.setSignalBandwidth(125E3);
  Serial.println(F(" OK"));
  
  Serial.println(F("==============="));
  Serial.println(F("Setup complete!"));
  Serial.println();
}

void loop() {
  Serial.print(F("Attempt #"));
  Serial.println(count);
  
  // Create simple message
  char message[30];
  snprintf(message, sizeof(message), "Test:%lu", count);
  
  Serial.print(F("Sending: "));
  Serial.println(message);
  
  // Try to send with timeout check
  Serial.println(F("beginPacket()..."));
  int result = LoRa.beginPacket();
  if (result == 0) {
    Serial.println(F("ERROR: beginPacket failed!"));
    delay(5000);
    return;
  }
  Serial.println(F("beginPacket() OK"));
  
  Serial.println(F("Writing data..."));
  size_t written = LoRa.print(message);
  Serial.print(F("Bytes written: "));
  Serial.println(written);
  
  Serial.println(F("endPacket()..."));
  unsigned long startTime = millis();
  
  // endPacket with explicit mode (non-blocking)
  int endResult = LoRa.endPacket(false); // false = async mode
  
  Serial.print(F("endPacket() returned: "));
  Serial.println(endResult);
  
  if (endResult == 1) {
    Serial.println(F("SUCCESS: Packet sent!"));
  } else {
    Serial.println(F("ERROR: Failed to send packet"));
    Serial.print(F("Error code: "));
    Serial.println(endResult);
    
    // Try to get RSSI to check if module is responding
    Serial.print(F("Packet RSSI: "));
    Serial.println(LoRa.packetRssi());
  }
  
  unsigned long endTime = millis();
  Serial.print(F("Time taken: "));
  Serial.print(endTime - startTime);
  Serial.println(F(" ms"));
  
  Serial.println(F("------------------------"));
  Serial.println();
  
  count++;
  delay(3000); // Wait 3 seconds between attempts
}