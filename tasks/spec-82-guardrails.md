# Spec: Guardrails für die Freitext-Eingabe (#82)

Stand 02.11.2026, Basis `origin/main` (e9ac735, nach #73, #75, #76, #77, #79).

## Ziel

BürgerAI beantwortet per Freitext nur Fragen zu Lebenslagen, Leistungen und Behörden.
Missbrauch darf weder Kosten verursachen noch falsche Ergebnisse erzeugen. Jede
Schutzregel ist eine Anforderung `ANF-GR-*` mit Test (ANF-QS-01) und steht als
Katalog in ADR 0009.

## Bestandsaufnahme: was schon da ist

| Regel aus #82 | Stand | Wo |
|---|---|---|
| Router-Kategorien `kein_thema`, `umgehung`, `rechtsberatung`, `notlage` | erledigt | `llm/router.py` (#76) |
| Feste Hinweistexte je Kategorie, nicht vom LLM | erledigt (Texte als „vorläufig“ markiert) | `router.HINWEISE` |
| Freitext als Daten, abgegrenzt, keine Werkzeuge, Ausgabe nur Katalogwerte | erledigt | Router-Prompt, `schema.py` (#75) |
| Nach dem LLM: Schema, `parse_wert`, Beleg im Text | erledigt | `schema.py`, `extraktion.py` (#75, #77) |
| Fakten nur nach Bestätigung | erledigt | `/api/intake` liefert nur Vorschläge (#79, ANF-LLM-18) |
| Refusal / ungültige Ausgabe → Fallback statt Fehlerseite | erledigt | `erkennen`, `intake` (ANF-LLM-05) |
| Längengrenze | da, aber 2.000 statt ~1.000 Zeichen | `api.MAX_FREITEXT`, `MAX_ANTWORT = 500` |
| `max_tokens` je Aufgabe | da, aber verstreut (600 / 1500) | `router.py`, `extraktion.py` |
| Hinweis „Unverbindliche Orientierung, keine Rechtsberatung“ | da | `index.html`, `.ics`, Terminal |
| Negativfälle in der Evaluation (10/10/5/5/5) | erledigt | `tests/eval/intake/guardrails.json` |
| Abweisungsquote und Quote der fälschlichen Abweisungen | erledigt | `evaluation.kennzahlen` |

## Was dieses Issue noch baut

1. **Rate-Limit je IP** für `POST /api/intake` und `POST /api/antwort`
   (10 pro Minute, 100 pro Tag, gemeinsamer Zähler). Bei Überschreitung HTTP 429 mit festem
   Hinweis „Bitte nutzen Sie die Auswahl und das Formular“. Suche, Formular und Bericht
   bleiben ohne Limit. Die IP liegt nur im Speicher und nur, solange das Fenster läuft.
2. **Kostendeckel** je Tag und Monat. Ist er erreicht, verhält sich die Anwendung wie ohne
   LLM (Fallback: Stichwortsuche und Formular) bis zum nächsten Zeitraum. Grenzen per
   Umgebungsvariable. → *Offene Frage 1*
3. **Cache für gleiche Anfragen** (nur im Speicher, z. B. 10 Minuten, höchstens 256 Einträge,
   Schlüssel = SHA-256 aus Aufgabe, Prompt und Eingabe). Ein Treffer ruft das Modell nicht
   auf und zählt nicht gegen den Kostendeckel. Kein Freitext in Logs.
4. **`max_tokens` fest je Aufgabe** an einer Stelle (`router` 600, `extraktion` 1500),
   per Test abgesichert.
5. **Notlagen-Stichwortliste im Code** (z. B. „umbringen“, „Suizid“, „schlägt mich“,
   „kein Schlafplatz“, „obdachlos“): Trifft sie, erscheint der Notlage-Hinweis immer, auch
   ohne LLM, bei LLM-Fehler und wenn das LLM eine andere Kategorie wählt. Erkannte
   Lebenslagen bleiben erhalten.
6. **Injection-Tests mit `FakeLLM`** als `ANF-GR-*`: Eine Injection kann keine Fakten ohne
   Bestätigung setzen, keine Lebenslage außerhalb des Katalogs erzeugen, und bei
   `kein_thema`/`umgehung`/`rechtsberatung` kommt kein Fakt durch.
7. **Katalog der Schutzregeln** als neuer Abschnitt §8 in ADR 0009, mit Verweis auf #82,
   je Regel die Schicht (vor / im / nach dem LLM) und die `ANF-GR`-Nummer.
8. **Anforderungen `ANF-GR-01 …`** in `docs/anforderungen.json`; bereits erfüllte Regeln
   bekommen die Markierung an vorhandenen oder kleinen neuen Tests.

## Nicht in diesem Issue

- **Formulierung (#78):** „Injection erreicht den Antworttext nicht“, „keine Zusagen“,
  „keine Links/Nummern/Beträge außerhalb des Berichts“. Die Regeln kommen in den Katalog
  (ADR §8), Code und Test mit #78, weil es den Formulierungsschritt noch nicht gibt.
- **Tokenzählung (#80)** – siehe Offene Frage 1.
- Echte Proxy-Konfiguration (`X-Forwarded-For`) für das Hosting (#6): Das Rate-Limit nutzt
  die Adresse der Verbindung; Header werden nicht ausgewertet, weil sie fälschbar sind.

## Technik und Struktur

- Nur Standardbibliothek (ADR 0002). Kein neues Paket.
- Neues Modul `src/buergerai/llm/schutz.py`: Notlagen-Stichworte, Rate-Limit (Klasse mit
  Zeitquelle als Parameter, damit Tests ohne Warten laufen), Kostendeckel und Cache als
  Hülle um ein `LLM` (gleiche Schnittstelle `strukturiert`/`text`, `name`).
- `web/server.py`: Rate-Limit vor den Freitext-Routen, 429 über `ApiFehler`.
- `llm/konfiguration.py`: Grenzen aus Umgebungsvariablen, die Hülle wird in
  `llm_aus_umgebung` bzw. beim Serverstart um das Modell gelegt.
- Tests: `tests/test_llm_schutz.py` (Einheit) und Ergänzungen in `tests/test_web_freitext.py`.

## Befehle

```
python -m pytest
python -m pyflakes src tests scripts
./bai anforderungen          # jede Anforderung hat einen Test
./bai eval intake            # Abweisungsquoten (Baseline ohne LLM)
```

## Stil

Wie im Bestand: deutsche Bezeichner, Dataclasses, Docstring mit Issue/ADR-Verweis,
Logs nur mit IDs und Zahlen (ADR 0009 §3), Tests mit `@pytest.mark.anforderung("ANF-GR-…")`.

## Grenzen

- Immer: Tests ohne Netz (`FakeLLM`), kein Freitext und keine IP in Logs oder Dateien.
- Erst fragen: neue Abhängigkeiten, Änderung der festen Hinweistexte über den Feinschliff
  hinaus, Änderung bestehender Anforderungen `ANF-LLM-*`.
- Nie: Freitext kürzen und trotzdem ans Modell schicken, Limits auf die Formular-Strecke
  legen, Schlüssel oder Prompts preisgeben.

## Erfolgskriterien

- [x] ADR 0009 §8: Katalog aller Regeln aus #82 mit Schicht, Status und `ANF-GR`-Nummer
- [x] 11. Freitext-Anfrage derselben IP in einer Minute → 429 mit Hinweis; Formular-Routen nie 429
- [x] Kostendeckel erreicht → `/api/intake` antwortet mit `quelle: "fallback"`, ohne Modellaufruf
- [x] Zweite identische Anfrage → kein zweiter Aufruf beim `FakeLLM`
- [x] Router-Aufruf mit 600, Extraktion mit 1500 `max_tokens` (Test über `FakeLLM.aufrufe`)
- [x] Notlagen-Text ohne LLM, mit LLM-Fehler und bei LLM-Kategorie `lebenslage` → Notlage-Hinweis
- [x] Injection-Fälle mit `FakeLLM`: keine Fakten ohne Bestätigung, nichts außerhalb des Katalogs
- [x] `./bai anforderungen`, `pyflakes` und `pytest` grün

## Entscheidungen (02.11.2026 freigegeben)

1. **Kostendeckel ohne #80** (umgesetzt wie vorgeschlagen): Der Adapter kennt die Tokenzahlen nur im Log. Vorschlag: jetzt
   ein Deckel auf die Zahl der Modellaufrufe je Tag/Monat, mit #80 auf Tokens umstellen.
2. **Längengrenze** (umgesetzt wie vorgeschlagen): #79 hat 2.000 Zeichen gewählt, #82 nennt „z. B. 1.000“. Vorschlag: 2.000
   lassen (lange Beschreibungen mehrerer Lebenslagen), Regel und Test unter `ANF-GR`.
3. **Notlagen-Hinweis bei Stichwort-Treffer** (umgesetzt wie vorgeschlagen): Vorschlag: Hinweis zeigen, aber nicht abweisen
   (Lebenslagen und Fakten bleiben), wie es der Router schon für `notlage` tut.
