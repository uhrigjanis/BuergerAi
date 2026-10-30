"""HTTP-Server der Web-Oberfläche (nur Standardbibliothek, siehe ADR 0006).

Startet mit ``buergerai web`` bzw. ``./bai web``. Liefert die Dateien aus
``static/`` und die JSON-API unter ``/api/...``. Es werden keine Angaben
gespeichert oder protokolliert.
"""

from __future__ import annotations

import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import unquote, urlparse

from ..wissensbasis import Wissensbasis
from . import api

STATIC = Path(__file__).resolve().parent / "static"
# Nur diese Dateien werden ausgeliefert (kein Zugriff auf andere Pfade)
DATEIEN = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}
MAX_BODY = 64 * 1024
SICHERHEIT = {
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'self'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


def handler_fuer(kb: Wissensbasis) -> type[BaseHTTPRequestHandler]:
    post_routen: dict[str, Callable[[Wissensbasis, Any], Any]] = {
        "/api/ort": api.ort,
        "/api/bericht": api.bericht,
    }

    class Handler(BaseHTTPRequestHandler):
        server_version = "BuergerAI"
        sys_version = ""

        # Keine Zugriffsprotokolle: Angaben stehen zwar nicht in der URL, aber sicher ist sicher
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            pass

        def _senden(self, status: int, inhalt: bytes, typ: str, extra: Optional[dict[str, str]] = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(inhalt)))
            for k, v in {**SICHERHEIT, **(extra or {})}.items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(inhalt)

        def _json(self, status: int, daten: Any) -> None:
            self._senden(status, json.dumps(daten, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _fehler(self, exc: api.ApiFehler) -> None:
            self._json(exc.status, exc.json())

        def do_HEAD(self) -> None:  # noqa: N802
            self.do_GET()

        def do_GET(self) -> None:  # noqa: N802
            pfad = urlparse(self.path).path
            try:
                if pfad in DATEIEN:
                    name, typ = DATEIEN[pfad]
                    self._senden(200, (STATIC / name).read_bytes(), typ)
                elif pfad == "/api/meta":
                    self._json(200, api.meta(kb))
                elif pfad.startswith("/api/szenario/"):
                    self._json(200, api.szenario(kb, unquote(pfad[len("/api/szenario/"):])))
                elif pfad == "/api/gesund":
                    self._json(200, {"ok": True})
                else:
                    raise api.ApiFehler(404, "Nicht gefunden")
            except api.ApiFehler as exc:
                self._fehler(exc)

        def do_POST(self) -> None:  # noqa: N802
            pfad = urlparse(self.path).path
            try:
                daten = self._body()
                if pfad == "/api/kalender":
                    ics = api.kalender(kb, daten).encode("utf-8")
                    self._senden(200, ics, "text/calendar; charset=utf-8",
                                 {"Content-Disposition": 'attachment; filename="buergerai-fristen.ics"'})
                elif pfad in post_routen:
                    self._json(200, post_routen[pfad](kb, daten))
                else:
                    raise api.ApiFehler(404, "Nicht gefunden")
            except api.ApiFehler as exc:
                self._fehler(exc)
            except Exception:  # pragma: no cover - Sicherheitsnetz, Details nur im Terminal
                import traceback

                traceback.print_exc()
                self._json(500, {"fehler": "Interner Fehler. Details stehen im Terminal, in dem der Server läuft."})

        def _body(self) -> Any:
            if not self.headers.get("Content-Type", "").startswith("application/json"):
                raise api.ApiFehler(415, "Content-Type application/json erwartet")
            try:
                laenge = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise api.ApiFehler(400, "Ungültige Länge") from exc
            if laenge <= 0 or laenge > MAX_BODY:
                raise api.ApiFehler(413 if laenge > MAX_BODY else 400, "Anfrage leer oder zu groß")
            try:
                return json.loads(self.rfile.read(laenge).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise api.ApiFehler(400, "Ungültiges JSON") from exc

    return Handler


def erstellen(kb: Wissensbasis, host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), handler_fuer(kb))
    server.daemon_threads = True
    return server


def starten(kb: Wissensbasis, host: str = "127.0.0.1", port: int = 8000, oeffnen: bool = False) -> int:
    try:
        server = erstellen(kb, host, port)
    except OSError as exc:
        print(f"Fehler: Port {port} ist nicht verfügbar ({exc.strerror}). Anderen Port wählen: --port 8001", file=sys.stderr)
        return 2
    adresse = f"http://{'localhost' if host in ('127.0.0.1', '0.0.0.0') else host}:{server.server_address[1]}/"
    print(f"BürgerAI Web-Oberfläche läuft auf {adresse}")
    print("In Codespaces: unten im Reiter 'Ports' auf die Weltkugel bei Port "
          f"{server.server_address[1]} klicken. Beenden mit Strg+C.")
    sys.stdout.flush()
    browser: Optional[threading.Timer] = None
    if oeffnen:
        browser = threading.Timer(0.5, lambda: webbrowser.open(adresse))
        browser.daemon = True
        browser.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer beendet.")
    finally:
        if browser is not None:
            browser.cancel()  # nach Strg+C keinen Browser mehr öffnen
        server.server_close()
    return 0
