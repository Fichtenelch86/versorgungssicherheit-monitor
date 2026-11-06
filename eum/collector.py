"""Collector: holt Eurostat-Daten und schreibt sie in die SQLite-Historie; rechnet Statistik."""

import time

from . import sources, stats, store


def sammeln(db_pfad="data/eu_historie.sqlite3", geos=None, nur_aktuell=False):
    """Holt alle Kennzahlen und persistiert sie. Liefert (daten, stats, snapshot_info)."""
    st = store.Store(db_pfad)
    try:
        if nur_aktuell:
            daten = []
            for key, cfg in sources.INDICATORS.items():
                daten.append(sources.hole_kennzahl(key, geos=geos, last_periods=1))
        else:
            daten = sources.hole_alle_kennzahlen(geos=geos)
        for d in daten:
            st.schreibe_werte(d["schluessel"], d["reihen"], quelle=f"Eurostat {d.get('aktualisiert') or ''}")
        return daten, auswerten(st), st.snapshot_info()
    finally:
        st.close()


def auswerten(st):
    """Statistik ueber alle Kennzahlen und Laender aus der Historie."""
    ergebnis = {}
    for key, cfg in sources.INDICATORS.items():
        alle = st.lade_alle(key)
        laender = {land: stats.zusammenfassung(reihe, einheit=cfg["einheit"])
                   for land, reihe in alle.items() if land != sources.EU27_AGG}
        laender_all = {land: stats.zusammenfassung(reihe, einheit=cfg["einheit"])
                       for land, reihe in alle.items()}
        ergebnis[key] = {
            "titel": cfg["titel"],
            "einheit": cfg["einheit"],
            "laender": laender,
            "laender_all": laender_all,
            "rang": stats.rangfolge(alle),
            "konvergenz": stats.konvergenz(alle),
        }
    return ergebnis


def auswerten_pfad(db_pfad):
    st = store.Store(db_pfad)
    try:
        return auswerten(st), st.snapshot_info()
    finally:
        st.close()


def letzte_aktualisierung(db_pfad):
    st = store.Store(db_pfad)
    try:
        info = st.snapshot_info()
        return info["snapshots"][0]["zeit"] if info["snapshots"] else None
    finally:
        st.close()


if __name__ == "__main__":
    import json
    daten, s, info = sammeln()
    print(json.dumps({"werte": sum(len(d["reihen"]) for d in daten), "snapshots": info["snapshots"][-1:]}, ensure_ascii=False))
