# Prüfprotokoll: bkgg_6a

- Quelle: § 6a BKGG – Kinderzuschlag, https://www.gesetze-im-internet.de/bkgg_1996/__6a.html
- Fassung/Stand: amtliches XML von gesetze-im-internet.de, abgerufen am 30.10.2026 · zuletzt geändert durch Art. 10 G v. 16.4.2026 I Nr. 107 (Recherche vorher am 29.10.2026 per Websuche)
- Geprüft von: Claude (Recherche 29.10.2026, Abgleich mit dem amtlichen XML 30.10.2026) · Abnahme: <Name, Datum>
- Prüfstatus vorher: teilweise (2026-10-24, Claude (Websuche))
- Gerüst erzeugt am 2026-10-29 mit `./bai quellen --protokoll bkgg_6a`

> Bisherige Notiz: Höchstbetrag 297 € (2026), Mindesteinkommen 900 € (Paare) / 600 € (Alleinerziehende) brutto: Mehrheit der Quellen; eine Quelle nennt abweichende Werte. Gegen Volltext prüfen.
>
> **Abgleich:** Die Zitate stammen aus der Websuche vom 29.10.2026 und wurden am 30.10.2026 mit `./bai quellen --abgleich bkgg_6a` gegen das amtliche XML von gesetze-im-internet.de geprüft (Ergebnis unten unter „Automatischer Abgleich“).

## Verwendungen in der Wissensbasis (6)

| # | Verwendung in der Wissensbasis | Fundstelle | Wortlaut der Quelle (Zitat, Absatz) | Ergebnis |
|---|---|---|---|---|
| 1 | kinderzuschlag: Betrag „bis zu 297 € im Monat je Kind“ | `fachmodule/familie/geburt.json` `leistungen[9].betraege[0]` | Abs. 2: Höchstbetrag deckt mit dem Kindergeld ein Zwölftel des sächlichen Existenzminimums, „mindestens jedoch ein Betrag in Höhe des Vorjahres“, und „erhöht sich um einen Sofortzuschlag in Höhe von 25 Euro“; der Betrag steht nicht als Zahl im Gesetz. Familienportal des Bundes (abgerufen 30.10.2026): ab 1. Januar 2025 pro Kind bis zu 297 Euro im Monat, Sofortzuschlag enthalten | ⚠️ für 2025 amtlich belegt; für 2026 nennt das Familienportal keinen neuen Betrag. Wegen „mindestens … Vorjahr“ kann er nicht gesunken sein – eine Erhöhung 2026 mit dem KiZ-Lotsen ausschließen (#58) |
| 2 | kinderzuschlag_bund: Variante „Leistung kinderzuschlag in Gebiet DE“ | `fachmodule/familie/geburt.json` `varianten[9]` | § 6a Abs. 1: „für in ihrem Haushalt lebende unverheiratete oder nicht verpartnerte Kinder, die noch nicht das 25. Lebensjahr vollendet haben“ | ✅ |
| 3 | kinderzuschlag_bund: Bedingung „Das Kind lebt im eigenen Haushalt (kind_lebt_im_haushalt == true)“ | `fachmodule/familie/geburt.json` `varianten[9].regel.alle[0].eine[0].regel` | wie Nr. 2 | ✅ |
| 4 | kinderzuschlag_bund: Bedingung „Mindestens ein Kind lebt im Haushalt (kinder_im_haushalt >= 1)“ | `fachmodule/familie/geburt.json` `varianten[9].regel.alle[0].eine[1]` | wie Nr. 2 | ✅ |
| 5 | kinderzuschlag_bund: Bedingung „Mindesteinkommen für Elternpaare: 900 € brutto im Monat (brutto_haushalt_monat >= 900)“ | `fachmodule/familie/geburt.json` `varianten[9].regel.alle[1].eine[0].alle[1]` | Abs. 1 Nr. 2: Einkommen im Sinne des § 11 SGB II „in Höhe von mindestens 900 Euro oder, wenn sie alleinerziehend sind, in Höhe von mindestens 600 Euro“, ohne Wohngeld, Kindergeld und Kinderzuschlag; Absetzbeträge nach § 11b SGB II werden nicht abgezogen (also brutto) | ✅ Betrag; ❌ Hilfetext des Fakts nannte nur Erwerbseinkommen – berichtigt, siehe unten |
| 6 | kinderzuschlag_bund: Bedingung „Mindesteinkommen für Alleinerziehende: 600 € brutto im Monat (brutto_haushalt_monat >= 600)“ | `fachmodule/familie/geburt.json` `varianten[9].regel.alle[1].eine[1].alle[1]` | wie Nr. 5 | ✅ (Hilfetext wie Nr. 5 berichtigt) |

Ergebnis: ✅ stimmt mit dem Wortlaut überein · ❌ weicht ab (Korrektur nötig) · ⚠️ unklar oder nur teilweise belegt

## Abweichungen und Folgeaktionen

- **Abgleich 30.10.2026:** 900 und 600 im amtlichen Text gefunden; „297“ steht erwartungsgemäß nicht im Gesetz (Hinweis, kein Fehler).
- ❌ **Korrigiert:** Der Fakt `brutto_haushalt_monat` fragte nur nach „Erwerbseinkommen“. Zum Mindesteinkommen zählt jedes Einkommen nach § 11 SGB II, z. B. Arbeitslosengeld, Krankengeld und Elterngeld (§ 10 Abs. 5 BEEG nimmt § 6a BKGG vom 300-€-Freibetrag aus; nur bei Elterngeld aus früherer Erwerbstätigkeit bleiben bis 300 € frei), nicht aber Mutterschaftsgeld (§ 11a Abs. 1 Nr. 6 SGB II). Wer etwa Elterngeld bezieht und nur den Lohn angab, konnte fälschlich ein Nein erhalten. Hilfetext angepasst (ANF-KZ-02, `test_mindesteinkommen_kinderzuschlag_zaehlt_alle_einnahmen`). Die 300-€-Feinheit fehlt im Hilfetext bewusst: zu viel gezähltes Einkommen führt höchstens zu „Unklar“ (ANF-KZ-01), nie zu einem falschen Nein.
- Die frühere Notiz „eine Quelle weicht ab“ bestätigt sich nicht: alle aktuellen Quellen nennen 900/600 € und 297 €. Den Betrag beim nächsten Wechsel (Existenzminimumbericht) prüfen.

## Automatischer Abgleich

Stand 30.10.2026 (`./bai quellen --abgleich bkgg_6a`): Zitate 4/4 · Zahlen 2/3 · Stand: zuletzt geändert durch Art. 10 G v. 16.4.2026 I Nr. 107

Geprüfter Abschnitt: § 6a BKGG 1996

- ⚠️ Zahl 297 nicht im Abschnitt gefunden (kinderzuschlag: bis zu 297 € im Monat je Kind)
