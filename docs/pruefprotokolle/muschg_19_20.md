# Prüfprotokoll: muschg_19_20

- Quelle: §§ 19, 20 MuSchG – Mutterschaftsgeld, Arbeitgeberzuschuss, https://www.gesetze-im-internet.de/muschg_2018/__19.html
- Fassung/Stand: amtliches XML von gesetze-im-internet.de, abgerufen am 30.10.2026 · zuletzt geändert durch Art. 13 G v. 22.12.2025 I Nr. 371 (Recherche vorher am 29.10.2026 per Websuche)
- Geprüft von: Claude (Recherche 29.10.2026, Abgleich mit dem amtlichen XML 30.10.2026) · Abnahme: <Name, Datum>
- Prüfstatus vorher: teilweise (2026-10-24, Claude (Websuche))
- Gerüst erzeugt am 2026-10-29 mit `./bai quellen --protokoll muschg_19_20`

> Bisherige Notiz: Privat oder familienversicherte Arbeitnehmerinnen: einmalig bis 210 € vom Bundesamt für Soziale Sicherung; Arbeitgeber zahlt Zuschuss. Schutzfrist i. d. R. 6 Wochen vor, 8 Wochen nach der Geburt.
>
> **Abgleich:** Die Zitate stammen aus der Websuche vom 29.10.2026 und wurden am 30.10.2026 mit `./bai quellen --abgleich muschg_19_20` gegen das amtliche XML von gesetze-im-internet.de geprüft (Ergebnis unten unter „Automatischer Abgleich“).

## Verwendungen in der Wissensbasis (9)

| # | Verwendung in der Wissensbasis | Fundstelle | Wortlaut der Quelle (Zitat, Absatz) | Ergebnis |
|---|---|---|---|---|
| 1 | mutterschaftsgeld_bas: Betrag „einmalig höchstens 210 € für die gesamte Schutzfrist“ | `fachmodule/familie/geburt.json` `leistungen[4].betraege[0]` | § 19 Abs. 2 Satz 1: Mutterschaftsgeld zu Lasten des Bundes, „jedoch insgesamt höchstens 210 Euro“; Satz 2: „Das Mutterschaftsgeld wird dieser Frau auf Antrag vom Bundesamt für Soziale Sicherung gezahlt.“ | ✅ Zitat am 30.10.2026 berichtigt (Wortstellung), Betrag stimmt |
| 2 | arbeitgeberzuschuss_mutterschaftsgeld: Betrag „Unterschied zwischen 13 € je Kalendertag und dem durchschnittlichen Nettoarbeitsentgelt“ | `fachmodule/familie/geburt.json` `leistungen[5].betraege[0]` | § 20 Abs. 1: Zuschuss in Höhe des „Unterschiedsbetrag zwischen 13 Euro und dem um die gesetzlichen Abzüge verminderten durchschnittlichen kalendertäglichen Arbeitsentgelt“ | ✅ |
| 3 | mutterschaftsgeld_krankenkasse_bund: Frist „Vor Beginn der Schutzfrist (6 Wochen vor dem Termin) beantragen“ | `fachmodule/familie/geburt.json` `varianten[3].verfahren.fristen[1]` | Das Gesetz nennt keine Antragsfrist | ⚠️ Empfehlung, keine gesetzliche Frist – Text sagt „beantragen“, Art „spaetestens“ prüfen |
| 4 | mutterschaftsgeld_bas_bund: Variante „Leistung mutterschaftsgeld_bas in Gebiet DE“ | `fachmodule/familie/geburt.json` `varianten[4]` | § 19 Abs. 2: Frauen, die nicht Mitglied einer gesetzlichen Krankenkasse sind | ✅ |
| 5 | mutterschaftsgeld_bas_bund: Bedingung „Die Mutter ist angestellt (mutter.beschaeftigt == true)“ | `fachmodule/familie/geburt.json` `varianten[4].regel.alle[0]` | § 19 Abs. 2 Satz 1: Mutterschaftsgeld „in entsprechender Anwendung der Vorschriften des Fünften Buches Sozialgesetzbuch über das Mutterschaftsgeld“, also wie § 24i SGB V als Ersatz für Arbeitsentgelt, das wegen der Schutzfristen entfällt; Satz 3: „Endet das Beschäftigungsverhältnis nach Maßgabe von § 17 Absatz 2 durch eine Kündigung“ | ✅ im Ergebnis; die Beschäftigung steht nicht wörtlich in § 19 (die frühere Umschreibung „bei Beginn der Schutzfrist in einem Arbeitsverhältnis“ stammte aus § 13 Abs. 2 MuSchG a. F.). Sonderfall Kündigung (Satz 3) nicht modelliert |
| 6 | mutterschaftsgeld_bas_bund: Bedingung „Die Mutter ist privat oder familienversichert (kein eigenes Kassenmitglied) (mutter.krankenversicherung in ["privat", "gesetzlich_familienversichert"])“ | `fachmodule/familie/geburt.json` `varianten[4].regel.alle[1]` | § 19 Abs. 2: „nicht Mitglied einer gesetzlichen Krankenkasse“ – privat oder familienversichert | ✅ |
| 7 | mutterschaftsgeld_bas_bund: Frist „Vor Beginn der Schutzfrist (6 Wochen vor dem Termin) beantragen“ | `fachmodule/familie/geburt.json` `varianten[4].verfahren.fristen[0]` | wie Nr. 3 | ⚠️ wie Nr. 3 |
| 8 | arbeitgeberzuschuss_mutterschaftsgeld_bund: Variante „Leistung arbeitgeberzuschuss_mutterschaftsgeld in Gebiet DE“ | `fachmodule/familie/geburt.json` `varianten[5]` | § 20 Abs. 1: Zuschuss des Arbeitgebers für die Zeit der Schutzfristen | ✅ |
| 9 | arbeitgeberzuschuss_mutterschaftsgeld_bund: Bedingung „Die Mutter ist angestellt (mutter.beschaeftigt == true)“ | `fachmodule/familie/geburt.json` `varianten[5].regel` | § 20 Abs. 1 Satz 1: „Eine Frau erhält während ihres bestehenden Beschäftigungsverhältnisses für die Zeit der Schutzfristen“ | ✅ |

Ergebnis: ✅ stimmt mit dem Wortlaut überein · ❌ weicht ab (Korrektur nötig) · ⚠️ unklar oder nur teilweise belegt

## Abweichungen und Folgeaktionen

- **Abgleich 30.10.2026:** Das Zitat in Zeile 1 hatte die Wortstellung eines Gesetzesspiegels („höchstens jedoch insgesamt“); amtlich: „jedoch insgesamt höchstens 210 Euro“. Berichtigt, Daten unverändert.
- Zeile 5 stützte sich auf den Wortlaut des MuSchG vor 2018. Die Bedingung „angestellt“ bleibt richtig (entsprechende Anwendung von § 24i SGB V, Satz 3), die Fundstelle ist berichtigt.
- Hinweise des Abgleichs, kein Fehler: „13“ steht in § 20 Abs. 1 Satz 2 (der Abgleich prüft Zahlen nur in § 19 aus der URL; das Zitat in Zeile 2 wurde gefunden). „6 Wochen“ ist die Schutzfrist nach § 3 Abs. 1 MuSchG, nicht Inhalt von §§ 19, 20.
- Die Frist „Vor Beginn der Schutzfrist beantragen“ ist eine Empfehlung; gesetzlich gibt es keine Antragsfrist. Prüfen, ob die Frist als „empfohlen“ statt „spätestens“ geführt werden sollte (Folgeaktion, keine Auswirkung auf Ja/Nein).

## Automatischer Abgleich

Stand 30.10.2026 (`./bai quellen --abgleich muschg_19_20`): Zitate 7/7 · Zahlen 1/3 · Stand: Zuletzt geändert durch Art. 13 G v. 22.12.2025 I Nr. 371

Geprüfter Abschnitt: § 19 MuSchG 2018

- ⚠️ Zahl 13 nicht im Abschnitt gefunden (arbeitgeberzuschuss_mutterschaftsgeld: Unterschied zwischen 13 € je Kalendertag und dem durchschnittlichen Nettoarbeitsentgelt)
- ⚠️ Zahl 6 Wochen nicht im Abschnitt gefunden (mutterschaftsgeld_krankenkasse_bund: Vor Beginn der Schutzfrist (6 Wochen vor dem Termin) beantragen)
