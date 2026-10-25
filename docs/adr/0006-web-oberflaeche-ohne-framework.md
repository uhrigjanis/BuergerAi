# ADR 0006: Web-Oberfläche mit Standardbibliothek und Vanilla-JavaScript

**Status:** angenommen · **Datum:** 25.10.2026

## Kontext
Phase 2 braucht einen formularbasierten Intake mit einfacher Web-UI. Das Projekt hat bewusst keine Laufzeit-Abhängigkeiten (ADR 0002). Die Oberfläche soll fast nichts im Betrieb kosten und später als Notbremse dienen, wenn das LLM-Budget erreicht ist.

## Entscheidung
- **Server:** `http.server.ThreadingHTTPServer` aus der Standardbibliothek (`buergerai web`). Kein Flask/FastAPI.
- **API:** wenige JSON-Endpunkte (`/api/meta`, `/api/ort`, `/api/bericht`, `/api/kalender`, `/api/szenario/<id>`). Die Logik liegt in `web/api.py` und ruft dieselbe Engine wie das Terminal (`planer.planen`). Es gibt keine zweite Regel-Logik im Browser.
- **Zustandslos:** Der Browser hält die Angaben (localStorage) und schickt sie bei jeder Antwort komplett mit. Der Server speichert und protokolliert nichts.
- **Oberfläche:** eine HTML-Seite, eine CSS- und eine JS-Datei, ohne Framework, Build-Schritt oder externe Ressourcen. Strikte Content-Security-Policy (`default-src 'self'`).
- **Fragenfolge:** Der Server liefert die offenen Fragen (`fehlend` des Berichts). Die Oberfläche zeigt immer die erste, passend zum Typ (Ja/Nein-Buttons, Auswahl-Buttons, Datum, Zahl) und immer mit „Weiß nicht“.

## Folgen
- Start ohne Installation (`./bai web`), auch in Codespaces (Port 8000 wird automatisch weitergeleitet).
- Für einen öffentlichen Betrieb (Phase 5) fehlen noch: TLS, Rate-Limit und ein produktionsreifer Server davor (z. B. Reverse Proxy). Die API ist dafür klein genug.
- Neue Fragetypen brauchen eine Erweiterung in `app.js` (`eingabe`).
