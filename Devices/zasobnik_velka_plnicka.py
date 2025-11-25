import requests
import time
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# InfluxDB konfigurace
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "eVyYk0wMFink-OHYXoCABFBo1spJdJe8EmIAlw5nIaOlPCgdsK76KyqO4v22QJxUhC_ojeDj6Cp7e82opwSWNQ=="  # Zkopíruj z InfluxDB webového rozhraní
INFLUX_ORG = "Demo_InfluxDB"
INFLUX_BUCKET = "Demo_bucket"

# Připojení k InfluxDB
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

url = "http://192.168.16.36/values.json"

while True:
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        # Extrakce 4 teplotních kanálů z pole 'ch'
        channels = data.get("ch", [])

        temp1 = channels[0].get("value") if len(channels) > 0 and channels[0].get("name") == "Temperature" else None
        temp2 = channels[1].get("value") if len(channels) > 1 and channels[1].get("name") == "Temperature" else None
        temp3 = channels[2].get("value") if len(channels) > 2 and channels[2].get("name") == "Temperature" else None
        temp4 = channels[3].get("value") if len(channels) > 3 and channels[3].get("name") == "Temperature" else None

        print(f"Teplota 1: {temp1}")
        print(f"Teplota 2: {temp2}")
        print(f"Teplota 3: {temp3}")
        print(f"Teplota 4: {temp4}")
        print("-" * 40)

        # Zápis do InfluxDB
        if temp1 is not None:
            point1 = Point("temperature").tag("channel", "1").field("value", float(temp1))
            write_api.write(bucket=INFLUX_BUCKET, record=point1)
        
        if temp2 is not None:
            point2 = Point("temperature").tag("channel", "2").field("value", float(temp2))
            write_api.write(bucket=INFLUX_BUCKET, record=point2)
        
        if temp3 is not None:
            point3 = Point("temperature").tag("channel", "3").field("value", float(temp3))
            write_api.write(bucket=INFLUX_BUCKET, record=point3)
        
        if temp4 is not None:
            point4 = Point("temperature").tag("channel", "4").field("value", float(temp4))
            write_api.write(bucket=INFLUX_BUCKET, record=point4)

        print("✓ Data zapsána do InfluxDB")

    except requests.exceptions.RequestException as e:
        print("Chyba při čtení dat:", e)
    except (KeyError, IndexError) as e:
        print("Chyba při zpracování dat:", e)
    except Exception as e:
        print("Chyba při zápisu do InfluxDB:", e)

    time.sleep(5)