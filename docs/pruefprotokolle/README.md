# Prüfprotokolle

Je Quelle ein Protokoll `<quelle-id>.md`: Was behauptet die Wissensbasis, was steht im Volltext der Quelle, stimmt es überein? Das Protokoll ist die Grundlage für die Abnahme durch einen Menschen (ADR 0004, ANF-QS-02) und die Vorlage für die Pflege in Phase 4.

## Ablauf

1. **Verwendungen ansehen:** `./bai quellen --verwendung <id>` listet jede Bedingung, Frist, jeden Betrag, jede Zuständigkeit und jedes Gebiet, das die Quelle zitiert, mit Datei und JSON-Pfad.
2. **Gerüst anlegen:** `./bai quellen --protokoll <id>` schreibt `docs/pruefprotokolle/<id>.md` nach der Vorlage unten, die Tabelle ist mit allen Verwendungen vorbefüllt. Ein vorhandenes Protokoll wird nicht überschrieben.
3. **Volltext lesen:** aktuelle Fassung abrufen. Bei Gesetzen „zuletzt geändert durch …“, bei Behördenseiten das Abrufdatum eintragen.
4. **Abgleichen:** je Zeile den Wortlaut (mit Absatz) zitieren und das Ergebnis setzen. Bei Fristen auch Beginn, Dauer, „Tag zählt mit?“ und das Ende an Wochenenden prüfen; bei Beträgen den Gültigkeitszeitraum.
5. **Bei Abweichung:** Daten oder Regel korrigieren und einen Test oder ein Szenario ergänzen, das den Fehler gefunden hätte. Unter „Abweichungen und Folgeaktionen“ den PR nennen.
6. **Status setzen und verlinken:** In der Quelle (`data/**/quellen`) `pruefstatus`, `geprueft_am`, `geprueft_von` setzen und in `notiz` auf `docs/pruefprotokolle/<id>.md` verweisen. `./bai daten` warnt bei geprüften Quellen ohne verlinktes Protokoll.
7. `./bai daten && ./bai szenarien --pruefen && python -m pytest`

**Claude setzt nie `verifiziert`,** höchstens `teilweise` mit vollständigem Protokoll. `verifiziert` setzt ein Mensch nach Durchsicht des Protokolls, mit eigenem Namen und Datum.

Nur die Quellen der Pilotregion (Phase 1, Issue #45): `./bai quellen --phase1 --offen`

## Ergebnis je Zeile

| Symbol | Bedeutung |
|---|---|
| ✅ | stimmt mit dem Wortlaut überein |
| ❌ | weicht ab – Korrektur nötig (mit Test oder Szenario) |
| ⚠️ | unklar oder nur teilweise belegt – offene Frage benennen |

## Vorlage

```markdown
# Prüfprotokoll: <quelle-id>

- Quelle: <Titel>, <URL>
- Fassung/Stand: <z. B. zuletzt geändert durch Art. X G v. TT.MM.JJJJ> · abgerufen am <Datum>
- Geprüft von: Claude (Recherche) · Abnahme: <Name, Datum>

## Verwendungen in der Wissensbasis

| # | Verwendung in der Wissensbasis | Fundstelle | Wortlaut der Quelle (Zitat, Absatz) | Ergebnis |
|---|---|---|---|---|
| 1 | elterngeld_bund: Bedingung „Arbeitet höchstens 32 Stunden pro Woche“ | `fachmodule/familie/geburt.json` `varianten[7].regel.alle[3]` | § 1 Abs. 6 Nr. 1 BEEG: „…“ | ✅ |

## Abweichungen und Folgeaktionen

- …
```
