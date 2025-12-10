# Rychlý start - MQTT to InfluxDB Bridge s čítači

## 1. Instalace závislostí

```bash
pip install -r requirements.txt
```

Nové závislosti:
- `pyyaml` - pro čtení konfiguračního souboru

## 2. Konfigurace

### Základní konfigurace - čítač kusů

Upravte soubor [topic_config.yaml](topic_config.yaml):

```yaml
topics:
  "tovarna/citac/kusy":
    strategy: "counter"
    interval: 60  # každou minutu odešle a vynuluje
    measurement: "citac_kusu"
    tags:
      location: "hala1"
      machine: "citac_01"
    increment_value: 1
    field_name: "count"
    reset_after_send: true
```

### Pokročilá konfigurace

Pro více příkladů viz [topic_config_examples.yaml](topic_config_examples.yaml)

## 3. Spuštění

```bash
# Spusť MQTT to InfluxDB Bridge
python3 mqtt_to_influxdb.py
```

Výstup:
```
============================================================
MQTT to InfluxDB Bridge
============================================================
MQTT Broker: localhost:1883
InfluxDB: http://localhost:8086
Organization: Demo_InfluxDB
Bucket: Demo_bucket
============================================================
✓ Konfigurace načtena z topic_config.yaml
✓ Časovač pro agregovaná data spuštěn
✓ Připojeno k MQTT brokeru: localhost:1883
✓ Odebírám topic: tovarna/citac/kusy
```

## 4. Test čítače

V novém terminálu:

```bash
# Jednoduchý test - odešle 10 zpráv
./test_counter.sh

# Komplexní test - testuje všechny strategie
./test_all_strategies.sh
```

Nebo ručně:

```bash
# Odešli zprávu do čítače
mosquitto_pub -t tovarna/citac/kusy -m "1"

# Nebo více najednou
for i in {1..5}; do mosquitto_pub -t tovarna/citac/kusy -m "1"; done
```

## 5. Monitoring

V terminálu s běžícím bridge uvidíte:

```
📨 Přijata zpráva:
   Topic: tovarna/citac/kusy
   Payload: 1
   Strategie: counter
✓ Přičteno k čítači: 1 (počet: 1)

📨 Přijata zpráva:
   Topic: tovarna/citac/kusy
   Payload: 1
   Strategie: counter
✓ Přičteno k čítači: 2 (počet: 2)

... po 60 sekundách ...

⏰ Časový interval uplynul pro topic: tovarna/citac/kusy
   Strategie: counter, Hodnota: 45, Počet vzorků: 45
✓ Agregovaná data úspěšně odeslána do InfluxDB
🔄 Vynulováno počítadlo pro topic: tovarna/citac/kusy
```

## 6. Ověření v InfluxDB

```bash
# Přes InfluxDB CLI nebo webové rozhraní (http://localhost:8086)
```

V Grafana použijte dotaz:
```flux
from(bucket: "Demo_bucket")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "citac_kusu")
  |> filter(fn: (r) => r._field == "count")
```

## Strategie zpracování

### Counter (čítač)
- ✅ Počítání kusů, událostí, chyb
- ✅ Každá zpráva přičte hodnotu
- ✅ Po intervalu odešle součet
- ✅ Volitelné vynulování

### Average (průměr)
- ✅ Průměrování hodnot
- ✅ Ideální pro teplotu, vlhkost
- ✅ Po intervalu odešle průměr

### Immediate (okamžité)
- ✅ Okamžité odeslání každé zprávy
- ✅ Pro kritická data

## Nejčastější problémy

### Program nevidí konfiguraci
```bash
# Zkontroluj, že topic_config.yaml je ve stejné složce
ls -la topic_config.yaml
```

### MQTT broker není dostupný
```bash
# Zkontroluj, že Mosquitto běží
sudo systemctl status mosquitto

# Nebo ve Docker
docker ps | grep mosquitto
```

### Data se neukládají do InfluxDB
- Zkontroluj `INFLUX_TOKEN` v [mqtt_to_influxdb.py](mqtt_to_influxdb.py:21)
- Zkontroluj `INFLUX_BUCKET` a `INFLUX_ORG`
- Zkontroluj InfluxDB běží: `http://localhost:8086`

## Další informace

- Detailní dokumentace: [README_TOPIC_CONFIG.md](README_TOPIC_CONFIG.md)
- Příklady konfigurace: [topic_config_examples.yaml](topic_config_examples.yaml)
- Test skripty: [test_counter.sh](test_counter.sh), [test_all_strategies.sh](test_all_strategies.sh)
