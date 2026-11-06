"""Datenquellen: Eurostat REST API (JSON 2.0), oeffentlich und keyfrei."""

import json
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"

EU27 = [
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "EL",
    "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
    "SI", "ES", "SE",
]
EU27_AGG = "EU27_2020"
ALL_GEOS = EU27 + [EU27_AGG]

LAND_NAMEN = {
    "AT": "Österreich", "BE": "Belgien", "BG": "Bulgarien", "HR": "Kroatien",
    "CY": "Zypern", "CZ": "Tschechien", "DK": "Dänemark", "EE": "Estland",
    "FI": "Finnland", "FR": "Frankreich", "DE": "Deutschland", "EL": "Griechenland",
    "HU": "Ungarn", "IE": "Irland", "IT": "Italien", "LV": "Lettland",
    "LT": "Litauen", "LU": "Luxemburg", "MT": "Malta", "NL": "Niederlande",
    "PL": "Polen", "PT": "Portugal", "RO": "Rumänien", "SK": "Slowakei",
    "SI": "Slowenien", "ES": "Spanien", "SE": "Schweden", "EU27_2020": "EU-27 gesamt",
}

# Kennzahlen-Definitionen: (Schluessel, Titel, Einheit, Eurostat-Abfrage ohne geo/lastTimePeriod)
INDICATORS = {
    "bip_kopf": {
        "titel": "BIP je Einwohner (KKS, EU-27 = 100)",
        "einheit": "Index",
        "query": "nama_10_pc?format=JSON&lang=DE&unit=PC_EU27_2020_HAB_MPPS_CP&na_item=B1GQ",
        "frequenz": "Jahr",
        "periods": 26,
    },
    "wachstum": {
        "titel": "Reales BIP-Wachstum",
        "einheit": "% gg. Vorjahr",
        "query": "nama_10_gdp?format=JSON&lang=DE&unit=CLV_PCH_PRE&na_item=B1GQ",
        "frequenz": "Jahr",
        "periods": 26,
    },
    "arbeitslosenquote": {
        "titel": "Arbeitslosenquote (saisonbereinigt)",
        "einheit": "%",
        "query": "une_rt_m?format=JSON&lang=DE&s_adj=SA&age=TOTAL&sex=T&unit=PC_ACT",
        "frequenz": "Monat",
        "periods": 241,
    },
    "inflation": {
        "titel": "Inflation (HVPI, annual rate)",
        "einheit": "% gg. Vorjahr",
        "query": "prc_hicp_manr?format=JSON&lang=DE&coicop=CP00&unit=RCH_A",
        "frequenz": "Monat",
        "periods": 241,
    },
    "schuldenquote": {
        "titel": "Staatsschuldenquote (Maastricht)",
        "einheit": "% BIP",
        "query": "gov_10q_ggdebt?format=JSON&lang=DE&na_item=GD&sector=S13&unit=PC_GDP",
        "frequenz": "Quartal",
        "periods": 81,
    },
}

USER_AGENT = "EU-Wirtschafts-Monitor/0.1 (+lokale Statistik-App; Eurostat-Daten)"


def _fetch_json(url, timeout=180, retries=2):
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:200]
            last = f"HTTP {exc.code}: {body}"
            if exc.code in (400, 404):
                break
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
        if attempt < retries:
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Eurostat-Abruf fehlgeschlagen: {url[:120]} -> {last}")


def _entpacken(dataset):
    """Wandelt Eurostat-JSON-2.0 in {geo: {periode: wert}} um."""
    ids = dataset.get("id", [])
    dims = dataset.get("dimension", {})
    idx = {name: {cat: i for i, cat in enumerate(dims[name]["category"]["index"])}
           for name in ids}
    size = dataset.get("size", [])
    out = {}
    for flat, wert in dataset.get("value", {}).items():
        pos = int(flat)
        koordinaten = []
        for i, name in enumerate(reversed(ids)):
            koordinaten.append(pos % size[len(ids) - 1 - i])
            pos //= size[len(ids) - 1 - i]
        koordinaten.reverse()
        geo = None
        periode = None
        for name, k in zip(ids, koordinaten):
            if name == "geo":
                geo = list(dims["geo"]["category"]["index"].keys())[k]
            elif name == "time":
                periode = list(dims["time"]["category"]["index"].keys())[k]
        if geo and periode:
            out.setdefault(geo, {})[periode] = wert
    return out


def hole_kennzahl(schluessel, geos=None, last_periods=None):
    """Liefert {geo: {periode: wert}} plus Metadaten (aktualisiert, Zeitformat)."""
    cfg = INDICATORS[schluessel]
    geos = geos or ALL_GEOS
    periods = last_periods or cfg["periods"]
    geo_params = "&".join("geo=" + urllib.parse.quote(g) for g in geos)
    url = f"{API}{cfg['query']}&{geo_params}&lastTimePeriod={periods}"
    dataset = _fetch_json(url)
    reihen = _entpacken(dataset)
    return {
        "schluessel": schluessel,
        "titel": cfg["titel"],
        "label_quelle": dataset.get("label"),
        "einheit": cfg["einheit"],
        "frequenz": cfg["frequenz"],
        "aktualisiert": dataset.get("updated"),
        "reihen": reihen,
    }


def hole_alle_kennzahlen(geos=None):
    """Holt alle fuenf Kennzahlen; liefert Liste der Ergebnisse."""
    ergebnisse = []
    for schluessel in INDICATORS:
        ergebnisse.append(hole_kennzahl(schluessel, geos=geos))
    return ergebnisse
