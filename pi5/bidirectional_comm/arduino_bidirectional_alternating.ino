// Arduino LoRa Bidirectional - Proper Alternating
// Arduino sends FIRST, then listens

#include <SPI.h>
#include <LoRa.h>

#define NSS_PIN 10
#define RST_PIN 9
#define DIO0_PIN 2

int messageCount = 0;
unsigned long lastAction = 0;
bool sendMode = true;  // Start with SEND mode
int packetsReceived = 0;

void setup() {
  Serial.begin(9600);
  while (!Serial);

  Serial.println("Arduino Bidirectional - Alternating Protocol");

  LoRa.setPins(NSS_PIN, RST_PIN, DIO0_PIN);

  if (!LoRa.begin(433E6)) {
    Serial.println("LoRa init failed!");
    while (1);
  }

  LoRa.setTxPower(14);
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);

  Serial.println("Protocol: Arduino SENDS first, Pi receives");
  Serial.println("Then: Pi sends, Arduino receives");
  Serial.println("Starting in SEND mode...");
  lastAction = millis();
}

void loop() {
  unsigned long currentTime = millis();

  if (sendMode) {
    // SEND MODE - Send immediately
    messageCount++;
    String message = "XXXXArduino #" + String(messageCount);

    LoRa.beginPacket();
    LoRa.print(message);
    LoRa.endPacket(false);

    Serial.print("Sent: ");
    Serial.println(message.substring(4));

    // Switch to receive mode for 12 seconds (give Pi time to receive and send back)
    sendMode = false;
    lastAction = currentTime;
    packetsReceived = 0;
    Serial.println("Listening for 12 seconds...");

  } else {
    // RECEIVE MODE - Listen for 12 seconds
    if (currentTime - lastAction < 12000) {
      int packetSize = LoRa.parsePacket();
      if (packetSize) {
        packetsReceived++;
        String message = "";
        while (LoRa.available()) {
          message += (char)LoRa.read();
        }

        if (message.startsWith("XXXX")) {
          message = message.substring(4);
        }

        Serial.print("Received: ");
        Serial.print(message);
        Serial.print(" (RSSI: ");
        Serial.print(LoRa.packetRssi());
        Serial.println(")");
      }
    } else {
      // 12 seconds up, switch back to send mode
      if (packetsReceived == 0) {
        Serial.println("No reply received");
      }

      sendMode = true;
      lastAction = currentTime;
      Serial.println("\nNext send cycle...");
      delay(1000);  // 1 second delay before next send
    }
  }

  delay(10);  // Small delay to prevent CPU overload
}