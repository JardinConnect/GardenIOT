// Arduino LoRa Bidirectional Communication - Debug Version
// Enhanced debugging and sync word configuration

#include <SPI.h>
#include <LoRa.h>

// Pin definitions for LoRa module
#define NSS_PIN 10
#define RST_PIN 9
#define DIO0_PIN 2

int messageCount = 0;
unsigned long lastModeSwitch = 0;
bool receiveMode = true;
int packetsReceived = 0;

void setup() {
  Serial.begin(9600);
  while (!Serial);

  Serial.println("LoRa Bidirectional Communication - Debug");
  Serial.println("=========================================");

  // Setup LoRa
  LoRa.setPins(NSS_PIN, RST_PIN, DIO0_PIN);

  if (!LoRa.begin(433E6)) {
    Serial.println("LoRa init failed!");
    while (1);
  }

  // Configure LoRa parameters to match Pi
  LoRa.setTxPower(14);
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);  // Default coding rate
  LoRa.setSyncWord(0x12);  // Private network sync word (LoRa default)

  Serial.println("LoRa Configuration:");
  Serial.print("  Frequency: 433 MHz\n");
  Serial.print("  TX Power: 14 dBm\n");
  Serial.print("  SF: 7\n");
  Serial.print("  BW: 125 kHz\n");
  Serial.print("  Sync Word: 0x12\n");
  Serial.println("=========================================");
  Serial.println("Starting: Receive (10s) -> Send -> Receive...");
  Serial.println("\n--- RECEIVE MODE ---");
}

void loop() {
  unsigned long currentTime = millis();

  if (receiveMode) {
    // RECEIVE MODE - Listen for 10 seconds
    if (currentTime - lastModeSwitch < 10000) {
      int packetSize = LoRa.parsePacket();
      if (packetSize) {
        packetsReceived++;
        String message = "";
        while (LoRa.available()) {
          message += (char)LoRa.read();
        }
        int rssi = LoRa.packetRssi();
        float snr = LoRa.packetSnr();

        Serial.print("[");
        Serial.print(packetsReceived);
        Serial.print("] Received: ");
        Serial.println(message);
        Serial.print("    RSSI: ");
        Serial.print(rssi);
        Serial.print(" dBm, SNR: ");
        Serial.print(snr);
        Serial.println(" dB");
      }
    } else {
      // Report and switch to send mode
      if (packetsReceived == 0) {
        Serial.println("No packets received in this window");
      }
      packetsReceived = 0;

      receiveMode = false;
      lastModeSwitch = currentTime;
      Serial.println("\n--- SEND MODE ---");
    }
  } else {
    // SEND MODE - Send one message then switch back
    messageCount++;
    String message = "Arduino #" + String(messageCount);

    // Send packet
    LoRa.beginPacket();
    LoRa.print(message);
    LoRa.endPacket(false);  // non-blocking

    Serial.print("Sent: ");
    Serial.println(message);

    // Switch back to receive mode
    receiveMode = true;
    lastModeSwitch = currentTime;
    Serial.println("\n--- RECEIVE MODE (10s) ---");

    // Small delay before receiving
    delay(500);
  }
}