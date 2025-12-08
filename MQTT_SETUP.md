# MQTT Broker Setup - Návod k použití

## Přehled

Tento setup obsahuje:
- **Mosquitto MQTT Broker** - přijímá MQTT zprávy
- **MQTT to InfluxDB Bridge** - Python skript, který poslouchá MQTT topics a ukládá data do InfluxDB
- **Systemd service** - pro automatické spuštění při startu systému

## Instalace

### 1. Instalace Python závislostí

```bash
cd /home/dzymator/tovarna01
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Spuštění MQTT brokeru (Mosquitto)

```bash
# Spuštění všech služeb včetně Mosquitto
docker compose up -d

# Kontrola, že Mosquitto běží
docker ps | grep mosquitto

# Zobrazení logů Mosquitto
docker logs mosquitto
```

### 3. Testování MQTT brokeru

```bash
# Instalace MQTT klientských nástrojů (pokud nejsou nainstalované)
sudo apt-get install mosquitto-clients

# Test 1: Odebírání zpráv (spusťte v jednom terminálu)
mosquitto_sub -h localhost -t "tovarna/#" -v

# Test 2: Publikování zprávy (spusťte v druhém terminálu)
mosquitto_pub -h localhost -t "tovarna/teplota/senzor1" -m '{"value": 25.5, "unit": "C"}'
```

## Spuštění MQTT Bridge

### Manuální spuštění (pro testování)

```bash
cd /home/dzymator/tovarna01
source .venv/bin/activate
python mqtt_to_influxdb.py
```

Nyní můžete publikovat zprávy a sledovat, jak se ukládají do InfluxDB:

```bash
# V jiném terminálu
mosquitto_pub -h localhost -t "tovarna/teplota/senzor1" -m '{"value": 25.5, "unit": "C"}'
mosquitto_pub -h localhost -t "tovarna/vlhkost/senzor2" -m '{"value": 60, "unit": "%"}'
mosquitto_pub -h localhost -t "sensors/pressure" -m "1013.25"
```

### Automatické spuštění při startu systému (systemd)

```bash
# Instalace systemd service
sudo cp mqtt-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mqtt-bridge.service
sudo systemctl start mqtt-bridge.service

# Kontrola stavu služby
sudo systemctl status mqtt-bridge.service

# Sledování logů
sudo journalctl -u mqtt-bridge.service -f
```

## Konfigurace MQTT Topics

MQTT Bridge je ve výchozím nastavení nakonfigurován pro odběr těchto topics:

- `tovarna/#` - všechny zprávy začínající "tovarna/"
- `sensors/#` - všechny zprávy začínající "sensors/"

Pro změnu topics upravte soubor [mqtt_to_influxdb.py](mqtt_to_influxdb.py) řádky 20-23:

```python
MQTT_TOPICS = [
    ("tovarna/#", 0),
    ("sensors/#", 0),
    ("vase_topic/#", 0),  # Přidejte vlastní topic
]
```

## Formát zpráv

MQTT Bridge podporuje několik formátů zpráv:

### 1. JSON formát (doporučený)

```bash
mosquitto_pub -h localhost -t "tovarna/teplota/senzor1" -m '{"value": 25.5, "unit": "C", "sensor_id": "temp_01"}'
```

Všechny klíče v JSON budou uloženy jako fields v InfluxDB.

### 2. Číselný formát

```bash
mosquitto_pub -h localhost -t "tovarna/teplota/senzor1" -m "25.5"
```

Hodnota bude uložena jako field "value".

### 3. Textový formát

```bash
mosquitto_pub -h localhost -t "tovarna/status/system" -m "online"
```

Text bude uložen jako string field "value".

## Struktura dat v InfluxDB

Data jsou ukládána do InfluxDB s následující strukturou:

- **Measurement**: Odvozeno z topic (např. "teplota" z "tovarna/teplota/senzor1")
- **Tags**:
  - `topic`: Celý MQTT topic
  - `category`: První část topic (např. "tovarna")
  - `sensor`: Třetí část topic (např. "senzor1")
- **Fields**: Data z MQTT zprávy

### Příklad query v Grafaně

```flux
from(bucket: "Demo_bucket")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "teplota")
  |> filter(fn: (r) => r._field == "value")
```

## Přístupové údaje

### MQTT Broker (Mosquitto)

- **Host**: localhost (nebo IP RPi v síti)
- **Port**: 1883 (MQTT)
- **WebSocket Port**: 9001
- **Autentizace**: Aktuálně vypnutá (allow_anonymous true)

Pro zabezpečení MQTT brokeru upravte [mosquitto.conf](mosquitto.conf) a přidejte:

```conf
allow_anonymous false
password_file /mosquitto/config/passwd
```

### InfluxDB

- **URL**: http://localhost:8086
- **Organization**: Demo_InfluxDB
- **Bucket**: Demo_bucket
- **Token**: (viz docker-compose.yml)

## Užitečné příkazy

```bash
# Restart MQTT brokeru
docker compose restart mosquitto

# Restart MQTT Bridge služby
sudo systemctl restart mqtt-bridge.service

# Sledování logů MQTT brokeru
docker logs -f mosquitto

# Sledování logů MQTT Bridge
sudo journalctl -u mqtt-bridge.service -f

# Test připojení k MQTT
mosquitto_sub -h localhost -t "#" -v

# Zastavení všech služeb
docker compose down

# Zastavení MQTT Bridge
sudo systemctl stop mqtt-bridge.service
```

## Integrace s ESP32/Arduino

Příklad kódu pro publikování z ESP32:

```cpp
#include <WiFi.h>
#include <PubSubClient.h>

const char* mqtt_server = "192.168.16.51";  // IP vašeho RPi
const int mqtt_port = 1883;

WiFiClient espClient;
PubSubClient client(espClient);

void setup() {
  client.setServer(mqtt_server, mqtt_port);
}

void loop() {
  if (!client.connected()) {
    client.connect("ESP32_Client");
  }

  // Publikování teploty
  float temp = 25.5;
  String payload = "{\"value\":" + String(temp) + ",\"unit\":\"C\"}";
  client.publish("tovarna/teplota/esp32", payload.c_str());

  delay(5000);
}
```

## Troubleshooting

### MQTT broker se nespustí

```bash
# Kontrola logů
docker logs mosquitto

# Kontrola konfigurace
docker exec mosquitto cat /mosquitto/config/mosquitto.conf
```

### MQTT Bridge nemůže zapisovat do InfluxDB

```bash
# Kontrola, že InfluxDB běží
docker ps | grep influxdb

# Test připojení k InfluxDB
curl http://localhost:8086/health
```

### Zprávy se nepřijímají

```bash
# Ověřte, že Bridge běží
sudo systemctl status mqtt-bridge.service

# Sledujte logy
sudo journalctl -u mqtt-bridge.service -f

# Test publikování
mosquitto_pub -h localhost -t "test/topic" -m "test message"
```
