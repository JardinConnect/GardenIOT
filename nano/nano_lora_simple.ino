#include <SPI.h>
#include <LoRa.h>

void setup() {
  Serial.begin(9600);
  while (!Serial);
  
  Serial.println("Starting LoRa Simple Test");
  
  if (!LoRa.begin(433E6)) {
    Serial.println("LoRa init failed!");
    while (1);
  }
  
  Serial.println("LoRa init OK!");
  Serial.println("Sending test packets...");
}

void loop() {
  static int counter = 0;
  
  Serial.print("Sending packet: ");
  Serial.println(counter);
  
  // Send packet
  LoRa.beginPacket();
  LoRa.print("hello ");
  LoRa.print(counter);
  LoRa.endPacket(); // Mode synchrone par défaut
  
  Serial.println("Packet sent!");
  
  counter++;
  delay(2000);
}