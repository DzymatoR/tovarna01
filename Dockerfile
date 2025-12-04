FROM python:3.11-slim

WORKDIR /app

# Kopírování requirements a instalace závislostí
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopírování skriptů
COPY Devices/ ./Devices/

# Spuštění skriptu
CMD ["python", "Devices/zasobnik_velka_plnicka.py"]
