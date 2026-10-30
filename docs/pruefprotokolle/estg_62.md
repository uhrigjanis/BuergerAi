# Prüfprotokoll: estg_62

- Quelle: §§ 62, 63 EStG – Anspruchsberechtigte und Kinder (Kindergeld), https://www.gesetze-im-internet.de/estg/__62.html
- Fassung/Stand: recherchiert am 29.10.2026 über Websuche (gesetze-im-internet.de aus Entwicklungsumgebung und CI nicht erreichbar) · Stand „zuletzt geändert durch …“ beim lokalen Abgleich eintragen
- Geprüft von: Claude (Recherche) · Abnahme: <Name, Datum>
- Prüfstatus vorher: ungeprueft
- Gerüst erzeugt am 2026-10-29 mit `./bai quellen --protokoll estg_62`

> Bisherige Notiz: § 62 Abs. 2: Nicht freizügigkeitsberechtigte Ausländer nur mit bestimmten Aufenthaltstiteln.
>
> **Einschränkung:** Zitate aus Suchergebnissen (Gesetzesspiegel wie dejure.org, buzer.de, lxgesetze.de, rewis.io, Kommentare). Vor der Abnahme lokal prüfen: `./bai quellen --abgleich estg_62 --in-protokoll` – der Abgleich vergleicht jedes Zitat mit dem amtlichen XML von gesetze-im-internet.de.

## Verwendungen in der Wissensbasis (6)

| # | Verwendung in der Wissensbasis | Fundstelle | Wortlaut der Quelle (Zitat, Absatz) | Ergebnis |
|---|---|---|---|---|
| 1 | kindergeld_bund: Variante „Leistung kindergeld in Gebiet DE“ | `fachmodule/familie/geburt.json` `varianten[8]` | Abs. 1: „Für Kinder im Sinne des § 63 hat Anspruch auf Kindergeld nach diesem Gesetz, wer“ | ✅ |
| 2 | kindergeld_bund: Bedingung „Wohnsitz in Deutschland (wohnsitz_in_deutschland == true)“ | `fachmodule/familie/geburt.json` `varianten[8].regel.alle[0]` | Abs. 1 Satz 1 Nr. 1: „im Inland einen Wohnsitz oder seinen gewöhnlichen Aufenthalt hat“ | ⚠️ Nr. 2 (unbeschränkt steuerpflichtig ohne Wohnsitz, z. B. Grenzpendler) nicht modelliert |
| 3 | kindergeld_bund: Bedingung „Das Kind lebt im eigenen Haushalt (kind_lebt_im_haushalt == true)“ | `fachmodule/familie/geburt.json` `varianten[8].regel.alle[1]` | Steht nicht in § 62. Haushaltsaufnahme entscheidet nach § 64 Abs. 2 EStG, welcher Berechtigte das Kindergeld erhält | ⚠️ im Ergebnis für die Geburt passend, Quelle sollte § 64 nennen |
| 4 | kindergeld_bund: Bedingung „Die Mutter hat die deutsche oder eine EU/EWR/Schweizer Staatsangehörigkeit (mutter.staatsangehoerigkeit in ["deutsch", "eu_ewr_ch"])“ | `fachmodule/familie/geburt.json` `varianten[8].regel.alle[2].eine[0]` | Abs. 2 gilt nur für nicht freizügigkeitsberechtigte Ausländer | ✅ |
| 5 | kindergeld_bund: Bedingung „Der andere Elternteil hat die deutsche oder eine EU/EWR/Schweizer Staatsangehörigkeit (partner.staatsangehoerigkeit in ["deutsch", "eu_ewr_ch"])“ | `fachmodule/familie/geburt.json` `varianten[8].regel.alle[2].eine[1].alle[1]` | wie Nr. 4 | ✅ |
| 6 | kindergeld_bund: Bedingung „Prüfung nötig: Bei anderer Staatsangehörigkeit hängt der Anspruch vom Aufenthaltstitel ab (§ 62 Abs. 2 EStG) – bitte bei der Familienkasse klären.“ | `fachmodule/familie/geburt.json` `varianten[8].regel.alle[2].eine[2]` | Abs. 2: „Ein nicht freizügigkeitsberechtigter Ausländer erhält Kindergeld nur, wenn er“ (Niederlassungserlaubnis, bestimmte Aufenthaltserlaubnisse) | ✅ bewusst „Prüfung nötig“ |

Ergebnis: ✅ stimmt mit dem Wortlaut überein · ❌ weicht ab (Korrektur nötig) · ⚠️ unklar oder nur teilweise belegt

## Abweichungen und Folgeaktionen

- Bedingung „Kind lebt im Haushalt“ ist im Ergebnis richtig (wer das Kind im Haushalt hat, erhält das Kindergeld, § 64 Abs. 2), steht aber nicht in § 62. Folgeaktion: Quelle § 64 EStG ergänzen (#57 oder eigenes Issue).
- Kindergeld für Grenzpendler ohne Wohnsitz in Deutschland (Abs. 1 Nr. 2) ist nicht abgebildet; außerhalb der Pilotregion-Fälle.
