#!/bin/bash
# Komplexní test všech strategií MQTT to InfluxDB Bridge

BROKER="localhost"

echo "============================================"
echo "Test MQTT to InfluxDB Bridge"
echo "============================================"
echo ""

# Test 1: Counter strategie
echo "=== Test 1: Counter (čítač kusů) ==="
echo "Topic: tovarna/citac/kusy"
echo "Odesílám 5 zpráv (každá = 1 kus)..."
for i in {1..5}; do
    mosquitto_pub -h $BROKER -t tovarna/citac/kusy -m "1"
    echo "  Odesláno: zpráva $i/5"
    sleep 0.3
done
echo "✓ Test 1 dokončen - čekejte 60s na odeslání součtu do InfluxDB"
echo ""

sleep 2

# Test 2: Counter s různými hodnotami
echo "=== Test 2: Counter s různými hodnotami ==="
echo "Topic: tovarna/citac/palety"
echo "Odesílám zprávy s různými čísly..."
mosquitto_pub -h $BROKER -t tovarna/citac/palety -m "5"
echo "  Odesláno: 5 palet"
sleep 0.3
mosquitto_pub -h $BROKER -t tovarna/citac/palety -m "3"
echo "  Odesláno: 3 palety"
sleep 0.3
mosquitto_pub -h $BROKER -t tovarna/citac/palety -m "7"
echo "  Odesláno: 7 palet"
echo "✓ Test 2 dokončen - celkem 15 palet (5+3+7)"
echo ""

sleep 2

# Test 3: Average strategie
echo "=== Test 3: Average (průměrování teploty) ==="
echo "Topic: tovarna/teplota/hala1"
echo "Odesílám různé teploty..."
temps=("23.5" "24.2" "22.8" "23.9" "24.5")
for temp in "${temps[@]}"; do
    mosquitto_pub -h $BROKER -t tovarna/teplota/hala1 -m "$temp"
    echo "  Odesláno: ${temp}°C"
    sleep 0.3
done
echo "✓ Test 3 dokončen - průměr bude odeslán po 120s"
echo ""

sleep 2

# Test 4: Immediate strategie
echo "=== Test 4: Immediate (okamžité odeslání) ==="
echo "Topic: tovarna/alarm/kriticky"
echo "Odesílám kritický alarm..."
mosquitto_pub -h $BROKER -t tovarna/alarm/kriticky -m "vysoky_tlak"
echo "  Odesláno: vysoky_tlak"
sleep 0.5
mosquitto_pub -h $BROKER -t tovarna/alarm/kriticky -m "vysoka_teplota"
echo "  Odesláno: vysoka_teplota"
echo "✓ Test 4 dokončen - data okamžitě v InfluxDB"
echo ""

sleep 2

# Test 5: Simulace reálného provozu
echo "=== Test 5: Simulace výrobní linky (10 sekund) ==="
echo "Odesílám mix zpráv různých typů..."

# Spustíme v pozadí různé "zdroje" dat
(
    for i in {1..10}; do
        mosquitto_pub -h $BROKER -t tovarna/citac/kusy -m "1"
        sleep 1
    done
) &

(
    for i in {1..5}; do
        temp=$(awk -v min=22 -v max=25 'BEGIN{srand(); print min+rand()*(max-min)}')
        mosquitto_pub -h $BROKER -t tovarna/teplota/hala1 -m "$temp"
        sleep 2
    done
) &

(
    for i in {1..3}; do
        mosquitto_pub -h $BROKER -t tovarna/citac/palety -m "2"
        sleep 3
    done
) &

echo "Čekám 10 sekund..."
sleep 10
echo "✓ Test 5 dokončen"
echo ""

# Shrnutí
echo "============================================"
echo "Shrnutí testů"
echo "============================================"
echo ""
echo "1. Counter (kusy): Odesláno 5+10 = 15 kusů"
echo "   → Po 60s odešle součet: ~15 a vynuluje"
echo ""
echo "2. Counter (palety): Odesláno 15+6 = 21 palet"
echo "   → Po 10min odešle součet: 21"
echo ""
echo "3. Average (teplota): Odesláno 5+5 = 10 měření"
echo "   → Po 120s odešle průměr: ~23.5°C"
echo ""
echo "4. Immediate (alarmy): 2 zprávy"
echo "   → Okamžitě v InfluxDB"
echo ""
echo "============================================"
echo "Sledujte výstup mqtt_to_influxdb.py"
echo "pro detaily o zpracování"
echo "============================================"
