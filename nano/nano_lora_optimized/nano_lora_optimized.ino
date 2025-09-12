#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <BH1750.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// === Unique sensor ID ===
const char SENSOR_ID[] = "NANO_01";

// === Pin Configuration ===
#define DHTPIN        4     // DHT22 on pin D4
#define DHTTYPE       DHT22
#define SOIL_SENSOR   A0    // Soil moisture sensor on A0
#define ONE_WIRE_BUS  3     // DS18B20 on D3

// LoRa SX1278 pins
#define NSS   10  // CS
#define RST   9   // Reset
#define DIO0  2   // Interrupt for reception

// === Sensor instances ===
DHT dht(DHTPIN, DHTTYPE);
BH1750 lightMeter;
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature ds18b20(&oneWire);

// === Variables ===
unsigned long count = 0;

void setup() {
  Serial.begin(9600);
  while (!Serial) {
    ; // Wait for serial port
  }
  
  Serial.println(F("Garden IoT Node - Arduino Nano"));
  Serial.println(F("================================"));
  
  Wire.begin();

  // -- BH1750 Light Sensor --
  if (!lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
    Serial.println(F("BH1750 not detected!"));
  } else {
    Serial.println(F("BH1750 OK"));
  }

  // -- DHT22 --
  dht.begin();
  Serial.println(F("DHT22 OK"));
  
  // -- DS18B20 --
  ds18b20.begin();
  Serial.println(F("DS18B20 OK"));

  // -- LoRa SX1278 --
  Serial.println(F("Initializing LoRa..."));
  LoRa.setPins(NSS, RST, DIO0);
  if (!LoRa.begin(433E6)) {
    Serial.println(F("LoRa init failed!"));
    while (1);
  }
  LoRa.setTxPower(15);
  Serial.println(F("LoRa OK"));
  Serial.println(F("================================"));
}

void loop() {
  // Read sensors
  float lux = lightMeter.readLightLevel();
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  
  // Read soil temperature
  ds18b20.requestTemperatures();
  float soilTemp = ds18b20.getTempCByIndex(0);
  
  // Read soil moisture
  int soilMoisture = analogRead(SOIL_SENSOR);
  // Convert to percentage (inverse scale: wet=low value, dry=high value)
  float soilPercent = map(soilMoisture, 1023, 0, 0, 100);

  // Check for sensor errors
  if (isnan(temperature)) temperature = -999.0;
  if (isnan(humidity)) humidity = -999.0;
  if (lux < 0) lux = -999.0;
  if (soilTemp == -127.0) soilTemp = -999.0;

  // Convert floats to strings (Arduino sprintf doesn't support %f)
  char luxStr[10], tempStr[10], humStr[10];
  char soilTStr[10], soilHStr[10];

  dtostrf(lux, 6, 1, luxStr);
  dtostrf(temperature, 6, 1, tempStr);
  dtostrf(humidity, 6, 1, humStr);
  dtostrf(soilTemp, 6, 1, soilTStr);
  dtostrf(soilPercent, 6, 1, soilHStr);

  // Display readings
  Serial.println(F("--- Sensor Readings ---"));
  Serial.print(F("Count    : ")); Serial.println(count);
  Serial.print(F("Light    : ")); Serial.print(luxStr); Serial.println(F(" lux"));
  Serial.print(F("Temp     : ")); Serial.print(tempStr); Serial.println(F(" C"));
  Serial.print(F("Humidity : ")); Serial.print(humStr); Serial.println(F(" %"));
  Serial.print(F("Soil Temp: ")); Serial.print(soilTStr); Serial.println(F(" C"));
  Serial.print(F("Soil Moist: ")); Serial.print(soilHStr); Serial.println(F(" %"));

  // Build message using README format
  // Format: Count:X,Temp:XX.X,Hum:XX.X,Light:XXX.X,Soil:XXX
  char message[100];
  snprintf(message, sizeof(message),
    "Count:%lu,Temp:%s,Hum:%s,Light:%s,SoilT:%s,SoilM:%s",
    count,
    tempStr,
    humStr,
    luxStr,
    soilTStr,
    soilHStr
  );

  Serial.print(F("LoRa TX: "));
  Serial.println(message);

  // Send via LoRa
  LoRa.beginPacket();
  LoRa.print(message);
  LoRa.endPacket();

  Serial.println(F("Data sent!"));
  Serial.println(F("-----------------------"));

  count++;
  
  // Wait 5 seconds
  delay(1000);
}
