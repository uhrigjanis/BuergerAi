# Ergebnisse der Evaluation (#73, #76)

Jeder Lauf von `./bai eval intake` schreibt hier eine Datei
`<Datum>_<Uhrzeit>_<Verfahren>[_<Modell>].json`, z. B. `2026-11-02_153012_llm_mistral-small-latest.json`.

```bash
./bai eval intake --verfahren llm --pause 3       # schreibt automatisch hierhin
./bai eval intake --ausgabe lauf.json             # anderer Ort
./bai eval intake --keine-datei                   # nichts schreiben
```

## Inhalt

| Feld | Bedeutung |
|---|---|
| `zeitpunkt`, `commit` | wann und mit welchem Stand des Codes gemessen wurde |
| `verfahren`, `modell` | z. B. `llm` und `mistral/mistral-small-latest`; `null` bei der Stichwortsuche |
| `kennzahlen` | dieselben Zahlen wie in der Textausgabe, inkl. `fallback` (wie oft und warum die Stichwortsuche galt) |
| `faelle` | je Fall: erwartete und erkannte Kategorie und Lebenslagen, Top-1/Top-3, Fallback-Grund, Fakten richtig/falsch/fehlend |

## Judge-Tests (`judge/`)

`./bai eval judge` schreibt je Lauf `judge/<Datum>_<Uhrzeit>_<Router-Modell>[_judge-<Modell>].yaml`,
z. B. `judge/2026-11-04_193005_gemini-2.5-flash-lite_judge-gemini-2.5-pro.yaml`. Ohne LLM heißt der
Router `stichwortsuche`.

| Feld | Bedeutung |
|---|---|
| `zeitpunkt`, `commit` | wann und mit welchem Stand des Codes |
| `router`, `judge`, `wiederholungen` | Modelle des Laufs; `judge: null` ohne `--judge` |
| `zusammenfassung` | bestanden, fehlgeschlagene IDs, Fallbacks, Judge-Urteile, nicht geprüfte Fakten und Leistungen |
| `tests` | je Test: `erkannt` (Kategorie, Lebenslagen, Quelle, Fallback-Grund), `befunde` der exakten Prüfungen, `judge` (Stimmen und Begründungen je Kriterium) |

Die Anfrage steht nicht in der Datei, sondern in `tests/eval/judge/<datei>` unter derselben `id`.
Die Begründungen des Judges sind Modelltext über ausgedachte Anfragen.

Keine der Dateien enthält Schlüssel oder die Anfragen. Die Intake-Dateien enthalten gar keine Freitexte; die Texte stehen in `tests/eval/intake` und werden über die `id` gefunden.

## Was eingecheckt wird

Nur Läufe, die etwas belegen, z. B. den Nachweis „Router besser als Baseline“ in einem PR. Ein Lauf zählt nur, wenn unter `kennzahlen.fallback` nichts steht; sonst mischen sich LLM und Stichwortsuche. Probeläufe einfach löschen.
