# Prüfprotokoll: sgb5_24i

- Quelle: § 24i SGB V – Mutterschaftsgeld der Krankenkasse (bis 13 € je Kalendertag), https://www.gesetze-im-internet.de/sgb_5/__24i.html
- Fassung/Stand: recherchiert am 29.10.2026 über Websuche (gesetze-im-internet.de aus Entwicklungsumgebung und CI nicht erreichbar) · Stand „zuletzt geändert durch …“ beim lokalen Abgleich eintragen
- Geprüft von: Claude (Recherche) · Abnahme: <Name, Datum>
- Prüfstatus vorher: teilweise (2026-10-24, Claude (Websuche))
- Gerüst erzeugt am 2026-10-29 mit `./bai quellen --protokoll sgb5_24i`

> **Einschränkung:** Zitate aus Suchergebnissen (Gesetzesspiegel wie dejure.org, buzer.de, lxgesetze.de, rewis.io, Kommentare). Vor der Abnahme lokal prüfen: `./bai quellen --abgleich sgb5_24i --in-protokoll` – der Abgleich vergleicht jedes Zitat mit dem amtlichen XML von gesetze-im-internet.de.

## Verwendungen in der Wissensbasis (5)

| # | Verwendung in der Wissensbasis | Fundstelle | Wortlaut der Quelle (Zitat, Absatz) | Ergebnis |
|---|---|---|---|---|
| 1 | mutterschaftsgeld_krankenkasse: Betrag „bis zu 13 € je Kalendertag während der Schutzfristen (der Arbeitgeber stockt auf)“ | `fachmodule/familie/geburt.json` `leistungen[3].betraege[0]` | Abs. 2: „höchstens 13 Euro für den Kalendertag“; den übersteigenden Betrag zahlt der Arbeitgeber nach dem Mutterschutzgesetz | ✅ |
| 2 | mutterschaftsgeld_krankenkasse_bund: Variante „Leistung mutterschaftsgeld_krankenkasse in Gebiet DE“ | `fachmodule/familie/geburt.json` `varianten[3]` | Abs. 1 Satz 1: „Weibliche Mitglieder, die bei Arbeitsunfähigkeit Anspruch auf Krankengeld haben oder denen wegen der Schutzfristen nach § 3 des Mutterschutzgesetzes kein Arbeitsentgelt gezahlt wird, erhalten Mutterschaftsgeld.“ | ✅ |
| 3 | mutterschaftsgeld_krankenkasse_bund: Bedingung „Die Mutter ist selbst Mitglied einer gesetzlichen Krankenkasse (mutter.krankenversicherung == "gesetzlich_mitglied")“ | `fachmodule/familie/geburt.json` `varianten[3].regel.alle[0]` | wie Nr. 2: „Weibliche Mitglieder“ | ✅ |
| 4 | mutterschaftsgeld_krankenkasse_bund: Bedingung „Die Mutter ist angestellt (mutter.beschaeftigt == true)“ | `fachmodule/familie/geburt.json` `varianten[3].regel.alle[1].eine[0]` | wie Nr. 2: kein Arbeitsentgelt wegen der Schutzfristen | ✅ |
| 5 | mutterschaftsgeld_krankenkasse_bund: Bedingung „Die Mutter hat Anspruch auf Krankengeld (mutter.krankengeldanspruch == true)“ | `fachmodule/familie/geburt.json` `varianten[3].regel.alle[1].eine[1]` | wie Nr. 2: Anspruch auf Krankengeld | ✅ |

Ergebnis: ✅ stimmt mit dem Wortlaut überein · ❌ weicht ab (Korrektur nötig) · ⚠️ unklar oder nur teilweise belegt

## Abweichungen und Folgeaktionen

- Keine.
