"""Serverseitige SVG-Grafiken (keine externen Bibliotheken)."""

PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
    "#e377c2", "#7f7f7f", "#bcbd22", "#17becf", "#003f8c", "#c0392b",
    "#27ae60", "#8e44ad", "#d35400", "#16a085", "#2c3e50", "#e67e22",
    "#2980b9", "#c0392b", "#7f8c8d", "#f39c12", "#1abc9c", "#e74c3c",
    "#3498db", "#9b59b6",
]


def _fmt(wert, einheit):
    if wert is None:
        return "–"
    if einheit == "%":
        return f"{wert:.1f} %"
    if abs(wert) >= 1000:
        return f"{wert:,.0f}".replace(",", ".")
    return f"{wert:.1f}"


def linien_chart(reihen, titel="", einheit="", breite=760, hoehe=300, max_serien=28, referenz=None):
    """reihen: {label: [(periode, wert), ...]}. Zeichnet Linienchart als SVG-String."""
    reihen = {k: v for k, v in reihen.items() if v}
    if not reihen:
        return f'<svg width="{breite}" height="40"><text x="8" y="24">Keine Daten</text></svg>'
    alle_werte = [w for _, reihe in reihen.items() for _, w in reihe]
    alle_pts = [p for _, reihe in reihen.items() for p, _ in reihe]
    if not alle_werte:
        return f'<svg width="{breite}" height="40"><text x="8" y="24">Keine Daten</text></svg>'
    lo, hi = min(alle_werte), max(alle_werte)
    if lo == hi:
        lo, hi = lo - 1, hi + 1
    puffer = (hi - lo) * 0.08
    lo, hi = lo - puffer, hi + puffer
    punkte = sorted(set(alle_pts))
    n = len(punkte)
    links, rechts, oben, unten = 64, 16, 34, 46
    iw, ih = breite - links - rechts, hoehe - oben - unten

    def x(i):
        return links + (iw * i / (n - 1) if n > 1 else iw / 2)

    def y(w):
        return oben + ih * (1 - (w - lo) / (hi - lo))

    teile = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{breite}" height="{hoehe}" '
        f'viewBox="0 0 {breite} {hoehe}" font-family="system-ui, sans-serif" font-size="11">',
        f'<rect width="{breite}" height="{hoehe}" fill="#ffffff" rx="8"/>',
        f'<text x="{links}" y="20" font-size="13" font-weight="600" fill="#1a2733">{titel}</text>',
    ]
    for g in range(5):
        gw = lo + (hi - lo) * g / 4
        gy = y(gw)
        teile.append(f'<line x1="{links}" y1="{gy:.1f}" x2="{breite - rechts}" y2="{gy:.1f}" stroke="#e3e8ee" stroke-width="1"/>')
        teile.append(f'<text x="{links - 6}" y="{gy + 4:.1f}" text-anchor="end" fill="#5b6b7b">{_fmt(gw, einheit)}</text>')
    if referenz is not None:
        ry = y(referenz)
        teile.append(f'<line x1="{links}" y1="{ry:.1f}" x2="{breite - rechts}" y2="{ry:.1f}" stroke="#c0392b" stroke-width="1.2" stroke-dasharray="5,4"/>')
        teile.append(f'<text x="{breite - rechts - 4}" y="{ry - 4:.1f}" text-anchor="end" fill="#c0392b" font-size="10">Referenz {referenz:g}</text>')
    step = max(1, n // 8)
    for i, p in enumerate(punkte):
        if i % step == 0 or i == n - 1:
            teile.append(f'<text x="{x(i):.1f}" y="{hoehe - unten + 16}" text-anchor="middle" fill="#5b6b7b">{p}</text>')
    teile.append(f'<line x1="{links}" y1="{oben}" x2="{links}" y2="{hoehe - unten}" stroke="#c7d0d9"/>')
    teile.append(f'<line x1="{links}" y1="{hoehe - unten}" x2="{breite - rechts}" y2="{hoehe - unten}" stroke="#c7d0d9"/>')
    for j, (label, reihe) in enumerate(list(reihen.items())[:max_serien]):
        farbe = PALETTE[j % len(PALETTE)]
        d = dict(reihe)
        punkte_str = " ".join(f"{x(i):.1f},{y(d[p]):.1f}" for i, p in enumerate(punkte) if p in d)
        teile.append(f'<polyline points="{punkte_str}" fill="none" stroke="{farbe}" stroke-width="1.6" stroke-opacity="0.9"/>')
    teile.append("</svg>")
    return "".join(teile)


def balken_chart(eintraege, titel="", einheit="", breite=760, hoehe=None, referenz=None, farbe_positiv="#2e7d32", farbe_negativ="#c0392b"):
    """eintraege: [(label, wert), ...] absteigend. Horizontaler Balkendiagramm als SVG."""
    eintraege = [(l, w) for l, w in eintraege if w is not None]
    if not eintraege:
        return f'<svg width="{breite}" height="40"><text x="8" y="24">Keine Daten</text></svg>'
    zeilen = len(eintraege)
    hoehe = hoehe or (zeilen * 20 + 56)
    oben, links, rechts, unten = 34, 150, 84, 12
    iw = breite - links - rechts
    lo = min(0, min(w for _, w in eintraege))
    hi = max(0, max(w for _, w in eintraege))
    if hi == lo:
        hi = lo + 1
    span = hi - lo

    def x(w):
        return links + iw * (w - lo) / span

    teile = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{breite}" height="{hoehe}" '
        f'viewBox="0 0 {breite} {hoehe}" font-family="system-ui, sans-serif" font-size="11">',
        f'<rect width="{breite}" height="{hoehe}" fill="#ffffff" rx="8"/>',
        f'<text x="{links}" y="20" font-size="13" font-weight="600" fill="#1a2733">{titel}</text>',
    ]
    for i, (label, wert) in enumerate(eintraege):
        y0 = oben + i * 20
        farbe = farbe_positiv if wert >= 0 else farbe_negativ
        teile.append(f'<text x="{links - 8}" y="{y0 + 13}" text-anchor="end" fill="#1a2733">{label}</text>')
        teile.append(f'<rect x="{x(min(0, wert)):.1f}" y="{y0 + 2}" width="{abs(x(wert) - x(0)):.1f}" height="15" fill="{farbe}" rx="2"/>')
        anchor = "start" if wert >= 0 else "end"
        tx = x(wert) + (5 if wert >= 0 else -5)
        teile.append(f'<text x="{tx:.1f}" y="{y0 + 13}" text-anchor="{anchor}" fill="#37474f">{_fmt(wert, einheit)}</text>')
    if referenz is not None:
        rx = x(referenz)
        teile.append(f'<line x1="{rx:.1f}" y1="{oben - 4}" x2="{rx:.1f}" y2="{hoehe - unten}" stroke="#c0392b" stroke-width="1.2" stroke-dasharray="5,4"/>')
        teile.append(f'<text x="{rx:.1f}" y="{oben - 8}" text-anchor="middle" fill="#c0392b" font-size="10">60 %</text>')
    teile.append("</svg>")
    return "".join(teile)
