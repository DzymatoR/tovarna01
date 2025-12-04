# tovarna01
Automatizace a digitalizace továrny

## Popis

Projekt pro monitoring a vizualizaci teplotních dat ze zařízení v továrně pomocí InfluxDB a Grafany.

## Požadavky

- Docker a Docker Compose
- Python 3.7+
- Raspberry Pi (nebo jiný ARM64/x86_64 systém)

## Instalace

### 1. Instalace Python závislostí

```bash
pip install -r requirements.txt
```

Nebo s virtuálním prostředím:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Spuštění celého stacku (InfluxDB, Grafana a monitoring)

```bash
docker compose up -d
```

Tento příkaz spustí:
- **InfluxDB** - databázi pro ukládání dat
- **Grafana** - vizualizační nástroj
- **Temperature Monitor** - službu pro sběr teplotních dat

## Přístupové údaje

### InfluxDB

- **URL**: http://localhost:8086 nebo http://192.168.16.51:8086
- **Username**: admin
- **Password**: adminpassword123
- **Organization**: Demo_InfluxDB
- **Bucket**: Demo_bucket
- **Admin Token**: eVyYk0wMFink-OHYXoCABFBo1spJdJe8EmIAlw5nIaOlPCgdsK76KyqO4v22QJxUhC_ojeDj6Cp7e82opwSWNQ==

### Grafana

- **URL**: http://localhost:3000 nebo http://192.168.16.51:3000
- **Username**: admin
- **Password**: admin (při prvním přihlášení budete vyzváni ke změně)

## Nastavení Grafany

1. Otevřete Grafanu na http://localhost:3000
2. Přihlaste se (admin/admin)
3. Přejděte na **Connections** → **Data sources** → **Add data source**
4. Vyberte **InfluxDB**
5. Nastavte:
   - **Query Language**: Flux
   - **URL**: http://influxdb:8086
   - **Organization**: Demo_InfluxDB
   - **Token**: eVyYk0wMFink-OHYXoCABFBo1spJdJe8EmIAlw5nIaOlPCgdsK76KyqO4v22QJxUhC_ojeDj6Cp7e82opwSWNQ==
   - **Default Bucket**: Demo_bucket
6. Klikněte na **Save & Test**

## Spuštění datového sběru

```bash
python Devices/zasobnik_velka_plnicka.py
```

Skript bude každých 5 sekund načítat teplotní data ze zařízení a ukládat je do InfluxDB.

## Užitečné příkazy Docker

```bash
# Zobrazit běžící kontejnery
docker ps

# Zastavit všechny kontejnery
docker compose down

# Zobrazit logy
docker logs influxdb
docker logs grafana
docker logs temperature-monitor

# Sledovat logy v reálném čase
docker logs -f temperature-monitor

# Restart kontejnerů
docker compose restart

# Rebuild a restart monitoring služby po změnách v kódu
docker compose up -d --build temperature-monitor
```

## Struktura projektu

```
tovarna01/
├── Devices/
│   └── zasobnik_velka_plnicka.py       # Skript pro sběr teplotních dat
├── docker-compose.yml                   # Docker konfigurace pro všechny služby
├── Dockerfile                           # Dockerfile pro monitoring službu
├── requirements.txt                     # Python závislosti
├── zasobnik-velka-plnicka.service      # Systemd service soubor (volitelné)
└── README.md                            # Tento soubor
``` 
