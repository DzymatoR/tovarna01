#ifndef CONFIG_H
#define CONFIG_H

// WiFi konfigurace
#define WIFI_SSID "your_wifi_ssid"
#define WIFI_PASSWORD "your_wifi_password"

// MQTT konfigurace
#define MQTT_SERVER "192.168.1.100"  // IP adresa MQTT brokeru
#define MQTT_PORT 1883
#define MQTT_TOPIC "tovarna/vp_counter_01/pieces"

// Identifikace zařízení
#define DEVICE_NAME "VP_counter_01"

#endif
