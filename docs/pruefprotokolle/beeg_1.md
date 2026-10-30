# Prüfprotokoll: beeg_1

- Quelle: § 1 BEEG – Berechtigte (Elterngeld), https://www.gesetze-im-internet.de/beeg/__1.html
- Fassung/Stand: amtliches XML von gesetze-im-internet.de, abgerufen am 30.10.2026 · zuletzt geändert durch Art. 19 Abs. 2 G v. 22.12.2025 I Nr. 370 (Recherche vorher am 29.10.2026 per Websuche)
- Geprüft von: Claude (Recherche 29.10.2026, Abgleich mit dem amtlichen XML 30.10.2026) · Abnahme: <Name, Datum>
- Prüfstatus vorher: teilweise (2026-10-24, Claude (Websuche))
- Gerüst erzeugt am 2026-10-29 mit `./bai quellen --protokoll beeg_1`

> Bisherige Notiz: Einkommensgrenze 175.000 € (Geburten ab 1.4.2025) bzw. 200.000 € (1.4.2024–31.3.2025) über mehrere Quellen bestätigt. 32-Stunden-Grenze (§ 1 Abs. 6) und Aufenthaltstitel-Regeln (§ 1 Abs. 7) noch im Volltext prüfen.
>
> **Abgleich:** Die Zitate stammen aus der Websuche vom 29.10.2026 und wurden am 30.10.2026 mit `./bai quellen --abgleich beeg_1` gegen das amtliche XML von gesetze-im-internet.de geprüft (Ergebnis unten unter „Automatischer Abgleich“).

## Verwendungen in der Wissensbasis (26)

| # | Verwendung in der Wissensbasis | Fundstelle | Wortlaut der Quelle (Zitat, Absatz) | Ergebnis |
|---|---|---|---|---|
| 1 | elterngeld_bund: Variante „Leistung elterngeld in Gebiet DE“ – gilt per erbt_von auch für 57 weitere Varianten (elterngeld_bb, elterngeld_be, elterngeld_bw, …) | `fachmodule/familie/geburt.json` `varianten[7]` | Abs. 1: „Anspruch auf Elterngeld hat, wer“ – Quelle der Leistung insgesamt | ✅ |
| 2 | elterngeld_bund: Bedingung „Wohnsitz in Deutschland (wohnsitz_in_deutschland == true)“ | `fachmodule/familie/geburt.json` `varianten[7].regel.alle[0]` | Abs. 1 Nr. 1: „einen Wohnsitz oder seinen gewöhnlichen Aufenthalt in Deutschland hat“ | ✅ Fakt wird aus dem Wohnort abgeleitet |
| 3 | elterngeld_bund: Bedingung „Das Kind lebt im eigenen Haushalt (kind_lebt_im_haushalt == true)“ | `fachmodule/familie/geburt.json` `varianten[7].regel.alle[1]` | Abs. 1 Nr. 2: „mit seinem Kind in einem Haushalt lebt“ | ✅ |
| 4 | elterngeld_bund: Bedingung „Betreut und erzieht das Kind selbst (person.betreut_kind_selbst == true)“ | `fachmodule/familie/geburt.json` `varianten[7].regel.alle[2]` | Abs. 1 Nr. 3: „dieses Kind selbst betreut und erzieht“ | ✅ |
| 5 | elterngeld_bund: Bedingung „Arbeitet höchstens 32 Stunden pro Woche (person.erwerbsstunden_nach_geburt <= 32)“ | `fachmodule/familie/geburt.json` `varianten[7].regel.alle[3]` | Abs. 1 Nr. 4: „keine oder keine volle Erwerbstätigkeit ausübt“; Abs. 6 Nr. 1: „ihre Arbeitszeit 32 Wochenstunden im Durchschnitt des Lebensmonats nicht übersteigt“ | ✅ |
| 6 | elterngeld_bund: Bedingung „Deutsche oder EU/EWR/Schweizer Staatsangehörigkeit (person.staatsangehoerigkeit in ["deutsch", "eu_ewr_ch"])“ | `fachmodule/familie/geburt.json` `varianten[7].regel.alle[4].eine[0]` | Abs. 7 gilt nur für nicht freizügigkeitsberechtigte Personen; Deutsche und EU/EWR/Schweiz sind nicht betroffen | ✅ |
| 7 | elterngeld_bund: Bedingung „Prüfung nötig: Bei anderer Staatsangehörigkeit hängt der Anspruch vom Aufenthaltstitel ab (§ 1 Abs. 7 BEEG) – bitte bei der Elterngeldstelle klären.“ | `fachmodule/familie/geburt.json` `varianten[7].regel.alle[4].eine[1]` | Abs. 7 Satz 1: „Ein nicht freizügigkeitsberechtigter Ausländer oder eine nicht freizügigkeitsberechtigte Ausländerin ist nur anspruchsberechtigt, wenn diese Person“ (Niederlassungserlaubnis, Blaue Karte EU u. a.) | ✅ bewusst „Prüfung nötig“ |
| 8 | elterngeld_bund: Bedingung „Geburt ab dem 1.4.2025 (geburtsdatum_oder_termin >= "2025-04-01")“ | `fachmodule/familie/geburt.json` `varianten[7].regel.alle[5].eine[0].alle[0]` | Ab 1.4.2025 gilt Abs. 8 unmittelbar; die 200.000-€-Übergangsregel endet mit Geburten bis 31.3.2025 (§ 28 Abs. 5) | ✅ |
| 9 | elterngeld_bund: Bedingung „Zu versteuerndes Einkommen höchstens 175.000 € (zve_eltern <= 175000)“ | `fachmodule/familie/geburt.json` `varianten[7].regel.alle[5].eine[0].alle[1]` | Abs. 8 Satz 1: „Ein Anspruch entfällt, wenn die berechtigte Person im letzten abgeschlossenen Veranlagungszeitraum vor der Geburt des Kindes ein zu versteuerndes Einkommen nach § 2 Absatz 5 des Einkommensteuergesetzes in Höhe von mehr als 175 000 Euro erzielt hat.“ Satz 2: „wenn die Summe des zu versteuernden Einkommens beider Personen mehr als 175 000 Euro beträgt“ | ✅ gilt einheitlich für Paare und Alleinerziehende |
| 10 | elterngeld_bund: Bedingung „Geburt vor dem 1.4.2024 (geburtsdatum_oder_termin < "2024-04-01")“ | `fachmodule/familie/geburt.json` `varianten[7].regel.alle[5].eine[2].alle[0]` | Für Geburten vor dem 1.4.2024 galten frühere Grenzen (§ 28, ältere Fassungen) | ⚠️ bewusst „Prüfung nötig“, nicht im Detail geprüft |
| 11 | elterngeld_bb: Variante „Leistung elterngeld in Gebiet 12“ | `laender/bb/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 12 | elterngeld_be: Variante „Leistung elterngeld in Gebiet 11“ | `laender/be/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 13 | elterngeld_bw: Variante „Leistung elterngeld in Gebiet 08“ | `laender/bw/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 14 | elterngeld_by: Variante „Leistung elterngeld in Gebiet 09“ | `laender/by/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 15 | elterngeld_hb: Variante „Leistung elterngeld in Gebiet 04“ | `laender/hb/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 16 | elterngeld_he: Variante „Leistung elterngeld in Gebiet 06“ – gilt per erbt_von auch für 26 weitere Varianten (elterngeld_06411, elterngeld_06412, elterngeld_06413, …) | `laender/he/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 17 | elterngeld_hh: Variante „Leistung elterngeld in Gebiet 02“ | `laender/hh/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 18 | elterngeld_mv: Variante „Leistung elterngeld in Gebiet 13“ | `laender/mv/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 19 | elterngeld_ni: Variante „Leistung elterngeld in Gebiet 03“ | `laender/ni/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 20 | elterngeld_nw: Variante „Leistung elterngeld in Gebiet 05“ | `laender/nw/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 21 | elterngeld_rp: Variante „Leistung elterngeld in Gebiet 07“ | `laender/rp/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 22 | elterngeld_sh: Variante „Leistung elterngeld in Gebiet 01“ – gilt per erbt_von auch für 15 weitere Varianten (elterngeld_01001, elterngeld_01002, elterngeld_01003, …) | `laender/sh/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 23 | elterngeld_sl: Variante „Leistung elterngeld in Gebiet 10“ | `laender/sl/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 24 | elterngeld_sn: Variante „Leistung elterngeld in Gebiet 14“ | `laender/sn/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 25 | elterngeld_st: Variante „Leistung elterngeld in Gebiet 15“ | `laender/st/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 26 | elterngeld_th: Variante „Leistung elterngeld in Gebiet 16“ | `laender/th/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |

Ergebnis: ✅ stimmt mit dem Wortlaut überein · ❌ weicht ab (Korrektur nötig) · ⚠️ unklar oder nur teilweise belegt

## Abweichungen und Folgeaktionen

- Die Bedingungen für Geburten vom 1.4.2024 bis 31.3.2025 (Grenze 200.000 €) zitierten § 1 BEEG; die Regel steht in § 28 Abs. 5 BEEG. Korrigiert: neue Quelle [beeg_28](beeg_28.md), Test `test_grenze_200000_zitiert_uebergangsvorschrift`.
- Geprüft und **nicht** übernommen: eine eigene Grenze von 150.000 € für Alleinerziehende (Geburten 1.4.2024–31.3.2025). Sie stand nur im Referentenentwurf; beschlossen sind 200.000 € für alle (Haufe, Tillmanns/Mutschler). Absicherung: `test_keine_eigene_grenze_fuer_alleinerziehende_2024`.
- **Abgleich 30.10.2026:** alle 9 Zitate wörtlich im amtlichen Text. Die Hinweise „01.04.2025“ und „01.04.2024 nicht im Abschnitt“ sind erwartet: Die Stichtage stehen in der Übergangsvorschrift § 28 BEEG, die diese Bedingungen bereits zusätzlich zitieren (beeg_28).
- § 1 Abs. 6 Nr. 3 (Tagespflegepersonen, ohne Begrenzung auf fünf Kinder seit 1.5.2025) ist nicht modelliert; betrifft die Pilotregion nur am Rand.

## Automatischer Abgleich

Stand 30.10.2026 (`./bai quellen --abgleich beeg_1`): Zitate 9/9 · Zahlen 2/4 · Stand: zuletzt geändert durch Art. 19 Abs. 2 G v. 22.12.2025 I Nr. 370

Geprüfter Abschnitt: § 1 BEEG

- ⚠️ Zahl 01.04.2025 nicht im Abschnitt gefunden (elterngeld_bund: Geburt ab dem 1.4.2025)
- ⚠️ Zahl 01.04.2024 nicht im Abschnitt gefunden (elterngeld_bund: Geburt vor dem 1.4.2024)
