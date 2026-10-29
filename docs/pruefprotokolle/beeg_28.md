# Prüfprotokoll: beeg_28

- Quelle: § 28 BEEG – Übergangsvorschrift (u. a. Einkommensgrenze 200.000 € für Geburten 1.4.2024–31.3.2025), https://www.gesetze-im-internet.de/beeg/__28.html
- Fassung/Stand: recherchiert am 29.10.2026 über Websuche (gesetze-im-internet.de aus Entwicklungsumgebung und CI nicht erreichbar) · Stand „zuletzt geändert durch …“ beim lokalen Abgleich eintragen
- Geprüft von: Claude (Recherche) · Abnahme: <Name, Datum>
- Prüfstatus vorher: teilweise (2026-10-29, Claude (Websuche))
- Gerüst erzeugt am 2026-10-29 mit `./bai quellen --protokoll beeg_28`

> Bisherige Notiz: § 28 Abs. 5: Für Geburten vom 1.4.2024 bis 31.3.2025 gilt § 1 Abs. 8 mit der Grenze 200.000 € (auch für die Summe beider Elternteile); eine eigene Grenze für Alleinerziehende (150.000 €) stand nur im Entwurf. Über Suchergebnisse (rewis.io, Haufe), Volltext nicht abrufbar. Prüfprotokoll: docs/pruefprotokolle/beeg_28.md
>
> **Einschränkung:** Zitate aus Suchergebnissen (Gesetzesspiegel wie dejure.org, buzer.de, lxgesetze.de, rewis.io, Kommentare). Vor der Abnahme lokal prüfen: `./bai quellen --abgleich beeg_28 --in-protokoll` – der Abgleich vergleicht jedes Zitat mit dem amtlichen XML von gesetze-im-internet.de.

## Verwendungen in der Wissensbasis (3)

| # | Verwendung in der Wissensbasis | Fundstelle | Wortlaut der Quelle (Zitat, Absatz) | Ergebnis |
|---|---|---|---|---|
| 1 | elterngeld_bund: Bedingung „Geburt ab dem 1.4.2024 (geburtsdatum_oder_termin >= "2024-04-01")“ – gilt per erbt_von auch für 57 weitere Varianten (elterngeld_bb, elterngeld_be, elterngeld_bw, …) | `fachmodule/familie/geburt.json` `varianten[7].regel.alle[5].eine[1].alle[0]` | Abs. 5: Übergangsregel für Kinder, die vom 1. April 2024 bis 31. März 2025 geboren sind | ✅ inhaltlich laut rewis.io/Haufe |
| 2 | elterngeld_bund: Bedingung „Geburt vor dem 1.4.2025 (geburtsdatum_oder_termin < "2025-04-01")“ | `fachmodule/familie/geburt.json` `varianten[7].regel.alle[5].eine[1].alle[1]` | wie Nr. 1 | ✅ |
| 3 | elterngeld_bund: Bedingung „Zu versteuerndes Einkommen höchstens 200.000 € (zve_eltern <= 200000)“ | `fachmodule/familie/geburt.json` `varianten[7].regel.alle[5].eine[1].alle[2]` | Abs. 5: „mit der Maßgabe, dass ein Anspruch entfällt, wenn die berechtigte Person im letzten abgeschlossenen Veranlagungszeitraum vor der Geburt des Kindes ein zu versteuerndes Einkommen nach § 2 Absatz 5 des Einkommensteuergesetzes in Höhe von mehr als 200 000 Euro erzielt hat“ | ✅ auch für die Summe beider Elternteile (Abs. 5 Satz 3) |

Ergebnis: ✅ stimmt mit dem Wortlaut überein · ❌ weicht ab (Korrektur nötig) · ⚠️ unklar oder nur teilweise belegt

## Abweichungen und Folgeaktionen

- Neu angelegt; vorher wurden diese Bedingungen § 1 BEEG zugeordnet (siehe [beeg_1](beeg_1.md)).
