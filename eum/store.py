"""Persistente Historie in SQLite: Rohwerte je Kennzahl/Land/Periode plus Snapshot-Metadaten."""

import os
import sqlite3
import threading
import time

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messwerte (
    kennzahl   TEXT NOT NULL,
    land       TEXT NOT NULL,
    periode    TEXT NOT NULL,
    wert       REAL NOT NULL,
    abgerufen  REAL NOT NULL,
    PRIMARY KEY (kennzahl, land, periode)
);
CREATE TABLE IF NOT EXISTS snapshots (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    zeit       REAL NOT NULL,
    quelle     TEXT NOT NULL,
    details    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messwerte_kennzahl ON messwerte (kennzahl, periode);
"""


class Store:
    def __init__(self, pfad):
        os.makedirs(os.path.dirname(os.path.abspath(pfad)), exist_ok=True)
        self.pfad = pfad
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(pfad, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    def schreibe_werte(self, kennzahl, reihen, quelle="Eurostat"):
        """reihen: {land: {periode: wert}}. Schreibt/aktualisiert alle Werte."""
        jetzt = time.time()
        zeilen = [
            (kennzahl, land, periode, float(wert), jetzt)
            for land, reihe in reihen.items()
            for periode, wert in reihe.items()
            if wert is not None
        ]
        with self._lock, self._conn:
            self._conn.executemany(
                "INSERT INTO messwerte (kennzahl, land, periode, wert, abgerufen) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(kennzahl, land, periode) DO UPDATE SET wert=excluded.wert, abgerufen=excluded.abgerufen",
                zeilen,
            )
            self._conn.execute(
                "INSERT INTO snapshots (zeit, quelle, details) VALUES (?, ?, ?)",
                (jetzt, quelle, kennzahl),
            )
        return len(zeilen)

    def lade_reihe(self, kennzahl, land):
        """Liefert [(periode, wert)] chronologisch sortiert."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT periode, wert FROM messwerte WHERE kennzahl=? AND land=? ORDER BY periode",
                (kennzahl, land),
            )
            return [(r["periode"], r["wert"]) for r in cur.fetchall()]

    def lade_alle(self, kennzahl):
        """Liefert {land: [(periode, wert), ...]}."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT land, periode, wert FROM messwerte WHERE kennzahl=? ORDER BY land, periode",
                (kennzahl,),
            )
            out = {}
            for r in cur.fetchall():
                out.setdefault(r["land"], []).append((r["periode"], r["wert"]))
            return out

    def letzte_periode(self, kennzahl, land):
        with self._lock:
            cur = self._conn.execute(
                "SELECT periode FROM messwerte WHERE kennzahl=? AND land=? ORDER BY periode DESC LIMIT 1",
                (kennzahl, land),
            )
            row = cur.fetchone()
            return row["periode"] if row else None

    def snapshot_info(self):
        with self._lock:
            cur = self._conn.execute(
                "SELECT zeit, quelle, COUNT(*) AS n FROM snapshots GROUP BY zeit, quelle ORDER BY zeit DESC LIMIT 20"
            )
            rows = [dict(r) for r in cur.fetchall()]
            cur2 = self._conn.execute("SELECT COUNT(*) AS n FROM messwerte")
            return {"snapshots": rows, "werte_gesamt": cur2.fetchone()["n"]}

    def close(self):
        with self._lock:
            self._conn.close()
