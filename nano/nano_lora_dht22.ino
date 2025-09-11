#include <SPI.h>
#include <LoRa.h>
#include <DHT22.h>

// === Configuration ===
const char SENSOR_ID[] = "NANO_01";

// DHT22
#define DHTPIN 4

// LoRa SX1278
#define NSS 10
#define RST 9
#define DIO0 2

DHT22 dht(DHTPIN);

void setup() {
  Serial.begin(115200);
  
  // Initialisation DHT22 (pas de begin() nécessaire avec DHT22.h)
  Serial.println("✅ DHT22 OK");
  
  // Initialisation LoRa
  Serial.println("📡 Initialisation LoRa...");
  LoRa.setPins(NSS, RST, DIO0);
  
  if (!LoRa.begin(433E6)) {
    Serial.println("❌ Erreur init LoRa!");
    while (1);
  }
  
  Serial.println("✅ LoRa OK");
}

void loop() {
  // Lecture DHT22
  float temperature = dht.getTemperature();
  float humidity = dht.getHumidity();
  
  // Lecture du capteur (retourne 0 si succès)
  int status = dht.readData();
  
  // Vérification du statut
  if (status != 0) {
    Serial.print("❌ Erreur lecture DHT22, code: ");
    Serial.println(status);
    delay(2000);
    return;
  }
  
  // Récupération des valeurs après lecture réussie
  temperature = dht.getTemperature();
  humidity = dht.getHumidity();
  
  // Conversion en strings
  char tempStr[10], humStr[10];
  dtostrf(temperature, 6, 2, tempStr);
  dtostrf(humidity, 6, 2, humStr);
  
  // Debug
  Serial.println("🔍 Mesures:");
  Serial.print("🤖 ID: "); Serial.println(SENSOR_ID);
  Serial.print("🌡 Temp: "); Serial.print(tempStr); Serial.println("°C");
  Serial.print("💧 Hum: "); Serial.print(humStr); Serial.println("%");
  
  // Construction message
  char message[50];
  snprintf(message, sizeof(message),
    "DATA:%s,T:%s,H:%s",
    SENSOR_ID,
    tempStr,
    humStr
  );
  
  Serial.print("📡 Envoi: ");
  Serial.println(message);
  
  // Envoi LoRa
  LoRa.beginPacket();
  LoRa.write((uint8_t*)message, strlen(message));
  LoRa.endPacket();
  
  Serial.println("✅ Envoyé!");
  Serial.println("-------------------");
  
  delay(5000); // Envoi toutes les 5 secondes
}