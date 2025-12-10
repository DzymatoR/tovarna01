#!/bin/bash
# Testovací skript pro MQTT čítač

echo "=== Test MQTT čítače ==="
echo "Topic: tovarna/citac/kusy"
echo "Odesílám 10 zpráv po 1 kusu..."
echo ""

# Odešle 10 zpráv
for i in {1..10}
do
    echo "Zpráva $i/10"
    mosquitto_pub -h localhost -t tovarna/citac/kusy -m "1"
    sleep 0.5
done

echo ""
echo "✓ Odesláno 10 zpráv"
echo "Čekejte na interval (60s) pro automatické odeslání do InfluxDB"
echo "Nebo sledujte výstup mqtt_to_influxdb.py"
