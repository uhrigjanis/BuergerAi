# Prüfprotokoll: pstg_18

- Quelle: § 18 PStG – Anzeige der Geburt (innerhalb einer Woche), https://www.gesetze-im-internet.de/pstg/__18.html
- Fassung/Stand: recherchiert am 29.10.2026 über Websuche (gesetze-im-internet.de aus Entwicklungsumgebung und CI nicht erreichbar) · Stand „zuletzt geändert durch …“ beim lokalen Abgleich eintragen
- Geprüft von: Claude (Recherche) · Abnahme: <Name, Datum>
- Prüfstatus vorher: teilweise (2026-10-24, Claude (Websuche))
- Gerüst erzeugt am 2026-10-29 mit `./bai quellen --protokoll pstg_18`

> Bisherige Notiz: Frist eine Woche, Geburtstag zählt nicht mit, Anzeige gebührenfrei (FIM-Stammtext). Paragraf selbst noch im Volltext prüfen.
>
> **Einschränkung:** Zitate aus Suchergebnissen (Gesetzesspiegel wie dejure.org, buzer.de, lxgesetze.de, rewis.io, Kommentare). Vor der Abnahme lokal prüfen: `./bai quellen --abgleich pstg_18 --in-protokoll` – der Abgleich vergleicht jedes Zitat mit dem amtlichen XML von gesetze-im-internet.de.

## Verwendungen in der Wissensbasis (4)

| # | Verwendung in der Wissensbasis | Fundstelle | Wortlaut der Quelle (Zitat, Absatz) | Ergebnis |
|---|---|---|---|---|
| 1 | geburtsanzeige_bund: Variante „Leistung geburtsanzeige in Gebiet DE“ – gilt per erbt_von auch für 2 weitere Varianten (geburtsanzeige_by, geburtsanzeige_muenchen) | `fachmodule/familie/geburt.json` `varianten[0]` | Abs. 1 Satz 1: „Die Geburt eines Kindes ist dem Standesamt, in dessen Zuständigkeitsbereich es geboren ist, binnen einer Woche anzuzeigen“ | ✅ zuständig ist das Standesamt des Geburtsorts |
| 2 | geburtsanzeige_bund: Frist „Geburt innerhalb einer Woche anzeigen (der Geburtstag zählt nicht mit)“ | `fachmodule/familie/geburt.json` `varianten[0].verfahren.fristen[0]` | wie Nr. 1: „binnen einer Woche“; der Tag der Geburt zählt nach § 187 Abs. 1 BGB nicht mit | ✅ |
| 3 | geburtsanzeige_muenchen: Variante „Leistung geburtsanzeige in Gebiet 09162000“ | `kommunen/09162000/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 4 | geburtsanzeige_muenchen: Frist „Geburt innerhalb einer Woche anzeigen (der Geburtstag zählt nicht mit)“ | `kommunen/09162000/geburt.json` `varianten[0].verfahren.fristen[0]` | wie Nr. 2 | ✅ |

Ergebnis: ✅ stimmt mit dem Wortlaut überein · ❌ weicht ab (Korrektur nötig) · ⚠️ unklar oder nur teilweise belegt

## Abweichungen und Folgeaktionen

- Keine. Die frühere Formulierung „muss … angezeigt werden“ gilt seit 1.11.2022 nicht mehr; Inhalt unverändert.
