#include <Arduino.h>
#include <WiFi.h>
#include <InfluxDbClient.h>
#include <InfluxDbCloud.h>
#include "config.h"

// Senzor konfigurace
const int SENSOR_PIN = 21;
unsigned long counter = 0;
bool lastState = LOW;
unsigned long lastDebounceTime = 0;
const unsigned long debounceDelay = 200; // 200ms minimum mezi kusy

// Časovač pro odesílání dat
unsigned long lastSendTime = 0;
const unsigned long sendInterval = 60000; // 60 sekund = 1 minuta

// InfluxDB client
InfluxDBClient client(INFLUXDB_URL, INFLUXDB_ORG, INFLUXDB_BUCKET, INFLUXDB_TOKEN);

// Data point
Point sensor("production_counter");

void setup() {
  Serial.begin(115200);
  pinMode(SENSOR_PIN, INPUT);

  // Připojení k WiFi
  Serial.print("Připojuji se k WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.println("WiFi připojeno!");
  Serial.print("IP adresa: ");
  Serial.println(WiFi.localIP());

  // Nastavení tagu pro identifikaci zařízení
  sensor.addTag("device", DEVICE_NAME);

  // Test spojení s InfluxDB
  if (client.validateConnection()) {
    Serial.println("Připojeno k InfluxDB!");
  } else {
    Serial.print("InfluxDB spojení selhalo: ");
    Serial.println(client.getLastErrorMessage());
  }
}

void loop() {
  bool currentState = digitalRead(SENSOR_PIN);

  // Detekce nábežné hrany (přechod z LOW na HIGH)
  if (currentState == HIGH && lastState == LOW) {
    // Kontrola, zda uplynul debounce delay od poslední detekce
    if ((millis() - lastDebounceTime) > debounceDelay) {
      counter++;
      Serial.print("Počet kusů: ");
      Serial.println(counter);
      lastDebounceTime = millis();
    }
  }

  lastState = currentState;

  // Kontrola, zda uplynula minuta - odeslání dat do InfluxDB
  if (millis() - lastSendTime >= sendInterval) {
    Serial.println("=================================");
    Serial.print("Odesílám data do InfluxDB: ");
    Serial.print(counter);
    Serial.println(" kusů za poslední minutu");

    // Vyčištění předchozích polí
    sensor.clearFields();

    // Přidání hodnoty počítadla
    sensor.addField("count", counter);

    // Odeslání dat do InfluxDB
    if (client.writePoint(sensor)) {
      Serial.println("✓ Data úspěšně odeslána");
    } else {
      Serial.print("✗ Chyba při odesílání: ");
      Serial.println(client.getLastErrorMessage());
    }

    // Reset počítadla
    counter = 0;
    lastSendTime = millis();
    Serial.println("Počítadlo resetováno");
    Serial.println("=================================");
  }

  delay(10);
}