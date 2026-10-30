# Prüfprotokoll: bkgg_6a

- Quelle: § 6a BKGG – Kinderzuschlag, https://www.gesetze-im-internet.de/bkgg_1996/__6a.html
- Fassung/Stand: recherchiert am 29.10.2026 über Websuche (gesetze-im-internet.de aus Entwicklungsumgebung und CI nicht erreichbar) · Stand „zuletzt geändert durch …“ beim lokalen Abgleich eintragen
- Geprüft von: Claude (Recherche) · Abnahme: <Name, Datum>
- Prüfstatus vorher: teilweise (2026-10-24, Claude (Websuche))
- Gerüst erzeugt am 2026-10-29 mit `./bai quellen --protokoll bkgg_6a`

> Bisherige Notiz: Höchstbetrag 297 € (2026), Mindesteinkommen 900 € (Paare) / 600 € (Alleinerziehende) brutto: Mehrheit der Quellen; eine Quelle nennt abweichende Werte. Gegen Volltext prüfen.
>
> **Einschränkung:** Zitate aus Suchergebnissen (Gesetzesspiegel wie dejure.org, buzer.de, lxgesetze.de, rewis.io, Kommentare). Vor der Abnahme lokal prüfen: `./bai quellen --abgleich bkgg_6a --in-protokoll` – der Abgleich vergleicht jedes Zitat mit dem amtlichen XML von gesetze-im-internet.de.

## Verwendungen in der Wissensbasis (6)

| # | Verwendung in der Wissensbasis | Fundstelle | Wortlaut der Quelle (Zitat, Absatz) | Ergebnis |
|---|---|---|---|---|
| 1 | kinderzuschlag: Betrag „bis zu 297 € im Monat je Kind“ | `fachmodule/familie/geburt.json` `leistungen[9].betraege[0]` | Abs. 2: Höhe richtet sich nach dem Existenzminimumbericht zuzüglich Sofortzuschlag; der Betrag (297 € seit 1.1.2025, 2026 unverändert) steht nicht als Zahl im Gesetz | ⚠️ nur über Sekundärquellen belegt – mit KiZ-Lotse/Familienkasse gegenprüfen (#57/#58) |
| 2 | kinderzuschlag_bund: Variante „Leistung kinderzuschlag in Gebiet DE“ | `fachmodule/familie/geburt.json` `varianten[9]` | § 6a Abs. 1: Anspruch für in ihrem Haushalt lebende unverheiratete Kinder unter 25 Jahren | ✅ |
| 3 | kinderzuschlag_bund: Bedingung „Das Kind lebt im eigenen Haushalt (kind_lebt_im_haushalt == true)“ | `fachmodule/familie/geburt.json` `varianten[9].regel.alle[0].eine[0].regel` | wie Nr. 2 | ✅ |
| 4 | kinderzuschlag_bund: Bedingung „Mindestens ein Kind lebt im Haushalt (kinder_im_haushalt >= 1)“ | `fachmodule/familie/geburt.json` `varianten[9].regel.alle[0].eine[1]` | wie Nr. 2 | ✅ |
| 5 | kinderzuschlag_bund: Bedingung „Mindesteinkommen für Elternpaare: 900 € brutto im Monat (brutto_haushalt_monat >= 900)“ | `fachmodule/familie/geburt.json` `varianten[9].regel.alle[1].eine[0].alle[1]` | Abs. 1 Nr. 2: Mindesteinkommen 900 Euro für Elternpaare | ✅ inhaltlich übereinstimmend in allen Quellen |
| 6 | kinderzuschlag_bund: Bedingung „Mindesteinkommen für Alleinerziehende: 600 € brutto im Monat (brutto_haushalt_monat >= 600)“ | `fachmodule/familie/geburt.json` `varianten[9].regel.alle[1].eine[1].alle[1]` | Abs. 1 Nr. 2: 600 Euro für Alleinerziehende | ✅ |

Ergebnis: ✅ stimmt mit dem Wortlaut überein · ❌ weicht ab (Korrektur nötig) · ⚠️ unklar oder nur teilweise belegt

## Abweichungen und Folgeaktionen

- Die frühere Notiz „eine Quelle weicht ab“ bestätigt sich nicht: alle aktuellen Quellen nennen 900/600 € und 297 €. Den Betrag beim nächsten Wechsel (Existenzminimumbericht) prüfen.
