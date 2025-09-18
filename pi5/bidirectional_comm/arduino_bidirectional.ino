// Arduino LoRa Bidirectional Communication
// Alternates between send and receive modes

#include <SPI.h>
#include <LoRa.h>

// Pin definitions for LoRa module
#define NSS_PIN 10
#define RST_PIN 9
#define DIO0_PIN 2

int messageCount = 0;
unsigned long lastModeSwitch = 0;
bool receiveMode = true;

void setup() {
  Serial.begin(9600);
  while (!Serial);

  Serial.println("LoRa Bidirectional Communication");

  // Setup LoRa
  LoRa.setPins(NSS_PIN, RST_PIN, DIO0_PIN);

  if (!LoRa.begin(433E6)) {  // Changed to 433 MHz to match Pi
    Serial.println("LoRa init failed!");
    while (1);
  }

  LoRa.setTxPower(20);
  Serial.println("LoRa initialized successfully");
  Serial.println("Starting: Send -> Receive (2s) -> Send -> Receive (2s)...");
}

void loop() {
  unsigned long currentTime = millis();

  if (receiveMode) {
    // RECEIVE MODE - Listen for 2 seconds
    if (currentTime - lastModeSwitch < 2000) {
      int packetSize = LoRa.parsePacket();
      if (packetSize) {
        String message = "";
        while (LoRa.available()) {
          message += (char)LoRa.read();
        }
        int rssi = LoRa.packetRssi();
        Serial.print("Received: ");
        Serial.print(message);
        Serial.print(" (RSSI: ");
        Serial.print(rssi);
        Serial.println(")");
      }
    } else {
      // Switch to send mode
      receiveMode = false;
      lastModeSwitch = currentTime;
      Serial.println("\n--- SEND MODE ---");
    }
  } else {
    // SEND MODE - Send one message then switch back
    messageCount++;
    String message = "Arduino Message #" + String(messageCount);

    LoRa.beginPacket();
    LoRa.print(message);
    LoRa.endPacket(false);  // Use non-blocking mode to prevent freezing

    Serial.print("Sent: ");
    Serial.println(message);

    // Switch back to receive mode
    receiveMode = true;
    lastModeSwitch = currentTime;
    Serial.println("--- RECEIVE MODE ---");

    // Small delay before receiving
    delay(500);
  }
}