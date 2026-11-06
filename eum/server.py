"""HTTP-Server (nur Standardbibliothek), bindet exclusively an 127.0.0.1."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import collector, dashboard, sources, store

DEFAULT_DB = "data/eu_historie.sqlite3"
REFRESH_SEK = 300


class State:
    def __init__(self, db):
        self.db = db
        self.lock = threading.Lock()
        self.caches = {}

    def _laden(self):
        daten, s, info = collector.sammeln(self.db)
        self.caches = {"daten": daten, "stats": s, "info": info, "zeit": time.time()}

    def aktual(self):
        with self.lock:
            c = self.caches
            if not c or time.time() - c["zeit"] > REFRESH_SEK:
                self._laden()
                c = self.caches
            return c

    def nur_stats(self):
        s, info = collector.auswerten_pfad(self.db)
        return s, info


def make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        server_version = "EUM/0.1"

        def log_message(self, fmt, *args):
            pass

        def _sende(self, code, body, ctype="text/html; charset=utf-8"):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            url = urlparse(self.path)
            pfad = url.path.rstrip("/") or "/"
            qs = parse_qs(url.query)
            try:
                if pfad == "/":
                    c = state.aktual()
                    self._sende(200, dashboard.render_dashboard(c["daten"], c["stats"], c["info"]))
                elif pfad == "/api/status":
                    c = state.aktual()
                    self._sende(200, dashboard.render_status_json(c["daten"], c["stats"], c["info"]),
                                "application/json; charset=utf-8")
                elif pfad == "/api/statistik":
                    s, info = state.nur_stats()
                    self._sende(200, json.dumps({"statistik": s, "historie": info}, ensure_ascii=False, indent=1),
                                "application/json; charset=utf-8")
                elif pfad == "/api/reihe":
                    kennzahl = qs.get("kennzahl", [""])[0]
                    land = qs.get("land", [""])[0]
                    if kennzahl not in sources.INDICATORS:
                        self._sende(400, json.dumps({"error": "unbekannte kennzahl"}), "application/json")
                        return
                    st = store.Store(state.db)
                    try:
                        reihe = st.lade_reihe(kennzahl, land or sources.EU27_AGG)
                    finally:
                        st.close()
                    self._sende(200, json.dumps({"kennzahl": kennzahl, "land": land, "reihe": reihe},
                                                ensure_ascii=False), "application/json; charset=utf-8")
                elif pfad == "/api/refresh":
                    with state.lock:
                        state._laden()
                    self._sende(200, json.dumps({"ok": True, "zeit": state.caches["zeit"]}), "application/json")
                else:
                    self._sende(404, "<h1>404</h1>", "text/html; charset=utf-8")
            except Exception as exc:  # noqa: BLE001
                self._sende(500, json.dumps({"error": str(exc)}), "application/json; charset=utf-8")

    return Handler


def server_starten(host="127.0.0.1", port=8077, db=DEFAULT_DB):
    state = State(db)
    state.aktual()
    httpd = ThreadingHTTPServer((host, port), make_handler(state))
    print(f"EU-Wirtschafts-Monitor laeuft auf http://{host}:{port}/ (nur lokal, DB: {db})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
