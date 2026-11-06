#!/usr/bin/env python3
"""EU-Wirtschafts-Monitor: Startpunkt.

 Modi:
  python3 run_eu.py                -> Server auf http://127.0.0.1:8077/ (nur lokal)
  python3 run_eu.py --once         -> einmalig alle Eurostat-Daten holen + Historie schreiben
  python3 run_eu.py --once --nur-aktuell  -> nur die jeweils letzten Werte holen
  python3 run_eu.py --port 9000 --db data/eu_historie.sqlite3
"""

import argparse

from eum import collector, server


def main():
    parser = argparse.ArgumentParser(description="EU-Wirtschafts-Monitor (Eurostat, EU-27)")
    parser.add_argument("--once", action="store_true", help="nur einmal Daten abrufen und beenden")
    parser.add_argument("--nur-aktuell", action="store_true", help="nur letzte Periode je Kennzahl holen")
    parser.add_argument("--port", type=int, default=8077)
    parser.add_argument("--host", default="127.0.0.1", help="Bind-Adresse (Default: 127.0.0.1, nur lokal)")
    parser.add_argument("--db", default=server.DEFAULT_DB, help="SQLite-Datei der Historie")
    args = parser.parse_args()

    if args.once:
        daten, stats, info = collector.sammeln(args.db, nur_aktuell=args.nur_aktuell)
        gesamt = sum(len(r) for d in daten for r in d["reihen"].values())
        for d in daten:
            eu = d["reihen"].get("EU27_2020") or {}
            letzte = sorted(eu.items())[-1] if eu else (None, None)
            print(f"{d['schluessel']:<20} EU-27: {letzte[1]} ({letzte[0]})  Quelle aktualisiert: {d.get('aktualisiert')}")
        print(f"geschriebene Werte in dieser Runde: {gesamt}; gesamt in DB: {info['werte_gesamt']}")
        return

    server.server_starten(host=args.host, port=args.port, db=args.db)


if __name__ == "__main__":
    main()
