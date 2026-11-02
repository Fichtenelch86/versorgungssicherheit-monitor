"""HTML-Dashboard (serverseitig gerendert, Auto-Refresh, ohne externe Ressourcen)."""

import html
import json

from . import sources
from .charts import balken_chart, linien_chart


def _esc(s):
    return html.escape(str(s))


def _fmt(wert, einheit="%"):
    if wert is None:
        return "–"
    return f"{wert:.1f} %" if einheit == "%" else (f"{wert:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".") if abs(wert) >= 100 else f"{wert:.1f}")


CSS = """
:root { --bg:#f2f5f8; --card:#ffffff; --ink:#1a2733; --muted:#5b6b7b; --line:#dbe3ea; --akzent:#003f8c; }
* { box-sizing: border-box; }
body { margin:0; font-family: system-ui, -apple-system, 'Segoe UI', sans-serif; background:var(--bg); color:var(--ink); }
header { background:var(--akzent); color:#fff; padding:14px 22px; display:flex; flex-wrap:wrap; gap:14px; align-items:baseline; }
header h1 { font-size:19px; margin:0; }
header .meta { font-size:12px; opacity:.85; }
main { padding:18px 22px; max-width:1180px; margin:0 auto; }
.grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(340px, 1fr)); gap:16px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }
.card h2 { font-size:14px; margin:0 0 10px; color:var(--akzent); }
.kpis { display:grid; grid-template-columns:repeat(auto-fit, minmax(150px,1fr)); gap:12px; margin-bottom:16px; }
.kpi { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:10px 14px; }
.kpi .label { font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; }
.kpi .wert { font-size:22px; font-weight:700; margin-top:2px; }
.kpi .sub { font-size:11px; color:var(--muted); }
table { border-collapse:collapse; width:100%; font-size:12.5px; }
th, td { text-align:right; padding:5px 8px; border-bottom:1px solid var(--line); }
th:first-child, td:first-child { text-align:left; }
th { color:var(--muted); font-weight:600; font-size:11px; text-transform:uppercase; letter-spacing:.03em; }
tr.eu td { font-weight:700; background:#eef3fa; }
.hoch { color:#c0392b; } .runter { color:#2e7d32; }
footer { color:var(--muted); font-size:11px; padding:14px 22px 26px; max-width:1180px; margin:0 auto; }
.charts { display:grid; grid-template-columns:1fr; gap:16px; margin-top:16px; }
.charts svg { width:100%; height:auto; }
.tabelle-scroll { overflow-x:auto; }
"""


def _kpi_karte(label, wert, einheit, sub):
    return (
        f'<div class="kpi"><div class="label">{_esc(label)}</div>'
        f'<div class="wert">{_fmt(wert, einheit)}</div>'
        f'<div class="sub">{_esc(sub)}</div></div>'
    )


def render_dashboard(daten, stats, snapshot_info, refresh_sek=300):
    """daten: Liste der Kennzahl-Ergebnisse; stats: Auswertung je Kennzahl."""
    eu = sources.EU27_AGG
    now = snapshot_info.get("snapshots", [{}])[-1] if snapshot_info.get("snapshots") else {}
    aktual = daten[0].get("aktualisiert") if daten else None

    teile = [
        "<!DOCTYPE html><html lang='de'><head><meta charset='utf-8'>",
        f"<meta http-equiv='refresh' content='{refresh_sek}'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        f"<title>EU-Wirtschafts-Monitor</title><style>{CSS}</style></head><body>",
        "<header><h1>🇪🇺 EU-Wirtschafts-Monitor</h1>",
        f"<span class='meta'>27 EU-Mitgliedstaaten · Eurostat Live-Daten · Historie in SQLite · "
        f"letzte Aktualisierung der Quelle: {_esc(aktual or '–')} · gespeicherte Werte: {snapshot_info.get('werte_gesamt', 0)}</span>",
        "</header><main>",
    ]

    teile.append('<div class="kpis">')
    for d in daten:
        key = d["schluessel"]
        eu_reihe = d["reihen"].get(eu) or {}
        letzter = sorted(eu_reihe.items())[-1] if eu_reihe else (None, None)
        st = (stats.get(key) or {}).get(eu)
        sub_bits = [f"Stand {letzter[0]}" if letzter[0] else "–"]
        if st and st.get("delta_letzte") is not None:
            sub_bits.append(f"Δ letzte Periode: {st['delta_letzte']:+.1f}")
        teile.append(_kpi_karte(d["titel"], letzter[1], d["einheit"], " · ".join(sub_bits)))
    teile.append("</div>")

    teile.append('<div class="grid">')
    for d in daten:
        key = d["schluessel"]
        rang = (stats.get(key) or {}).get("rang") or []
        teile.append(f'<div class="card"><h2>{_esc(d["titel"])} <small style="color:var(--muted)">({_esc(d["einheit"])}, {_esc(d["frequenz"])})</small></h2>')
        svg = balken_chart(
            [(sources.LAND_NAMEN.get(r["land"], r["land"]), r["wert"]) for r in rang],
            titel=f"Aktueller Stand ({rang[0]['periode'] if rang else '–'})" if rang else "",
            einheit="%" if d["einheit"].startswith("%") else "",
            referenz=60 if key == "schuldenquote" else (2.0 if key == "inflation" else (100 if key == "bip_kopf" else None)),
        )
        teile.append(svg)
        teile.append("</div>")
    teile.append("</div>")

    teile.append('<div class="charts">')
    for d in daten:
        key = d["schluessel"]
        reihen = {}
        for land in sources.EU27:
            r = d["reihen"].get(land)
            if r:
                reihen[sources.LAND_NAMEN.get(land, land)] = sorted(r.items())
        teile.append(f'<div class="card"><h2>20-Jahres-Verlauf: {_esc(d["titel"])}</h2>')
        teile.append(linien_chart(reihen, titel="", einheit="%" if d["einheit"].startswith("%") else "",
                                  referenz=60 if key == "schuldenquote" else (2.0 if key == "inflation" else (100 if key == "bip_kopf" else None))))
        teile.append("</div>")
    teile.append("</div>")

    teile.append('<div class="card"><h2>Ländervergleich – aktueller Stand (Tabelle)</h2><div class="tabelle-scroll"><table>')
    teile.append("<tr><th>Land</th>" + "".join(f"<th>{_esc(d['titel'].split(' (')[0])}</th>" for d in daten) + "</tr>")
    letzte = {d["schluessel"]: d["reihen"] for d in daten}
    for land in sources.EU27:
        name = sources.LAND_NAMEN[land]
        teile.append(f"<tr><td>{_esc(name)}</td>")
        for d in daten:
            key = d["schluessel"]
            reihe = letzte[key].get(land) or {}
            if reihe:
                p, w = sorted(reihe.items())[-1]
                teile.append(f"<td>{_fmt(w, d['einheit'])} <small style='color:var(--muted)'>{_esc(p)}</small></td>")
            else:
                teile.append("<td>–</td>")
        teile.append("</tr>")
    teile.append("<tr class='eu'><td>EU-27 gesamt</td>")
    for d in daten:
        key = d["schluessel"]
        reihe = letzte[key].get(eu) or {}
        if reihe:
            p, w = sorted(reihe.items())[-1]
            teile.append(f"<td>{_fmt(w, d['einheit'])} <small style='color:var(--muted)'>{_esc(p)}</small></td>")
        else:
            teile.append("<td>–</td>")
    teile.append("</tr></table></div></div>")

    teile.append('<div class="card"><h2>Statistik: Entwicklung seit Reihenbeginn (ca. 20 Jahre)</h2><div class="tabelle-scroll"><table>')
    teile.append("<tr><th>Land</th><th>BIP/Kopf: Start → aktuell (Δ)</th><th>Schuldenquote: Start → aktuell (Δ pp)</th><th>Arbeitslosenquote: Start → aktuell (Δ pp)</th><th>Inflation: Ø letzte 12 M.</th></tr>")
    for land in sources.EU27:
        name = sources.LAND_NAMEN[land]
        cells = [f"<td>{_esc(name)}</td>"]
        for key in ("bip_kopf", "schuldenquote", "arbeitslosenquote"):
            st = ((stats.get(key) or {}).get("laender") or {}).get(land)
            if st and st.get("entwicklung_seit_start") and st.get("start"):
                e = st["entwicklung_seit_start"]
                cells.append(f"<td>{st['start']['wert']:.0f} → {st['aktuell']['wert']:.0f} ({e['veraenderung']:+.1f})</td>" if key == "bip_kopf"
                             else f"<td>{st['start']['wert']:.1f} → {st['aktuell']['wert']:.1f} ({e['veraenderung']:+.1f} pp)</td>")
            else:
                cells.append("<td>–</td>")
        st_inf = ((stats.get("inflation") or {}).get("laender") or {}).get(land)
        if st_inf and st_inf.get("mittel_fenster") is not None:
            cells.append(f"<td>{st_inf['mittel_fenster']:.1f} %</td>")
        else:
            cells.append("<td>–</td>")
        teile.append("<tr>" + "".join(cells) + "</tr>")
    teile.append("</table></div></div>")

    teile.append("</main>")
    teile.append(
        "<footer>Daten: <a href='https://ec.europa.eu/eurostat/web/main'>Eurostat</a> "
        "(nama_10_pc, nama_10_gdp, une_rt_m, prc_hicp_manr, gov_10q_ggdebt). "
        "Nur lokale Verarbeitung; Server bindet an 127.0.0.1. "
        f"JSON-API: /api/status · /api/statistik · /api/reihe?kennzahl=…&land=…</footer>"
    )
    teile.append("</body></html>")
    return "".join(teile)


def render_status_json(daten, stats, snapshot_info):
    eu = sources.EU27_AGG
    out = {"aktualisiert_quelle": daten[0].get("aktualisiert") if daten else None,
           "historie": snapshot_info, "kennzahlen": {}}
    for d in daten:
        key = d["schluessel"]
        st = stats.get(key) or {}
        eu_st = st.get("laender_all", {}).get(eu) or (st.get("laender") or {}).get(eu)
        out["kennzahlen"][key] = {
            "titel": d["titel"],
            "einheit": d["einheit"],
            "frequenz": d["frequenz"],
            "eu_aktuell": eu_st.get("aktuell") if eu_st else None,
            "laender_rang": st.get("rang"),
        }
    return json.dumps(out, ensure_ascii=False, indent=1)
