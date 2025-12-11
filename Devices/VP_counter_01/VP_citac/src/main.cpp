#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include "config.h"

// Senzor konfigurace
const int SENSOR_PIN = 21;
unsigned long counter = 0;
bool lastState = LOW;
unsigned long lastDebounceTime = 0;
const unsigned long debounceDelay = 200; // 200ms minimum mezi kusy

// MQTT client
WiFiClient espClient;
PubSubClient mqttClient(espClient);

void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Připojuji se k MQTT brokeru...");
    if (mqttClient.connect(DEVICE_NAME)) {
      Serial.println(" Připojeno!");
    } else {
      Serial.print(" Selhalo, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" Zkouším znovu za 5 sekund");
      delay(5000);
    }
  }
}

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

  // Nastavení MQTT brokeru
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);

  // Připojení k MQTT
  reconnectMQTT();
}

void loop() {
  // Kontrola MQTT připojení
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();

  bool currentState = digitalRead(SENSOR_PIN);

  // Detekce nábežné hrany (přechod z LOW na HIGH)
  if (currentState == HIGH && lastState == LOW) {
    // Kontrola, zda uplynul debounce delay od poslední detekce
    if ((millis() - lastDebounceTime) > debounceDelay) {
      counter++;
      Serial.print("Detekován kus #");
      Serial.println(counter);

      // Okamžité odeslání na MQTT
      char message[100];
      snprintf(message, 100, "{\"detected\":1,\"timestamp\":%lu,\"topic\":\"%s\"}", millis(), MQTT_TOPIC);

      if (mqttClient.publish(MQTT_TOPIC, message)) {
        Serial.println("-> MQTT: Odesláno");
      } else {
        Serial.println("-> MQTT: Chyba při odesílání");
      }

      lastDebounceTime = millis();
    }
  }

  lastState = currentState;
  delay(10);
}