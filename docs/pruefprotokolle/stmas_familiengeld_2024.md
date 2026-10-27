# Prüfprotokoll: stmas_familiengeld_2024

- Quelle: StMAS-Infoblatt Familiengeld/Krippengeld (Stand 14.11.2024), https://stmas.bayern.de/imperia/md/content/stmas/stmas_inet/241114_infoblatt_homepage.pdf
- Fassung/Stand: Infoblatt vom 14.11.2024, also vor dem Gesetzesbeschluss (GVBl. 2025 S. 570) · recherchiert am 27.10.2026
- Geprüft von: Claude (Recherche über Websuche) · Abnahme: <Name, Datum>
- Prüfstatus vorher: widerspruechlich (24.10.2026) → jetzt teilweise

> **Einschränkung:** stmas.bayern.de war nicht abrufbar. Inhalt laut Suchergebnissen und der bisherigen Notiz.

## Verwendungen in der Wissensbasis (2)

| # | Verwendung in der Wissensbasis | Fundstelle | Wortlaut der Quelle (Zitat, Absatz) | Ergebnis |
|---|---|---|---|---|
| 1 | zbfs_familiengeld: Zuständigkeit „Zentrum Bayern Familie und Soziales (ZBFS)“ | `laender/by/geburt.json` `zustaendigkeiten[1]` | Familiengeld wird vom ZBFS ausgezahlt; bestätigt durch die ZBFS-Seite „Bayerisches Familiengeld“ (zbfs.bayern.de/familienleistungen/familiengeld/) | ✅ |
| 2 | bayerisches_familiengeld_by: Variante (Bayern) | `laender/by/geburt.json` `varianten[2]` | Infoblatt: Familiengeld nur für Kinder, die vor dem 1.1.2025 geboren sind | ✅ deckt sich mit Art. 9a BayFamGG |

Ergebnis: ✅ stimmt mit dem Wortlaut überein · ❌ weicht ab (Korrektur nötig) · ⚠️ unklar oder nur teilweise belegt

## Abweichungen und Folgeaktionen

- Das Infoblatt stammt aus der Zeit vor dem Gesetz, sein Stichtag wurde aber so beschlossen. Es ist nicht mehr Grundlage der Regel: Bedingung und Betrag zitieren jetzt [bayfamgg_9a](bayfamgg_9a.md) und [bayfamgg_3](bayfamgg_3.md). Das Infoblatt bleibt als ergänzende Behördenquelle an der Variante.
- Die Quelle hat keinen Gültigkeitszeitraum. Das Datenmodell sieht für Quellen keinen vor (vgl. #4). Der Stand steht im Titel.
