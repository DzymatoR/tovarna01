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

// WiFi reconnect konfigurace
unsigned long lastWiFiCheck = 0;
const unsigned long wifiCheckInterval = 30000; // Kontrola každých 30 sekund
unsigned long lastMQTTAttempt = 0;
const unsigned long mqttReconnectInterval = 5000; // Pokus o MQTT reconnect každých 5 sekund

// MQTT client
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Keepalive - pravidelné odesílání dat pro kontrolu spojení
unsigned long lastKeepalive = 0;
const unsigned long keepaliveInterval = 60000; // Keepalive každou minutu

void reconnectWiFi() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi odpojeno! Reconnect...");
    WiFi.disconnect();
    delay(100);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
      delay(500);
      Serial.print(".");
      attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\nWiFi znovu připojeno!");
      Serial.print("IP adresa: ");
      Serial.println(WiFi.localIP());
    } else {
      Serial.println("\nWiFi reconnect selhal! Restart za 5s...");
      delay(5000);
      ESP.restart();
    }
  }
}

bool reconnectMQTT() {
  // Neblokující reconnect - jen jeden pokus
  if (!mqttClient.connected()) {
    unsigned long now = millis();
    if (now - lastMQTTAttempt > mqttReconnectInterval) {
      lastMQTTAttempt = now;

      Serial.print("Připojuji se k MQTT brokeru...");
      if (mqttClient.connect(DEVICE_NAME)) {
        Serial.println(" Připojeno!");
        // Po připojení pošleme keepalive
        char message[100];
        snprintf(message, 100, "{\"status\":\"online\",\"counter\":%lu,\"topic\":\"%s\"}", counter, MQTT_TOPIC);
        mqttClient.publish(MQTT_TOPIC, message);
        return true;
      } else {
        Serial.print(" Selhalo, rc=");
        Serial.print(mqttClient.state());
        Serial.println(" - zkusím později");
        return false;
      }
    }
  }
  return mqttClient.connected();
}

void setup() {
  Serial.begin(115200);
  pinMode(SENSOR_PIN, INPUT);

  // Připojení k WiFi
  Serial.print("Připojuji se k WiFi");
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("WiFi připojeno!");
    Serial.print("IP adresa: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nNepodařilo se připojit k WiFi! Restart...");
    delay(5000);
    ESP.restart();
  }

  // Nastavení MQTT brokeru
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setKeepAlive(60);
  mqttClient.setSocketTimeout(15);

  // Připojení k MQTT
  reconnectMQTT();
}

void loop() {
  unsigned long now = millis();

  // Pravidelná kontrola WiFi připojení
  if (now - lastWiFiCheck > wifiCheckInterval) {
    lastWiFiCheck = now;
    reconnectWiFi();
  }

  // Kontrola MQTT připojení (neblokující)
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }

  // MQTT loop - musí být voláno pravidelně
  if (mqttClient.connected()) {
    mqttClient.loop();
  }

  // Pravidelný keepalive - pošle stav i když nejsou detekce
  if (now - lastKeepalive > keepaliveInterval) {
    lastKeepalive = now;
    if (mqttClient.connected()) {
      char message[100];
      snprintf(message, 100, "{\"status\":\"alive\",\"counter\":%lu,\"uptime\":%lu,\"topic\":\"%s\"}",
               counter, millis()/1000, MQTT_TOPIC);
      mqttClient.publish(MQTT_TOPIC, message);
      Serial.println("-> Keepalive odeslán");
    }
  }

  // Detekce ze senzoru
  bool currentState = digitalRead(SENSOR_PIN);

  // Detekce nábežné hrany (přechod z LOW na HIGH)
  if (currentState == HIGH && lastState == LOW) {
    // Kontrola, zda uplynul debounce delay od poslední detekce
    // Řešení overflow problému pomocí rozdílu millis()
    if ((now - lastDebounceTime) > debounceDelay) {
      counter++;
      Serial.print("Detekován kus #");
      Serial.println(counter);

      // Okamžité odeslání na MQTT
      if (mqttClient.connected()) {
        char message[100];
        snprintf(message, 100, "{\"detected\":1,\"counter\":%lu,\"timestamp\":%lu,\"topic\":\"%s\"}",
                 counter, now, MQTT_TOPIC);

        if (mqttClient.publish(MQTT_TOPIC, message)) {
          Serial.println("-> MQTT: Odesláno");
        } else {
          Serial.println("-> MQTT: Chyba při odesílání");
        }
      } else {
        Serial.println("-> MQTT není připojen, ukládám do bufferu...");
        // TODO: Zde můžete přidat buffer pro offline režim
      }

      lastDebounceTime = now;
    }
  }

  lastState = currentState;
  delay(10);
}