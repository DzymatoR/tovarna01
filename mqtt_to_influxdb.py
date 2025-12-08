#!/usr/bin/env python3
"""
MQTT to InfluxDB Bridge
Poslouchá na MQTT topics a ukládá data do InfluxDB
"""

import json
import time
from datetime import datetime
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
MQTT_TOPICS = [
    ("tovarna/#", 0),  # Odebírá všechny zprávy začínající 'tovarna/'
    ("sensors/#", 0),  # Odebírá všechny zprávy začínající 'sensors/'
]

# Připojení k InfluxDB
influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)


def on_connect(client, userdata, flags, rc, properties=None):
    """Callback při připojení k MQTT brokeru"""
    if rc == 0:
        print(f"✓ Připojeno k MQTT brokeru: {MQTT_BROKER}:{MQTT_PORT}")
        # Přihlášení k odběru topics
        for topic, qos in MQTT_TOPICS:
            client.subscribe(topic, qos)
            print(f"✓ Odebírám topic: {topic}")
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


def on_message(client, userdata, msg):
    """Callback při přijetí MQTT zprávy"""
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8')

        print(f"\n📨 Přijata zpráva:")
        print(f"   Topic: {topic}")
        print(f"   Payload: {payload}")

        # Parsování zprávy
        data = parse_message(topic, payload)

        # Rozdělení topic na části (např. "tovarna/teplota/senzor1" -> ["tovarna", "teplota", "senzor1"])
        topic_parts = topic.split('/')

        # Vytvoření measurement name z topic
        measurement = topic_parts[1] if len(topic_parts) > 1 else "mqtt_data"

        # Příprava Point pro InfluxDB
        point = Point(measurement)

        # Přidání tagů z topic
        point.tag("topic", topic)
        if len(topic_parts) > 0:
            point.tag("category", topic_parts[0])
        if len(topic_parts) > 2:
            point.tag("sensor", topic_parts[2])

        # Přidání fieldu/ů
        if isinstance(data, dict):
            for key, value in data.items():
                try:
                    # Pokus o převod na float
                    point.field(key, float(value))
                except (ValueError, TypeError):
                    # Pokud nejde převést, uložíme jako string
                    point.field(key, str(value))
        else:
            point.field("value", data)

        # Zápis do InfluxDB
        write_api.write(bucket=INFLUX_BUCKET, record=point)
        print(f"✓ Data zapsána do InfluxDB (measurement: {measurement})")

    except Exception as e:
        print(f"✗ Chyba při zpracování zprávy: {e}")


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
