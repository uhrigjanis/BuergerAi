# Prüfprotokoll: estg_66

- Quelle: § 66 EStG – Höhe des Kindergeldes, https://www.gesetze-im-internet.de/estg/__66.html
- Fassung/Stand: recherchiert am 29.10.2026 über Websuche (gesetze-im-internet.de aus Entwicklungsumgebung und CI nicht erreichbar) · Stand „zuletzt geändert durch …“ beim lokalen Abgleich eintragen
- Geprüft von: Claude (Recherche) · Abnahme: <Name, Datum>
- Prüfstatus vorher: teilweise (2026-10-24, Claude (Websuche))
- Gerüst erzeugt am 2026-10-29 mit `./bai quellen --protokoll estg_66`

> Bisherige Notiz: 259 € je Kind ab 1.1.2026 (2025: 255 €) über mehrere Quellen bestätigt. Sechs-Monats-Frist für rückwirkende Zahlung noch im Volltext prüfen.
>
> **Einschränkung:** Zitate aus Suchergebnissen (Gesetzesspiegel wie dejure.org, buzer.de, lxgesetze.de, rewis.io, Kommentare). Vor der Abnahme lokal prüfen: `./bai quellen --abgleich estg_66 --in-protokoll` – der Abgleich vergleicht jedes Zitat mit dem amtlichen XML von gesetze-im-internet.de.

## Verwendungen in der Wissensbasis (3)

| # | Verwendung in der Wissensbasis | Fundstelle | Wortlaut der Quelle (Zitat, Absatz) | Ergebnis |
|---|---|---|---|---|
| 1 | kindergeld: Betrag „255 € im Monat je Kind“ | `fachmodule/familie/geburt.json` `leistungen[8].betraege[0]` | Frühere Fassung (2025): 255 Euro | ⚠️ nur in der Fassung für 2025 belegt; Gültigkeitszeitraum 1.1.–31.12.2025 ist in den Daten gepflegt |
| 2 | kindergeld: Betrag „259 € im Monat je Kind“ | `fachmodule/familie/geburt.json` `leistungen[8].betraege[1]` | Abs. 1: „Das Kindergeld beträgt monatlich für jedes Kind 259 Euro.“ | ✅ |
| 3 | kindergeld_bund: Variante „Leistung kindergeld in Gebiet DE“ | `fachmodule/familie/geburt.json` `varianten[8]` | Höhe des Kindergeldes | ✅ |

Ergebnis: ✅ stimmt mit dem Wortlaut überein · ❌ weicht ab (Korrektur nötig) · ⚠️ unklar oder nur teilweise belegt

## Abweichungen und Folgeaktionen

- Die Sechs-Monats-Rückwirkung war § 66 zugeordnet; sie steht seit 2019 in § 70 Abs. 1 Satz 2 EStG (vorher § 66 Abs. 3). Korrigiert: neue Quelle [estg_70](estg_70.md), Titel von estg_66 angepasst, Test `test_kindergeld_rueckwirkung_zitiert_paragraf_70`.
