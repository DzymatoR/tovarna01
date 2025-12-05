#ifndef CONFIG_H
#define CONFIG_H

// WiFi konfigurace
#define WIFI_SSID "your_wifi_ssid"
#define WIFI_PASSWORD "your_wifi_password"

// InfluxDB konfigurace
#define INFLUXDB_URL "http://192.168.1.100:8086"  // Změňte na IP vašeho InfluxDB serveru
#define INFLUXDB_TOKEN "your_influxdb_token_here"
#define INFLUXDB_ORG "Demo_InfluxDB"
#define INFLUXDB_BUCKET "Demo_bucket"

// Identifikace zařízení
#define DEVICE_NAME "VP_counter_01"

#endif
