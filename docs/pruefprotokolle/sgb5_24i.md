# Prüfprotokoll: sgb5_24i

- Quelle: § 24i SGB V – Mutterschaftsgeld der Krankenkasse (bis 13 € je Kalendertag), https://www.gesetze-im-internet.de/sgb_5/__24i.html
- Fassung/Stand: amtliches XML von gesetze-im-internet.de, abgerufen am 30.10.2026 · zuletzt geändert durch Art. 1 G v. 26.6.2026 I Nr. 195 (Recherche vorher am 29.10.2026 per Websuche)
- Geprüft von: Claude (Recherche 29.10.2026, Abgleich mit dem amtlichen XML 30.10.2026) · Abnahme: <Name, Datum>
- Prüfstatus vorher: teilweise (2026-10-24, Claude (Websuche))
- Gerüst erzeugt am 2026-10-29 mit `./bai quellen --protokoll sgb5_24i`

> **Abgleich:** Die Zitate stammen aus der Websuche vom 29.10.2026 und wurden am 30.10.2026 mit `./bai quellen --abgleich sgb5_24i` gegen das amtliche XML von gesetze-im-internet.de geprüft (Ergebnis unten unter „Automatischer Abgleich“).

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

- Keine. **Abgleich 30.10.2026:** alle Zitate wörtlich im amtlichen Text, „13“ in Abs. 2 gefunden.

## Automatischer Abgleich

Stand 30.10.2026 (`./bai quellen --abgleich sgb5_24i`): Zitate 3/3 · Zahlen 1/1 · Stand: Zuletzt geändert durch Art. 1 G v. 26.6.2026 I Nr. 195

Geprüfter Abschnitt: § 24i SGB 5

- ✅ alle Zitate und Zahlen gefunden
