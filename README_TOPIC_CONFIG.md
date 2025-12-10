# Konfigurace MQTT to InfluxDB Bridge

## Přehled

MQTT to InfluxDB Bridge nyní podporuje flexibilní konfiguraci s různými strategiemi zpracování pro jednotlivé MQTT topicy.

## Konfigurace

Konfigurace se provádí v souboru `topic_config.yaml`.

### Podporované strategie

#### 1. **immediate** - Okamžité odeslání
Každá přijatá zpráva se okamžitě zapíše do InfluxDB.

```yaml
"tovarna/teplota/senzor1":
  strategy: "immediate"
  measurement: "temperature"
  tags:
    location: "hala1"
    sensor_type: "DHT22"
  field_name: "value"
  unit: "celsius"
```

#### 2. **counter** - Čítač
Přičítá hodnoty a po určitém intervalu odesílá součet do InfluxDB. Ideální pro počítání kusů, událostí, chyb apod.

```yaml
"tovarna/citac/kusy":
  strategy: "counter"
  interval: 60  # interval v sekundách
  measurement: "citac_kusu"
  tags:
    location: "hala1"
    machine: "citac_01"
  increment_value: 1  # výchozí hodnota pokud zpráva neobsahuje číslo
  field_name: "count"
  reset_after_send: true  # vynulovat po odeslání
```

**Použití:**
- Pokud je ve zprávě číslo, přičte se tato hodnota
- Pokud zpráva neobsahuje číslo, přičte se `increment_value` (výchozí 1)
- Po uplynutí `interval` sekund se součet odešle do InfluxDB
- Pokud je `reset_after_send: true`, počítadlo se vynuluje

#### 3. **average** - Průměrování
Sbírá hodnoty a po určitém intervalu odesílá průměr do InfluxDB.

```yaml
"tovarna/teplota/senzor2":
  strategy: "average"
  interval: 120  # každé 2 minuty
  measurement: "temperature_avg"
  tags:
    location: "hala2"
  field_name: "avg_value"
  reset_after_send: true
```

### Parametry konfigurace

| Parametr | Popis | Povinný | Výchozí |
|----------|-------|---------|---------|
| `strategy` | Strategie zpracování (immediate/counter/average) | Ne | immediate |
| `interval` | Interval v sekundách (pro counter a average) | Ne | 60 |
| `measurement` | Název measurement v InfluxDB | Ne | mqtt_data |
| `tags` | Slovník tagů pro InfluxDB | Ne | {} |
| `field_name` | Název fieldu v InfluxDB | Ne | value |
| `unit` | Jednotka (uloží se jako tag) | Ne | - |
| `increment_value` | Výchozí hodnota pro counter | Ne | 1 |
| `reset_after_send` | Vynulovat data po odeslání | Ne | false |
| `auto_tags` | Automaticky vytvořit tagy z topic path | Ne | false |

### Wildcard support

Konfigurace podporuje MQTT wildcard:

```yaml
# Všechny topicy začínající 'sensors/'
"sensors/#":
  strategy: "immediate"
  measurement: "sensor_data"
  auto_tags: true
```

### Výchozí konfigurace

Pokud topic není v konfiguraci, použije se výchozí nastavení:

```yaml
default:
  strategy: "immediate"
  measurement: "mqtt_data"
  auto_tags: true
```

## Formát MQTT zpráv

Bridge podporuje různé formáty zpráv:

### JSON formát
```json
{"value": 123.45, "unit": "C", "sensor_id": "temp_01"}
```

### Prostá čísla
```
123.45
```

### Text
```
"online"
```

Pro **counter** strategii:
- Pokud zpráva obsahuje číslo, přičte se tato hodnota
- Pokud zpráva neobsahuje číslo, přičte se `increment_value`
- Prázdná zpráva nebo zpráva s libovolným textem přičte `increment_value`

## Příklady použití

### Čítač kusů s minutovým intervalem

**Konfigurace:**
```yaml
"tovarna/citac/kusy":
  strategy: "counter"
  interval: 60
  measurement: "production_count"
  tags:
    line: "linka_A"
  field_name: "pieces"
  reset_after_send: true
  increment_value: 1
```

**MQTT zprávy:**
```bash
# Každá zpráva přičte 1
mosquitto_pub -t tovarna/citac/kusy -m ""
mosquitto_pub -t tovarna/citac/kusy -m "1"
mosquitto_pub -t tovarna/citac/kusy -m "sensor_trigger"
```

Po 60 sekundách se do InfluxDB odešle součet (např. 150 kusů) a počítadlo se vynuluje.

### Čítač s různými hodnotami

**Konfigurace:**
```yaml
"tovarna/citac/palety":
  strategy: "counter"
  interval: 300  # 5 minut
  measurement: "palety_count"
  field_name: "total_palety"
  reset_after_send: true
```

**MQTT zprávy:**
```bash
# Přičte konkrétní číslo
mosquitto_pub -t tovarna/citac/palety -m "5"
mosquitto_pub -t tovarna/citac/palety -m "3"
mosquitto_pub -t tovarna/citac/palety -m "10"
```

Po 5 minutách se odešle součet: 18 palet

### Kombinace různých topiců

```yaml
topics:
  # Okamžitá data z teplotního senzoru
  "tovarna/teplota/hala1":
    strategy: "immediate"
    measurement: "temperature"
    field_name: "value"
    unit: "celsius"

  # Čítač výrobků
  "tovarna/citac/vyrobky":
    strategy: "counter"
    interval: 60
    measurement: "production"
    field_name: "count"
    reset_after_send: true

  # Průměrná vlhkost každých 5 minut
  "tovarna/vlhkost/hala1":
    strategy: "average"
    interval: 300
    measurement: "humidity"
    field_name: "avg_humidity"
    reset_after_send: true
```

## Instalace a spuštění

```bash
# Instalace závislostí
pip install -r requirements.txt

# Spuštění
python3 mqtt_to_influxdb.py
```

## Monitoring

Program vypisuje informace o zpracování:

```
📨 Přijata zpráva:
   Topic: tovarna/citac/kusy
   Payload: 1
   Strategie: counter
✓ Přičteno k čítači: 45 (počet: 45)

⏰ Časový interval uplynul pro topic: tovarna/citac/kusy
   Strategie: counter, Hodnota: 45, Počet vzorků: 45
✓ Agregovaná data úspěšně odeslána do InfluxDB
🔄 Vynulováno počítadlo pro topic: tovarna/citac/kusy
```

## Tipy

1. **Pro čítání kusů:** Použijte `strategy: counter` s `reset_after_send: true`
2. **Pro průměrování:** Použijte `strategy: average` s vhodným intervalem
3. **Pro kritická data:** Použijte `strategy: immediate` pro okamžitý zápis
4. **Intervaly:** Volte podle potřeby - kratší pro častější reporting, delší pro snížení zátěže DB
5. **Tagy:** Používejte konzistentní tagy pro snadné filtrování v InfluxDB/Grafana
