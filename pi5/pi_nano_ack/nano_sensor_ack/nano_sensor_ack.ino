// Nano LoRa Capteur avec ACK - Version Corrigée
// Envoie des mesures et attend l'ACK du Pi5
// Configuration LoRa identique au Pi5

#include <SPI.h>
#include <LoRa.h>

// Pins pour le module LoRa
#define NSS_PIN 10
#define RST_PIN 9
#define DIO0_PIN 2

// Configuration temporelle
const unsigned long ACK_WAIT_TIME = 3000;   // 3 secondes d'attente pour ACK
const unsigned long SUCCESS_DELAY = 10000;   // 10 secondes après ACK reçu
const unsigned long RETRY_DELAY = 3000;      // 3 secondes entre les tentatives

// Variables globales
int messageCount = 0;
unsigned long lastSendTime = 0;
bool waitingForAck = false;
unsigned long ackTimeout = 0;
String lastMessageId = "";

// Mode debug
bool DEBUG = true;

void setup() {
  Serial.begin(9600);
  while (!Serial);
  
  Serial.println("=== Nano Capteur LoRa avec ACK ===");
  Serial.println("Version corrigée avec configuration complète");
  
  // Configuration des pins
  LoRa.setPins(NSS_PIN, RST_PIN, DIO0_PIN);
  
  // Initialisation LoRa
  if (!LoRa.begin(433E6)) {
    Serial.println("❌ Erreur initialisation LoRa!");
    while (1);
  }
  
  // Configuration IDENTIQUE au Pi5
  LoRa.setTxPower(14);
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);           // Important !
  LoRa.setPreambleLength(8);
  LoRa.setSyncWord(0x12);           // Sync word par défaut
  
  Serial.println("✅ LoRa initialisé");
  Serial.println("Configuration: SF=7, BW=125kHz, CR=4/5");
  Serial.println("\nProtocole:");
  Serial.println("- Envoi mesure → Attente ACK (3s)");
  Serial.println("- Si ACK: pause 10s | Sinon: réessai 3s");
  Serial.println("\nDémarrage...\n");
  
  // Attendre un peu avant le premier envoi
  delay(2000);
}

void loop() {
  unsigned long currentTime = millis();
  
  if (!waitingForAck) {
    // Mode envoi - vérifier s'il faut envoyer un message
    unsigned long timeSinceLastSend = currentTime - lastSendTime;
    
    if (timeSinceLastSend >= SUCCESS_DELAY || lastSendTime == 0) {
      sendSensorData();
      waitingForAck = true;
      ackTimeout = currentTime + ACK_WAIT_TIME;
    }
  } 
  else {
    // Mode attente ACK - écouter la réponse
    int packetSize = LoRa.parsePacket();
    
    if (packetSize) {
      // Lire le paquet reçu
      String receivedMessage = "";
      byte skipBytes = 0;
      
      if (DEBUG) {
        Serial.print("DEBUG - Bytes reçus: ");
      }
      
      while (LoRa.available()) {
        byte b = LoRa.read();
        
        if (DEBUG) {
          Serial.print(b, HEX);
          Serial.print(" ");
        }
        
        // Ignorer les bytes FF au début (points d'interrogation inversés)
        if (skipBytes < 2 && b == 0xFF) {
          skipBytes++;
          continue;
        }
        
        // Ignorer aussi les bytes 00 parasites
        if (skipBytes < 4 && b == 0x00) {
          skipBytes++;
          continue;
        }
        
        // Ajouter le caractère au message
        char c = (char)b;
        receivedMessage += c;
      }
      
      if (DEBUG) {
        Serial.println();
      }
      
      int rssi = LoRa.packetRssi();
      
      Serial.print("📥 Reçu: ");
      Serial.print(receivedMessage);
      Serial.print(" (RSSI: ");
      Serial.print(rssi);
      Serial.println(" dBm)");
      
      // Vérifier si c'est un ACK valide (plus besoin de chercher XXXX)
      if (receivedMessage.startsWith("ACK_")) {
        String ackId = receivedMessage.substring(4);
        
        if (ackId == lastMessageId) {
          Serial.println("✅ ACK confirmé! Pause de 10 secondes...\n");
          waitingForAck = false;
          lastSendTime = currentTime;
        } else {
          Serial.print("⚠️  ACK pour message #");
          Serial.print(ackId);
          Serial.print(" (attendu #");
          Serial.print(lastMessageId);
          Serial.println(")");
        }
      } else {
        Serial.println("⚠️  Message non-ACK reçu");
      }
    }
    
    // Vérifier timeout ACK
    if (currentTime >= ackTimeout && waitingForAck) {
      Serial.println("❌ Timeout ACK - Réessai dans 3 secondes...\n");
      waitingForAck = false;
      // Forcer un nouvel envoi dans 3 secondes
      lastSendTime = currentTime - SUCCESS_DELAY + RETRY_DELAY;
    }
  }
  
  delay(10); // Petite pause pour éviter la surcharge
}

void sendSensorData() {
  messageCount++;
  lastMessageId = String(messageCount);
  
  // Simuler des mesures de capteurs
  float temperature = 20.0 + random(-50, 50) / 10.0;  // 15-25°C
  float humidity = 60.0 + random(-200, 200) / 10.0;   // 40-80%
  int soilMoisture = 500 + random(-200, 200);         // 300-700
  
  // Construire le message AVEC le préfixe XXXX
  String message = "XXXXNano #" + String(messageCount) +
                   " Temp:" + String(temperature, 1) + "C" +
                   " Hum:" + String(humidity, 1) + "%" +
                   " Sol:" + String(soilMoisture);
  
  Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  Serial.print("📡 Envoi #");
  Serial.print(messageCount);
  Serial.print(": ");
  Serial.println(message.substring(4)); // Afficher sans XXXX
  
  // Envoyer le message
  LoRa.beginPacket();
  LoRa.print(message);
  LoRa.endPacket();
  
  Serial.println("⏳ Attente ACK (3s max)...");
  
  if (DEBUG) {
    Serial.print("DEBUG - Message envoyé, taille: ");
    Serial.print(message.length());
    Serial.println(" bytes");
  }
}
