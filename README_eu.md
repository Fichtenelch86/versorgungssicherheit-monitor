# EU-Wirtschafts-Monitor (EUM)

Lokale App (nur Python-Standardbibliothek, Python ≥ 3.10) zur **Echtzeit-Beobachtung der
wesentlichen Wirtschaftsdaten aller 27 EU-Mitgliedstaaten** mit grafischer Darstellung und
**Statistik über die Entwicklung seit ~20 Jahren** in einer lokalen SQLite-Historie.

## Starten

```bash
python3 run_eu.py                 # Dashboard auf http://127.0.0.1:8077/ (nur lokal)
python3 run_eu.py --once          # einmalig Daten abrufen (z. B. für Cron) und beenden
python3 run_eu.py --once --nur-aktuell   # nur die jeweils neuesten Werte holen
python3 run_eu.py --port 9000 --db data/eu_historie.sqlite3
```

Der Server bindet ausschließlich an `127.0.0.1` – kein Zugriff von außen.

## Kennzahlen (Eurostat, öffentlich & keyfrei)

| Kennzahl | Eurostat-Datensatz | Frequenz | Historie |
|---|---|---|---|
| BIP je Einwohner (KKS, EU-27 = 100) | `nama_10_pc` (`PC_EU27_2020_HAB_MPPS_CP`, `B1GQ`) | jährlich | 2000–heute (26 Jahre) |
| Reales BIP-Wachstum | `nama_10_gdp` (`CLV_PCH_PRE`, `B1GQ`) | jährlich | 2000–heute |
| Arbeitslosenquote (saisonbereinigt) | `une_rt_m` (`SA, TOTAL, T, PC_ACT`) | monatlich | 2006–heute (~20 Jahre) |
| Inflation (HVPI, annual rate) | `prc_hicp_manr` (`CP00`, `RCH_A`) | monatlich | ~20 Jahre |
| Staatsschuldenquote (Maastricht) | `gov_10q_ggdebt` (`GD`, `S13`, `PC_GDP`) | quartalsweise | 2006–heute (~20 Jahre) |

Alle 27 Mitgliedstaaten plus EU-27-Gesamtwert (`EU27_2020`) werden je Lauf abgerufen.

## Dashboard & API

- `GET /` – Dashboard: KPI-Karten (EU-27), Balkendiagramme je Kennzahl (mit Referenzlinien:
  60 % Schulden, 2 % Inflation, 100 BIP/Kopf), 20-Jahres-Liniencharts je Kennzahl,
  Ländervergleichstabelle, Statistik-Tabelle „Start → aktuell" je Land. Auto-Refresh alle 5 Min.
- `GET /api/status` – aktuelle Kennzahlen + Rangfolgen (JSON)
- `GET /api/statistik` – vollständige Statistik aller Länder (JSON)
- `GET /api/reihe?kennzahl=<key>&land=<code>` – Zeitreihe eines Landes (JSON)
- `GET /api/refresh` – sofortiger Neuabruf

## Statistik (aus der Historie, `eum/stats.py`)

- aktueller Wert, Δ letzte Periode, Δ 12 Perioden, Mittel/Min/Max, linearer Trend (kl. Quadrate)
- **Entwicklung seit Reihenbeginn (~20 Jahre)**: Startwert → aktueller Wert, absolute und relative Veränderung
- Rangfolge der Länder je Kennzahl
- **Konvergenzindikator**: BIP/Kopf relativ zum EU-27-Wert, Veränderung in Prozentpunkten seit Start

## Aufbau

```
run_eu.py          Einstiegspunkt (Server / --once)
eum/
  sources.py       Eurostat REST API (JSON 2.0), Kennzahl-Definitionen, EU-27-Codes
  store.py         SQLite-Historie (data/eu_historie.sqlite3)
  collector.py     Abruf + Persistierung + Auswertung
  stats.py         Statistik-Funktionen
  charts.py        serverseitige SVG-Grafiken (Linien, Balken)
  dashboard.py     HTML-Rendering
  server.py        HTTP-Server (nur 127.0.0.1), JSON-API
```

Datenquelle: [Eurostat](https://ec.europa.eu/eurostat/web/main) (offizielle EU-Statistikbehörde).
