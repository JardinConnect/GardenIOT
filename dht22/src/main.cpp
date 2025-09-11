#include <Arduino.h>
#include <SPI.h>
#include <LoRa.h>
#include <DHT.h>

// === DHT22 ===
#define DHTPIN 2
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

// === LoRa Pins ===
#define SS 10
#define RST 9
#define DIO0 2

// LoRa frequency
#define LORA_FREQ 433E6

int count = 0;

void setup() {
  Serial.begin(9600);
  while (!Serial);

  dht.begin();
  delay(2000);  // Pause initiale

  LoRa.setPins(SS, RST, DIO0);
  if (!LoRa.begin(LORA_FREQ)) {
    Serial.println("Erreur init LoRa");
    while (true);
  }
  LoRa.setTxPower(15); // puissance TX
  Serial.println("LoRa prêt !");
}

void loop() {
  float t = dht.readTemperature();
  float h = dht.readHumidity();

  if (isnan(t) || isnan(h)) {
    Serial.println("Erreur lecture DHT22");
    delay(5000);
    return;
  }

  String msg = "Temp: " + String(t, 1) + " C, Hum: " + String(h, 1) + " %, Count: " + String(count);
  Serial.println("Envoi: " + msg);

  LoRa.beginPacket();
  LoRa.print(msg);
  LoRa.endPacket();

  count++;
  delay(5000);
}
