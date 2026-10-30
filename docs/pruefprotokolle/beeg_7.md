# Prüfprotokoll: beeg_7

- Quelle: § 7 BEEG – Antragstellung (rückwirkend höchstens drei Lebensmonate), https://www.gesetze-im-internet.de/beeg/__7.html
- Fassung/Stand: recherchiert am 29.10.2026 über Websuche (gesetze-im-internet.de aus Entwicklungsumgebung und CI nicht erreichbar) · Stand „zuletzt geändert durch …“ beim lokalen Abgleich eintragen
- Geprüft von: Claude (Recherche) · Abnahme: <Name, Datum>
- Prüfstatus vorher: teilweise (2026-10-24, Claude (Websuche))
- Gerüst erzeugt am 2026-10-29 mit `./bai quellen --protokoll beeg_7`

> Bisherige Notiz: Rückwirkende Zahlung nur für die letzten drei Lebensmonate vor dem Antragsmonat (Leistungsbeschreibung Bayern/Berlin im FIM-Portal).
>
> **Einschränkung:** Zitate aus Suchergebnissen (Gesetzesspiegel wie dejure.org, buzer.de, lxgesetze.de, rewis.io, Kommentare). Vor der Abnahme lokal prüfen: `./bai quellen --abgleich beeg_7 --in-protokoll` – der Abgleich vergleicht jedes Zitat mit dem amtlichen XML von gesetze-im-internet.de.

## Verwendungen in der Wissensbasis (18)

| # | Verwendung in der Wissensbasis | Fundstelle | Wortlaut der Quelle (Zitat, Absatz) | Ergebnis |
|---|---|---|---|---|
| 1 | elterngeld_bund: Variante „Leistung elterngeld in Gebiet DE“ – gilt per erbt_von auch für 57 weitere Varianten (elterngeld_bb, elterngeld_be, elterngeld_bw, …) | `fachmodule/familie/geburt.json` `varianten[7]` | Abs. 1 Satz 1: Elterngeld ist schriftlich zu beantragen | ✅ |
| 2 | elterngeld_bund: Frist „Bis zum Ende des 3. Lebensmonats beantragen – rückwirkend wird höchstens für 3 Lebensmonate vor dem Antragsmonat gezahlt“ | `fachmodule/familie/geburt.json` `varianten[7].verfahren.fristen[0]` | Abs. 1 Satz 2: „Es wird rückwirkend nur für die letzten drei Lebensmonate vor Beginn des Lebensmonats geleistet, in dem der Antrag auf Elterngeld eingegangen ist.“ | ✅ „bis Ende des 3. Lebensmonats“ ist die daraus folgende Empfehlung |
| 3 | elterngeld_bb: Variante „Leistung elterngeld in Gebiet 12“ | `laender/bb/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 4 | elterngeld_be: Variante „Leistung elterngeld in Gebiet 11“ | `laender/be/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 5 | elterngeld_bw: Variante „Leistung elterngeld in Gebiet 08“ | `laender/bw/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 6 | elterngeld_by: Variante „Leistung elterngeld in Gebiet 09“ | `laender/by/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 7 | elterngeld_hb: Variante „Leistung elterngeld in Gebiet 04“ | `laender/hb/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 8 | elterngeld_he: Variante „Leistung elterngeld in Gebiet 06“ – gilt per erbt_von auch für 26 weitere Varianten (elterngeld_06411, elterngeld_06412, elterngeld_06413, …) | `laender/he/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 9 | elterngeld_hh: Variante „Leistung elterngeld in Gebiet 02“ | `laender/hh/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 10 | elterngeld_mv: Variante „Leistung elterngeld in Gebiet 13“ | `laender/mv/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 11 | elterngeld_ni: Variante „Leistung elterngeld in Gebiet 03“ | `laender/ni/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 12 | elterngeld_nw: Variante „Leistung elterngeld in Gebiet 05“ | `laender/nw/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 13 | elterngeld_rp: Variante „Leistung elterngeld in Gebiet 07“ | `laender/rp/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 14 | elterngeld_sh: Variante „Leistung elterngeld in Gebiet 01“ – gilt per erbt_von auch für 15 weitere Varianten (elterngeld_01001, elterngeld_01002, elterngeld_01003, …) | `laender/sh/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 15 | elterngeld_sl: Variante „Leistung elterngeld in Gebiet 10“ | `laender/sl/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 16 | elterngeld_sn: Variante „Leistung elterngeld in Gebiet 14“ | `laender/sn/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 17 | elterngeld_st: Variante „Leistung elterngeld in Gebiet 15“ | `laender/st/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |
| 18 | elterngeld_th: Variante „Leistung elterngeld in Gebiet 16“ | `laender/th/geburt.json` `varianten[0]` | Landes-/Ortsvariante übernimmt Regel und Quellen der Bundesvariante (erbt_von) | ✅ |

Ergebnis: ✅ stimmt mit dem Wortlaut überein · ❌ weicht ab (Korrektur nötig) · ⚠️ unklar oder nur teilweise belegt

## Abweichungen und Folgeaktionen

- Keine.
