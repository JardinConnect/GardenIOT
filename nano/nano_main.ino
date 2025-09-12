#include <SPI.h>
#include <LoRa.h>
#include <DHT.h>
#include <Wire.h>
#include <BH1750.h>
#include <Adafruit_BMP280.h>

// LoRa Parameters
#define LORA_SS_PIN 10
#define LORA_RST_PIN 9
#define LORA_DIO0_PIN 2
#define LORA_FREQUENCY 433E6
#define LORA_TX_POWER 15
#define CLIENT_ADDRESS 1
#define SERVER_ADDRESS 2

// Sensor Pins
#define DHT22_PIN 3
#define LM393_ANALOG_PIN A0
#define LM393_DIGITAL_PIN 4

// Sensor Objects
DHT dht(DHT22_PIN, DHT22);
BH1750 lightMeter;
Adafruit_BMP280 bmp;

// Variables
unsigned long count = 0;
unsigned long lastSendTime = 0;
const unsigned long sendInterval = 5000; // 5 seconds

void setup() {
  Serial.begin(9600);
  while (!Serial);
  
  Serial.println("Garden IoT Node - Arduino Nano");
  
  // Initialize LoRa
  LoRa.setPins(LORA_SS_PIN, LORA_RST_PIN, LORA_DIO0_PIN);
  
  if (!LoRa.begin(LORA_FREQUENCY)) {
    Serial.println("Starting LoRa failed!");
    while (1);
  }
  
  LoRa.setTxPower(LORA_TX_POWER);
  Serial.println("LoRa initialized successfully!");
  
  // Initialize I2C
  Wire.begin();
  
  // Initialize BH1750 light sensor
  if (lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
    Serial.println("BH1750 initialized successfully");
  } else {
    Serial.println("Error initializing BH1750");
  }
  
  // Initialize BMP280
  if (!bmp.begin(0x76)) { // Try address 0x76, if fails try 0x77
    if (!bmp.begin(0x77)) {
      Serial.println("Could not find BMP280 sensor!");
    } else {
      Serial.println("BMP280 initialized at 0x77");
    }
  } else {
    Serial.println("BMP280 initialized at 0x76");
  }
  
  // Configure BMP280
  bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,
                  Adafruit_BMP280::SAMPLING_X2,
                  Adafruit_BMP280::SAMPLING_X16,
                  Adafruit_BMP280::FILTER_X16,
                  Adafruit_BMP280::STANDBY_MS_500);
  
  // Initialize DHT22
  dht.begin();
  Serial.println("DHT22 initialized");
  
  // Initialize LM393 soil moisture sensor
  pinMode(LM393_DIGITAL_PIN, INPUT);
  Serial.println("LM393 soil moisture sensor initialized");
  
  Serial.println("All sensors initialized. Starting main loop...");
}

void loop() {
  unsigned long currentTime = millis();
  
  if (currentTime - lastSendTime > sendInterval) {
    lastSendTime = currentTime;
    
    // Read sensors
    float temperature = readDHT22Temperature();
    float humidity = readDHT22Humidity();
    float light = readBH1750();
    float pressure = readBMP280Pressure();
    float altitude = readBMP280Altitude();
    float bmpTemp = readBMP280Temperature();
    int soilMoisture = readLM393();
    
    // Construct message
    String message = "Count:" + String(count);
    message += ",Temp:" + String(temperature, 1);
    message += ",Hum:" + String(humidity, 1);
    message += ",Light:" + String(light, 1);
    message += ",Press:" + String(pressure, 1);
    message += ",Alt:" + String(altitude, 1);
    message += ",BMP_T:" + String(bmpTemp, 1);
    message += ",Soil:" + String(soilMoisture);
    
    // Send via LoRa
    sendLoRaMessage(message);
    
    // Print to serial for debugging
    Serial.println(message);
    
    count++;
  }
}

float readDHT22Temperature() {
  float temp = dht.readTemperature();
  if (isnan(temp)) {
    Serial.println("Failed to read temperature from DHT22");
    return -999.0;
  }
  return temp;
}

float readDHT22Humidity() {
  float hum = dht.readHumidity();
  if (isnan(hum)) {
    Serial.println("Failed to read humidity from DHT22");
    return -999.0;
  }
  return hum;
}

float readBH1750() {
  float lux = lightMeter.readLightLevel();
  if (lux < 0) {
    Serial.println("Error reading light level");
    return -999.0;
  }
  return lux;
}

float readBMP280Temperature() {
  return bmp.readTemperature();
}

float readBMP280Pressure() {
  return bmp.readPressure() / 100.0F; // Convert to hPa
}

float readBMP280Altitude() {
  return bmp.readAltitude(1013.25); // Sea level pressure
}

int readLM393() {
  // Read analog value (0-1023)
  int analogValue = analogRead(LM393_ANALOG_PIN);
  
  // Read digital value (HIGH/LOW)
  int digitalValue = digitalRead(LM393_DIGITAL_PIN);
  
  // Return analog value for more precision
  // Higher value = drier soil, Lower value = wetter soil
  return analogValue;
}

void sendLoRaMessage(String message) {
  LoRa.beginPacket();
  LoRa.write(SERVER_ADDRESS);
  LoRa.write(CLIENT_ADDRESS);
  LoRa.print(message);
  LoRa.endPacket();
  
  Serial.print("Sent via LoRa: ");
  Serial.println(message);
}