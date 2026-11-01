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

Die Dateien enthalten **keine Freitexte und keine Schlüssel**. Die Texte stehen in `tests/eval/intake` und werden über die `id` gefunden.

## Was eingecheckt wird

Nur Läufe, die etwas belegen, z. B. den Nachweis „Router besser als Baseline“ in einem PR. Ein Lauf zählt nur, wenn unter `kennzahlen.fallback` nichts steht; sonst mischen sich LLM und Stichwortsuche. Probeläufe einfach löschen.
