"""Offline-Tests fuer eum: Store, Stats, Charts, Dashboard – ohne Netzwerk."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eum import charts, collector, dashboard, sources, stats, store  # noqa: E402


def test_store_und_stats():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.sqlite3")
        st = store.Store(db)
        reihe = {f"{2000 + i}": float(i) for i in range(21)}
        st.schreibe_werte("bip_kopf", {"DE": reihe})
        gelad = st.lade_reihe("bip_kopf", "DE")
        assert len(gelad) == 21, len(gelad)
        assert gelad[-1] == ("2020", 20.0), gelad[-1]
        # Upsert: gleicher Schluessel ueberschreibt
        st.schreibe_werte("bip_kopf", {"DE": {"2020": 99.0}})
        assert st.lade_reihe("bip_kopf", "DE")[-1] == ("2020", 99.0)
        st.close()
        s, _ = collector.auswerten_pfad(db)
        de = s["bip_kopf"]["laender"]["DE"]
        assert de["aktuell"]["wert"] == 99.0
        assert de["start"]["wert"] == 0.0
        assert de["entwicklung_seit_start"]["veraenderung"] == 99.0
        assert de["min"] == 0.0 and de["max"] == 99.0
        print("OK store+stats")


def test_charts_und_dashboard():
    reihen = {"Deutschland": [(f"{y}", float(y - 2000)) for y in range(2006, 2027)],
              "EU-27": [(f"{y}", 100.0) for y in range(2006, 2027)]}
    svg = charts.linien_chart(reihen, titel="Test", einheit="%")
    assert "<svg" in svg and "polyline" in svg
    balken = charts.balken_chart([("A", 5.0), ("B", -2.0)], titel="B", einheit="%", referenz=60)
    assert "<svg" in balken and "Referenz" not in balken  # Referenz-Label nur bei gesetzter Referenz
    daten = [{"schluessel": k, "titel": v["titel"], "einheit": v["einheit"], "frequenz": v["frequenz"],
              "aktualisiert": "2026-01-01", "reihen": {"DE": {"2025": 1.0}, "EU27_2020": {"2025": 2.0}}}
             for k, v in sources.INDICATORS.items()]
    st = {k: {"titel": v["titel"], "einheit": v["einheit"],
              "laender": {"DE": stats.zusammenfassung([("2025", 1.0)], einheit=v["einheit"])},
              "laender_all": {"EU27_2020": stats.zusammenfassung([("2025", 2.0)], einheit=v["einheit"])},
              "rang": [{"land": "DE", "periode": "2025", "wert": 1.0}],
              "konvergenz": {}}
          for k, v in sources.INDICATORS.items()}
    html = dashboard.render_dashboard(daten, st, {"snapshots": [], "werte_gesamt": 5})
    assert "EU-Wirtschafts-Monitor" in html and "<svg" in html and "Deutschland" in html
    js = dashboard.render_status_json(daten, st, {"snapshots": [], "werte_gesamt": 5})
    assert '"bip_kopf"' in js
    print("OK charts+dashboard")


if __name__ == "__main__":
    test_store_und_stats()
    test_charts_und_dashboard()
    print("Alle Offline-Tests bestanden.")
