# ADR 0003: Dreiwertige Regel-Engine (Ja / Nein / Unklar)

**Status:** angenommen · **Datum:** 24.10.2026

## Kontext
Die erste Implementierung wertete fehlende Angaben als „Nein“. Das widerspricht dem Prinzip „ehrlicher Fallback“ und kann Menschen von Anträgen abhalten, die ihnen zustehen.

## Entscheidung
- Regeln sind deklarative JSON-Bäume (`alle`, `eine`, `nicht`, `fakt`, `pruefung_noetig`) und werden nach Kleene-Logik ausgewertet.
- Fehlt eine Angabe, ist das Ergebnis **Unklar** und die Angabe wird als Rückfrage gemeldet – aber nur, wenn sie das Ergebnis noch ändern kann.
- „Weiß nicht“ ist ein eigener Wert: Ergebnis Unklar, keine erneute Rückfrage.
- `pruefung_noetig` steht für Voraussetzungen, die sich nicht sicher regelbasiert entscheiden lassen (z. B. Aufenthaltstitel). Solche Zweige ergeben höchstens Unklar – die Engine erfindet nie ein Ja.
- Jede Bedingung trägt einen lesbaren Text und Quellen; daraus entsteht die Begründung.

## Folgen
Der geführte Dialog („interaktiv“) ergibt sich direkt aus der Engine: Er fragt nur, was noch fehlt. Das ist auch die Grundlage für den formularbasierten Intake in Phase 2.
