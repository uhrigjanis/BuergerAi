# Prüfprotokoll: bayfamgg_9a

- Quelle: Art. 9a BayFamGG – Übergangsvorschriften, https://www.gesetze-bayern.de/Content/Document/BayFamGG-9a
- Fassung/Stand: eingefügt durch Gesetz zur Änderung des Bayerischen Familiengeldgesetzes und weiterer Rechtsvorschriften, GVBl. 2025 S. 570 (Nr. 22, ausgegeben am 28.11.2025), [PDF](https://www.verkuendung-bayern.de/files/gvbl/2025/22/gvbl-2025-22.pdf) · recherchiert am 27.10.2026
- Geprüft von: Claude (Recherche über Websuche) · Abnahme: <Name, Datum>
- Prüfstatus: teilweise (neu angelegt in #54)

> **Einschränkung:** gesetze-bayern.de und verkuendung-bayern.de waren aus der Entwicklungsumgebung nicht abrufbar. Die Zitate stammen aus Suchergebnissen, die beide Seiten wörtlich wiedergeben. Für `verifiziert` den Wortlaut im GVBl.-PDF nachsehen.

## Verwendungen in der Wissensbasis (4)

| # | Verwendung in der Wissensbasis | Fundstelle | Wortlaut der Quelle (Zitat, Absatz) | Ergebnis |
|---|---|---|---|---|
| 1 | bayerisches_familiengeld: Betrag „250 € … – nur für vor dem 1.1.2025 geborene Kinder“ | `laender/by/geburt.json` `leistungen[0].betraege[0]` | Abs. 1: „Hinsichtlich vor dem 1. Januar 2025 geborener Kinder sind Art. 2 bis 8 in der am 30. Dezember 2025 geltenden Fassung weiter anzuwenden.“ | ✅ |
| 2 | bayerisches_familiengeld_by: Variante (Bayern) | `laender/by/geburt.json` `varianten[2]` | wie Nr. 1 und 3 | ✅ |
| 3 | bayerisches_familiengeld_by: Bedingung „Kind vor dem 1.1.2025 geboren“ (`geburtsdatum_oder_termin < 2025-01-01`) | `laender/by/geburt.json` `varianten[2].regel` | Abs. 2 Satz 1: „Anträge auf Familiengeld für Kinder, die ab dem 1. Januar 2025 geboren wurden, sind unbeachtlich.“ Satz 2: „Dies gilt auch, soweit kein gesonderter Antrag auf das Familiengeld gestellt wurde, sondern der Antrag auf Elterngeld gemäß Art. 6 Abs. 1 Satz 2 … in der am 30. Dezember 2025 geltenden Fassung als Antrag auf Familiengeld gilt.“ | ✅ „ab dem 1. Januar“ schließt den 1.1.2025 ein, also `<` richtig |
| 4 | 09: Landesabdeckung „Landesleistungen erfasst“ | `laender/by/geburt.json` `abdeckung[0]` | Familiengeld bleibt für vor 2025 geborene Kinder eine Landesleistung, siehe Abs. 1 | ✅ |

Ergebnis: ✅ stimmt mit dem Wortlaut überein · ❌ weicht ab (Korrektur nötig) · ⚠️ unklar oder nur teilweise belegt

## Abweichungen und Folgeaktionen

- **Widerspruch aufgelöst:** Der Stichtag 1.9.2026 mit Einkommensgrenze 100.000 € stammt aus dem Änderungsantrag Drs. 19/8839, der abgelehnt wurde (siehe [landtag_by_familiengeld](landtag_by_familiengeld.md)). Die Regel gab für Geburten vom 1.1.2025 bis 31.8.2026 bisher „Unklar“ aus, jetzt „Nein“. Abgesichert durch `tests/test_fachregeln.py::test_familiengeld` (Grenzfälle 31.12.2024, 1.1.2025, 31.8.2026, 1.9.2026) und die Szenarien `muenchen_familiengeld_2024` (Ja) und `muenchen_familiengeld_2026` (Nein).
- Inkrafttreten des Änderungsgesetzes nicht ermittelt. Die Formulierung „in der am 30. Dezember 2025 geltenden Fassung“ deutet auf den 31.12.2025 hin. Für das Ergebnis spielt das keine Rolle, weil Abs. 2 auf das Geburtsdatum abstellt.
- Eine Anfrage beim ZBFS ist nicht nötig, solange die Abnahme den Wortlaut im GVBl. bestätigt.
