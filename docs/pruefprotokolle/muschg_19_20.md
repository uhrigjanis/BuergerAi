# Prüfprotokoll: muschg_19_20

- Quelle: §§ 19, 20 MuSchG – Mutterschaftsgeld, Arbeitgeberzuschuss, https://www.gesetze-im-internet.de/muschg_2018/__19.html
- Fassung/Stand: recherchiert am 29.10.2026 über Websuche (gesetze-im-internet.de aus Entwicklungsumgebung und CI nicht erreichbar) · Stand „zuletzt geändert durch …“ beim lokalen Abgleich eintragen
- Geprüft von: Claude (Recherche) · Abnahme: <Name, Datum>
- Prüfstatus vorher: teilweise (2026-10-24, Claude (Websuche))
- Gerüst erzeugt am 2026-10-29 mit `./bai quellen --protokoll muschg_19_20`

> Bisherige Notiz: Privat oder familienversicherte Arbeitnehmerinnen: einmalig bis 210 € vom Bundesamt für Soziale Sicherung; Arbeitgeber zahlt Zuschuss. Schutzfrist i. d. R. 6 Wochen vor, 8 Wochen nach der Geburt.
>
> **Einschränkung:** Zitate aus Suchergebnissen (Gesetzesspiegel wie dejure.org, buzer.de, lxgesetze.de, rewis.io, Kommentare). Vor der Abnahme lokal prüfen: `./bai quellen --abgleich muschg_19_20 --in-protokoll` – der Abgleich vergleicht jedes Zitat mit dem amtlichen XML von gesetze-im-internet.de.

## Verwendungen in der Wissensbasis (9)

| # | Verwendung in der Wissensbasis | Fundstelle | Wortlaut der Quelle (Zitat, Absatz) | Ergebnis |
|---|---|---|---|---|
| 1 | mutterschaftsgeld_bas: Betrag „einmalig höchstens 210 € für die gesamte Schutzfrist“ | `fachmodule/familie/geburt.json` `leistungen[4].betraege[0]` | § 19 Abs. 2: Mutterschaftsgeld zu Lasten des Bundes, „jedoch insgesamt höchstens 210 Euro“, gezahlt vom Bundesamt für Soziale Sicherung | ✅ |
| 2 | arbeitgeberzuschuss_mutterschaftsgeld: Betrag „Unterschied zwischen 13 € je Kalendertag und dem durchschnittlichen Nettoarbeitsentgelt“ | `fachmodule/familie/geburt.json` `leistungen[5].betraege[0]` | § 20 Abs. 1: Zuschuss in Höhe des „Unterschiedsbetrag zwischen 13 Euro und dem um die gesetzlichen Abzüge verminderten durchschnittlichen kalendertäglichen Arbeitsentgelt“ | ✅ |
| 3 | mutterschaftsgeld_krankenkasse_bund: Frist „Vor Beginn der Schutzfrist (6 Wochen vor dem Termin) beantragen“ | `fachmodule/familie/geburt.json` `varianten[3].verfahren.fristen[1]` | Das Gesetz nennt keine Antragsfrist | ⚠️ Empfehlung, keine gesetzliche Frist – Text sagt „beantragen“, Art „spaetestens“ prüfen |
| 4 | mutterschaftsgeld_bas_bund: Variante „Leistung mutterschaftsgeld_bas in Gebiet DE“ | `fachmodule/familie/geburt.json` `varianten[4]` | § 19 Abs. 2: Frauen, die nicht Mitglied einer gesetzlichen Krankenkasse sind | ✅ |
| 5 | mutterschaftsgeld_bas_bund: Bedingung „Die Mutter ist angestellt (mutter.beschaeftigt == true)“ | `fachmodule/familie/geburt.json` `varianten[4].regel.alle[0]` | § 19 Abs. 2: wenn sie bei Beginn der Schutzfrist in einem Arbeitsverhältnis stehen | ✅ Sonderfall zulässig aufgelöstes Arbeitsverhältnis nicht modelliert |
| 6 | mutterschaftsgeld_bas_bund: Bedingung „Die Mutter ist privat oder familienversichert (kein eigenes Kassenmitglied) (mutter.krankenversicherung in ["privat", "gesetzlich_familienversichert"])“ | `fachmodule/familie/geburt.json` `varianten[4].regel.alle[1]` | § 19 Abs. 2: „nicht Mitglied einer gesetzlichen Krankenkasse“ – privat oder familienversichert | ✅ |
| 7 | mutterschaftsgeld_bas_bund: Frist „Vor Beginn der Schutzfrist (6 Wochen vor dem Termin) beantragen“ | `fachmodule/familie/geburt.json` `varianten[4].verfahren.fristen[0]` | wie Nr. 3 | ⚠️ wie Nr. 3 |
| 8 | arbeitgeberzuschuss_mutterschaftsgeld_bund: Variante „Leistung arbeitgeberzuschuss_mutterschaftsgeld in Gebiet DE“ | `fachmodule/familie/geburt.json` `varianten[5]` | § 20 Abs. 1: Zuschuss des Arbeitgebers für die Zeit der Schutzfristen | ✅ |
| 9 | arbeitgeberzuschuss_mutterschaftsgeld_bund: Bedingung „Die Mutter ist angestellt (mutter.beschaeftigt == true)“ | `fachmodule/familie/geburt.json` `varianten[5].regel` | § 20 Abs. 1: Frauen in einem Beschäftigungsverhältnis | ✅ |

Ergebnis: ✅ stimmt mit dem Wortlaut überein · ❌ weicht ab (Korrektur nötig) · ⚠️ unklar oder nur teilweise belegt

## Abweichungen und Folgeaktionen

- Die Frist „Vor Beginn der Schutzfrist beantragen“ ist eine Empfehlung; gesetzlich gibt es keine Antragsfrist. Prüfen, ob die Frist als „empfohlen“ statt „spätestens“ geführt werden sollte (Folgeaktion, keine Auswirkung auf Ja/Nein).
