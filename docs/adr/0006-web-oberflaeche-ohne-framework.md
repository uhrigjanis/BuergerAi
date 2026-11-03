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

## Nachtrag 02.11.2026: viele Lebenslagen und Freitext (#86, #79)

- **Module statt einer Datei:** `app.js` ist der Einstieg und lädt ES-Module (`start.js`, `frage.js`, `checkliste.js`, `detail.js`, `vorschlaege.js`, `gemeinsam.js`). Ohne Build-Schritt; mit `default-src 'self'` erlaubt. Der Server liefert nur die Dateien aus seiner Liste (`server.MODULE`).
- **Zusätzliche Felder, gleiche Engine:** `fragen[].betrifft` (Leistungen, über die eine Frage entscheidet oder deren Frist sie festlegt), `fristen[].gruppe` und `leistungen[].zeitgruppe` (Abgelaufen, Diese Woche, …), `leistungen[].klaeren_mit` (stärkste offene Frage). Die Ergebnisse bleiben dieselben wie im Terminal.
- **Neue Endpunkte:** `POST /api/suche` (Stichwortsuche, ohne LLM). Nur mit konfiguriertem LLM: `POST /api/intake` (Freitext → Lebenslagen und Vorschläge mit Beleg) und `POST /api/antwort` (freie Antwort auf eine offene Frage → Vorschläge). `/api/meta` meldet `freitext`. Beide Freitext-Endpunkte rechnen keinen Bericht: Erst die vom Nutzer bestätigten Angaben gehen an `/api/bericht` (ADR 0009 §1).
- **Zustandslos wie bisher:** Freitexte werden weder auf dem Server noch im Browser gespeichert; `localStorage` enthält nur bestätigte Angaben.

## Nachtrag 03.11.2026: Design-Richtlinie (#99)

- **Richtlinie:** Die Oberfläche folgt [`docs/design/ClaudeDesign.md`](../design/ClaudeDesign.md). Eine zentrierte Spalte (`48rem`), neutrale Flächen und genau ein Akzent (Indigo). Abstand statt Rahmen, Typografie statt Symbole. Nebensächliches erscheint erst bei Bedarf.
- **Kein Tailwind:** Die Tokens der Richtlinie stehen als CSS-Variablen in `style.css` (`:root`, hell und dunkel). Tailwind-Angaben wie `max-w-3xl`, `leading-relaxed`, `shadow-sm` und `duration-200` gelten nur als Maße. Kein Build-Schritt, keine externen Ressourcen, die CSP bleibt unverändert.
- **Barrierefreiheit vor Wortlaut:**
  - `#6366F1` erreicht als Textfarbe im hellen Modus kein AA. Deshalb nutzen Füllungen und Links `--accent-strong` (Indigo 600, 6,3 : 1). `--accent` dient nur für Fokus und Indikatoren (≥ 3 : 1).
  - Knöpfe und Links behalten einen sichtbaren `:focus-visible`-Ring. Nur Eingabefelder wechseln auf den Akzentrand.
  - Eingabefelder behalten einen Rand in `--text-muted` (WCAG 1.4.11).
- **Ergebnis als Wort:** Ja, Unklar und Nein stehen als Text und unterscheiden sich über Schriftgewicht und Ton, ohne ✓/✗. Den Akzent bekommen nur abgelaufene Fristen und Fehlermeldungen. Ihre eigenen Worte (#79) werden mit dem Akzent in geringer Deckkraft markiert.
- **Aufbau:** Die Frage steht oben und die Checkliste darunter, auf allen Bildschirmen (die Reiter entfallen). Angaben, Lebenslagen, Datum, Speichern/Öffnen und „Neu beginnen“ liegen in einer Schublade (`<dialog id="schublade">`). Den Kalender gibt es nur bei datierten Fristen.
- **Prüfung:** `tests/test_web_design.py` (ANF-WEB-15) prüft die Tokens, Farben nur in `:root` und die Kontraste. `scripts/web_rauchtest.py` ist der Browser-Rauchtest (Playwright, optional).
