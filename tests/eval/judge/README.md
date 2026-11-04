# Judge-Tests für den Router (#83)

Hier steht, welche Lebenslagen der Router zu einer Anfrage erkennen soll. Jede YAML-Datei in
diesem Ordner wird gelesen. Das Format steht in [`vorlage.yaml`](vorlage.yaml), die Router-Fälle
stehen in [`router.yaml`](router.yaml).

## Ausführen

```bash
./bai eval judge                       # alle Tests; ohne LLM prüft der Lauf die Stichwortsuche
./bai eval judge --nur geburt-kind-mai # einzelne Tests
./bai eval judge --details             # auch bestandene Prüfungen zeigen
./bai eval judge --judge               # Tests mit "experte" zusätzlich vom Judge-LLM bewerten
./bai eval judge --judge --wiederholungen 3   # jedes Urteil dreimal, bestanden nur einstimmig
./bai eval judge --json                # Ergebnis als JSON
```

Exit-Code: 0 alle bestanden, 1 mindestens ein Test fehlgeschlagen, 2 Fehler in den Tests oder in
der Konfiguration. PyYAML ist nötig (`python -m pip install pyyaml`, steht in `.[dev]`).

## Was geprüft wird

| Angabe im Test | Prüfung |
|---|---|
| `erwartet.kategorie` | genau diese Kategorie |
| `erwartet.lebenslagen` | genau diese Lebenslagen, Reihenfolge egal; `[]` heißt: keine |
| `erwartet.nicht_erwartet.lebenslagen` | keine davon gewählt |
| `experte` | nur mit `--judge`: Das Judge-LLM bewertet die Auswahl nach drei Ja/Nein-Kriterien (`kategorie`, `nichts_zu_viel`, `nichts_fehlt`) mit Begründung |
| `erwartet.fakten`, `erwartet.leistungen` | noch nicht geprüft (folgt mit Extraktion und Engine), werden gezählt |

Was nicht angegeben ist, wird nicht geprüft. Die exakten Prüfungen entscheiden immer; der Judge
kann einen Test zusätzlich durchfallen lassen, aber keinen retten.

## Judge-Modell

Der Judge soll ein anderes, stärkeres Modell sein als der Router, damit er dessen Fehler nicht
teilt. Er wird über eigene Variablen eingestellt. `BUERGERAI_JUDGE_*` ersetzt dabei das passende
`BUERGERAI_LLM_*`; Schlüssel (`GEMINI_API_KEY`, `MISTRAL_API_KEY`) gelten für beide.

```bash
BUERGERAI_JUDGE_ANBIETER=gemini
BUERGERAI_JUDGE_MODELL=gemini-2.5-pro
```

## Neue Tests

- Nur ausgedachte Anfragen, nie Texte echter Personen (ADR 0009 §5a).
- Keine Sätze aus dem Router-Prompt (`src/buergerai/llm/router.py`, Beispiele) übernehmen: sonst
  prüft der Test nur das Beispiel. Ein pytest-Test achtet darauf.
- Bei Verwechslungsgefahr die falsche Lebenslage unter `nicht_erwartet` nennen, z. B. `schule`
  bei „Wir bekommen ein Kind“.
- `pytest` prüft, dass alle Tests gültig sind (IDs aus dem Katalog, keine doppelten IDs), führt
  sie aber nicht mit einem LLM aus.
