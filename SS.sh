#!/usr/bin/env bash

# Dajemy Cloud SQL Proxy czas na start
echo "--- DIAGNOZA CLOUD RUN/SQL (UBI) ---"
echo "Czekam 15 sekund, aby dać czas Cloud SQL Proxy na start..."
sleep 15

# 1. Sprawdzenie Lokalnego Nasłuchiwania
echo "--- 1. SPRAWDZENIE PORTU 5432 (ss/netstat) ---"
if command -v ss &> /dev/null; then
    echo "Używam ss -antp:"
    ss -antp | grep 5432
elif command -v netstat &> /dev/null; then
    echo "Używam netstat -tuln:"
    netstat -tuln | grep 5432
else
    echo "Brak ss i netstat. Nie można sprawdzić nasłuchujących portów."
fi

# 2. Test Połączenia nc (z nmap-ncat)
echo "--- 2. TEST POŁĄCZENIA 127.0.0.1:5432 (netcat/ncat) ---"
if command -v nc &> /dev/null; then
    # -z dla skanowania, -w dla timeout
    if nc -z -w 3 127.0.0.1 5432; then
      echo "✅ SUKCES! Port 5432 jest OTWARTY. Proxy działa i nasłuchuje."
      exit 0
    else
      echo "❌ BŁĄD! Port 5432 jest ZAMKNIĘTY. Proxy NIE działa poprawnie (Connection Refused)."
      exit 1 # Koniec z błędem
    fi
else
    echo "Brak nc (nmap-ncat). Pomijam test połączenia. Wymagana weryfikacja logów Cloud SQL Proxy!"
    exit 1
fi
