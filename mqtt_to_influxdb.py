#!/usr/bin/env python3
"""
MQTT to InfluxDB Bridge
Poslouchá na MQTT topics a ukládá data do InfluxDB
Podporuje různé strategie zpracování (immediate, counter, average)
"""

import json
import time
import threading
import yaml
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any, List
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# InfluxDB konfigurace
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "eVyYk0wMFink-OHYXoCABFBo1spJdJe8EmIAlw5nIaOlPCgdsK76KyqO4v22QJxUhC_ojeDj6Cp7e82opwSWNQ=="
INFLUX_ORG = "Demo_InfluxDB"
INFLUX_BUCKET = "Demo_bucket"

# MQTT konfigurace
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

# Cesta ke konfiguračnímu souboru
CONFIG_FILE = "topic_config.yaml"

# Připojení k InfluxDB
influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

# Globální úložiště pro agregované data
aggregated_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
    "values": [],
    "count": 0,
    "sum": 0,
    "last_sent": time.time()
})

# Lock pro thread-safe přístup k datům
data_lock = threading.Lock()

# Načtená konfigurace
topic_config = None


def load_config():
    """Načte konfiguraci z YAML souboru"""
    global topic_config
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            topic_config = yaml.safe_load(f)
        print(f"✓ Konfigurace načtena z {CONFIG_FILE}")
        return True
    except FileNotFoundError:
        print(f"⚠ Konfigurační soubor {CONFIG_FILE} nenalezen, používám výchozí nastavení")
        topic_config = {"topics": {}, "default": {"strategy": "immediate"}}
        return False
    except Exception as e:
        print(f"✗ Chyba při načítání konfigurace: {e}")
        topic_config = {"topics": {}, "default": {"strategy": "immediate"}}
        return False


def get_topic_config(topic: str) -> Dict[str, Any]:
    """Získá konfiguraci pro daný topic (včetně podpory wildcards)"""
    if not topic_config or "topics" not in topic_config:
        return topic_config.get("default", {"strategy": "immediate"})

    # Nejdřív zkusíme přesnou shodu
    if topic in topic_config["topics"]:
        return topic_config["topics"][topic]

    # Pak zkusíme wildcard shodu
    for pattern, config in topic_config["topics"].items():
        if pattern.endswith("/#"):
            prefix = pattern[:-2]
            if topic.startswith(prefix + "/"):
                return config
        elif pattern.endswith("/+"):
            # Jednoduchá podpora single-level wildcard
            prefix = pattern[:-2]
            if topic.startswith(prefix + "/") and topic.count("/") == prefix.count("/") + 1:
                return config

    # Výchozí konfigurace
    return topic_config.get("default", {"strategy": "immediate"})


def on_connect(client, userdata, flags, rc, properties=None):
    """Callback při připojení k MQTT brokeru"""
    if rc == 0:
        print(f"✓ Připojeno k MQTT brokeru: {MQTT_BROKER}:{MQTT_PORT}")
        # Přihlášení k odběru topics z konfigurace
        if topic_config and "topics" in topic_config:
            for topic in topic_config["topics"].keys():
                client.subscribe(topic, 0)
                print(f"✓ Odebírám topic: {topic}")
        else:
            # Fallback - odebíráme všechny zprávy
            client.subscribe("tovarna/#", 0)
            client.subscribe("sensors/#", 0)
            print(f"✓ Odebírám fallback topics: tovarna/#, sensors/#")
    else:
        print(f"✗ Chyba připojení, návratový kód: {rc}")


def on_disconnect(client, userdata, rc, properties=None):
    """Callback při odpojení od MQTT brokeru"""
    if rc != 0:
        print(f"⚠ Neočekávané odpojení. Pokus o znovupřipojení...")


def parse_message(topic, payload):
    """
    Parsuje MQTT zprávu a připravuje data pro InfluxDB

    Očekávaný formát:
    - JSON: {"value": 123.45, "unit": "C", "sensor_id": "temp_01"}
    - Nebo prostý číselný údaj: "123.45"
    """
    try:
        # Pokus o parsování jako JSON
        data = json.loads(payload)
        return data
    except json.JSONDecodeError:
        # Pokud není JSON, zkusíme to jako číslo
        try:
            value = float(payload)
            return {"value": value}
        except ValueError:
            # Pokud není ani číslo, vrátíme jako string
            return {"value": payload}


def write_to_influxdb(topic: str, config: Dict[str, Any], value: float, timestamp: int = None):
    """Zapíše data do InfluxDB podle konfigurace"""
    try:
        measurement = config.get("measurement", "mqtt_data")
        point = Point(measurement)

        # Přidání tagů z konfigurace
        if "tags" in config:
            for tag_key, tag_value in config["tags"].items():
                point.tag(tag_key, tag_value)

        # Přidání tagu topic
        point.tag("topic", topic)

        # Auto tagy z topic path
        if config.get("auto_tags", False):
            topic_parts = topic.split('/')
            if len(topic_parts) > 0:
                point.tag("category", topic_parts[0])
            if len(topic_parts) > 1:
                point.tag("subcategory", topic_parts[1])
            if len(topic_parts) > 2:
                point.tag("sensor", topic_parts[2])

        # Přidání field
        field_name = config.get("field_name", "value")
        point.field(field_name, float(value))

        # Přidání jednotky jako dalšího fieldu pokud je specifikována
        if "unit" in config:
            point.tag("unit", config["unit"])

        # Timestamp
        if timestamp:
            point.time(timestamp)

        # Zápis do InfluxDB
        write_api.write(bucket=INFLUX_BUCKET, record=point)
        return True
    except Exception as e:
        print(f"✗ Chyba při zápisu do InfluxDB: {e}")
        return False


def on_message(client, userdata, msg):
    """Callback při přijetí MQTT zprávy"""
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8')

        print(f"\n📨 Přijata zpráva:")
        print(f"   Topic: {topic}")
        print(f"   Payload: {payload}")

        # Získání konfigurace pro tento topic
        config = get_topic_config(topic)
        strategy = config.get("strategy", "immediate")

        print(f"   Strategie: {strategy}")

        # Parsování zprávy
        data = parse_message(topic, payload)

        # Získání hodnoty
        if isinstance(data, dict):
            value = data.get("value", config.get("increment_value", 1))
        else:
            value = data

        # Převod na číslo
        try:
            value = float(value)
        except (ValueError, TypeError):
            print(f"⚠ Nelze převést hodnotu '{value}' na číslo, používám výchozí hodnotu 1")
            value = 1.0

        # Zpracování podle strategie
        if strategy == "immediate":
            # Okamžité odeslání do InfluxDB
            if write_to_influxdb(topic, config, value):
                print(f"✓ Data okamžitě zapsána do InfluxDB")

        elif strategy == "counter":
            # Přičtení k čítači
            with data_lock:
                aggregated_data[topic]["count"] += 1
                aggregated_data[topic]["sum"] += value
                aggregated_data[topic]["config"] = config
                print(f"✓ Přičteno k čítači: {aggregated_data[topic]['sum']} (počet: {aggregated_data[topic]['count']})")

        elif strategy == "average":
            # Přidání hodnoty pro průměrování
            with data_lock:
                aggregated_data[topic]["values"].append(value)
                aggregated_data[topic]["count"] += 1
                aggregated_data[topic]["sum"] += value
                aggregated_data[topic]["config"] = config
                avg = aggregated_data[topic]["sum"] / aggregated_data[topic]["count"]
                print(f"✓ Přidáno do průměru: {avg:.2f} (počet vzorků: {aggregated_data[topic]['count']})")

        else:
            print(f"⚠ Neznámá strategie '{strategy}', používám immediate")
            if write_to_influxdb(topic, config, value):
                print(f"✓ Data zapsána do InfluxDB")

    except Exception as e:
        print(f"✗ Chyba při zpracování zprávy: {e}")


def process_aggregated_data():
    """
    Periodicky kontroluje agregovaná data a odesílá je do InfluxDB
    Běží v samostatném vlákně
    """
    while True:
        try:
            time.sleep(1)  # Kontrola každou sekundu
            current_time = time.time()

            with data_lock:
                topics_to_reset = []

                for topic, data in aggregated_data.items():
                    if "config" not in data:
                        continue

                    config = data["config"]
                    strategy = config.get("strategy", "immediate")

                    # Pouze pro strategie s intervalem
                    if strategy not in ["counter", "average"]:
                        continue

                    interval = config.get("interval", 60)
                    last_sent = data.get("last_sent", 0)

                    # Kontrola, zda uplynul interval
                    if current_time - last_sent >= interval:
                        if data["count"] > 0:
                            # Výpočet hodnoty k odeslání
                            if strategy == "counter":
                                value_to_send = data["sum"]
                            elif strategy == "average":
                                value_to_send = data["sum"] / data["count"]
                            else:
                                value_to_send = data["sum"]

                            # Odeslání do InfluxDB
                            print(f"\n⏰ Časový interval uplynul pro topic: {topic}")
                            print(f"   Strategie: {strategy}, Hodnota: {value_to_send}, Počet vzorků: {data['count']}")

                            if write_to_influxdb(topic, config, value_to_send):
                                print(f"✓ Agregovaná data úspěšně odeslána do InfluxDB")

                                # Reset dat pokud je nastaven
                                if config.get("reset_after_send", False):
                                    topics_to_reset.append(topic)
                                else:
                                    data["last_sent"] = current_time
                        else:
                            # I když nejsou data, aktualizujeme last_sent
                            data["last_sent"] = current_time

                # Reset dat mimo lock iteraci
                for topic in topics_to_reset:
                    aggregated_data[topic] = {
                        "values": [],
                        "count": 0,
                        "sum": 0,
                        "last_sent": current_time,
                        "config": aggregated_data[topic]["config"]
                    }
                    print(f"🔄 Vynulováno počítadlo pro topic: {topic}")

        except Exception as e:
            print(f"✗ Chyba v časovači: {e}")


def main():
    """Hlavní funkce"""
    print("=" * 60)
    print("MQTT to InfluxDB Bridge")
    print("=" * 60)
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"InfluxDB: {INFLUX_URL}")
    print(f"Organization: {INFLUX_ORG}")
    print(f"Bucket: {INFLUX_BUCKET}")
    print("=" * 60)

    # Načtení konfigurace
    load_config()

    # Spuštění vlákna pro zpracování agregovaných dat
    aggregation_thread = threading.Thread(target=process_aggregated_data, daemon=True)
    aggregation_thread.start()
    print("✓ Časovač pro agregovaná data spuštěn")

    # Vytvoření MQTT klienta
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mqtt_influxdb_bridge")

    # Nastavení callback funkcí
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Připojení k MQTT brokeru
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)

        # Spuštění smyčky pro příjem zpráv
        print("\n⏳ Čekám na MQTT zprávy... (Ctrl+C pro ukončení)\n")
        client.loop_forever()

    except KeyboardInterrupt:
        print("\n\n⏹ Ukončuji...")
        client.disconnect()
        influx_client.close()
        print("✓ Odpojeno")
    except Exception as e:
        print(f"✗ Chyba: {e}")
        client.disconnect()
        influx_client.close()


if __name__ == "__main__":
    main()
