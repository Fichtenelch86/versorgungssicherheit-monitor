"""Statistische Auswertung der Historie: aktuelle Werte, Veraenderungen, Trends, 20-Jahres-Entwicklung."""

import math
import statistics


def _fenster(reihe, n):
    """Letzte n (periode, wert)-Paare."""
    return reihe[-n:] if n and n < len(reihe) else reihe


def _trend_pp(reihe, fenster_n):
    """Linearer Trend in Prozentpunkten pro Periode ueber das Fenster (kleinste Quadrate)."""
    fenster = _fenster(reihe, fenster_n)
    if len(fenster) < 3:
        return None
    xs = list(range(len(fenster)))
    ys = [w for _, w in fenster]
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    zaehler = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    nenner = sum((x - mx) ** 2 for x in xs)
    if nenner == 0:
        return None
    return zaehler / nenner


def aktuell(reihe):
    if not reihe:
        return None
    return {"periode": reihe[-1][0], "wert": reihe[-1][1]}


def delta(reihe, n=1):
    if len(reihe) <= n:
        return None
    return reihe[-1][1] - reihe[-1 - n][1]


def zusammenfassung(reihe, einheit="", fenster=12):
    """Kernstatistik fuer eine Zeitreihe."""
    if not reihe:
        return None
    werte = [w for _, w in reihe]
    fenster_werte = [w for _, w in _fenster(reihe, fenster)]
    vor_20 = None
    if len(reihe) >= 2:
        basis = reihe[0]
        vor_20 = {"periode": basis[0], "wert": basis[1],
                  "veraenderung": reihe[-1][1] - basis[1],
                  "veraenderung_rel": ((reihe[-1][1] / basis[1]) - 1) * 100 if basis[1] else None}
    return {
        "aktuell": aktuell(reihe),
        "delta_letzte": delta(reihe, 1),
        "delta_12": delta(reihe, 12),
        "mittel_fenster": statistics.fmean(fenster_werte) if fenster_werte else None,
        "min": min(werte),
        "max": max(werte),
        "min_periode": reihe[werte.index(min(werte))][0],
        "max_periode": reihe[werte.index(max(werte))][0],
        "trend_pro_periode": _trend_pp(reihe, fenster),
        "anzahl": len(reihe),
        "start": {"periode": reihe[0][0], "wert": reihe[0][1]},
        "entwicklung_seit_start": vor_20,
        "einheit": einheit,
    }


def rangfolge(alle_reihen, kennzahl_einheit=""):
    """Rangfolge der Laender nach letztem Wert (absteigend)."""
    rang = []
    for land, reihe in alle_reihen.items():
        a = aktuell(reihe)
        if a:
            rang.append({"land": land, "periode": a["periode"], "wert": a["wert"]})
    rang.sort(key=lambda r: r["wert"], reverse=True)
    return rang


def konvergenz(alle_reihen, basis_land="EU27_2020"):
    """Abstand zum EU-Referenzwert und dessen Veraenderung seit Reihenbeginn (Konvergenzindikator)."""
    basis = alle_reihen.get(basis_land)
    if not basis:
        return None
    out = {}
    for land, reihe in alle_reihen.items():
        if land == basis_land or not reihe:
            continue
        a = aktuell(reihe)
        b = aktuell(basis)
        if not a or not b or b["wert"] == 0:
            continue
        start = reihe[0]
        start_basis = basis[0]
        rel_jetzt = a["wert"] / b["wert"] * 100 if b["wert"] else None
        rel_start = start[1] / start_basis[1] * 100 if start_basis[1] else None
        out[land] = {
            "rel_zu_eu_jetzt": rel_jetzt,
            "rel_zu_eu_start": rel_start,
            "veraenderung_pp": (rel_jetzt - rel_start) if (rel_jetzt is not None and rel_start is not None) else None,
        }
    return out


def beste_schlechteste(alle_reihen, n=5, richtung="hoch"):
    rang = rangfolge(alle_reihen)
    return rang[:n] if richtung == "hoch" else rang[-n:]
