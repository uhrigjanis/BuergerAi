# Datenquellen und Lizenzen

Übersicht über alle Quellen, aus denen Daten **automatisch** übernommen werden. Handgepflegte Angaben (Leistungen, Regeln, Zuständigkeiten) nennen ihre Quellen direkt in den Dateien unter `data/` (`./bai quellen`).

## Gebiete und Postleitzahlen (`data/generiert/gebiete.json`)

| Inhalt | Quelle | Lizenz / Nutzungsbedingungen | Stand im Repo |
|--------|--------|------------------------------|---------------|
| PLZ ↔ Gemeinde (AGS), Gemeindenamen | [OpenPLZ API Data](https://github.com/openpotato/openplzapi.data), `src/de/osm/streets.updated.csv` (Straßenverzeichnis aus OpenStreetMap) | [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), © OpenStreetMap-Mitwirkende. Namensnennung; abgeleitete **Datenbanken** müssen unter ODbL bleiben (Share-Alike). Die Datei `data/generiert/gebiete.json` ist eine solche abgeleitete Datenbank und steht daher unter ODbL. | Commit `c26389b` |
| Kreise (Name, Art) | Statistisches Bundesamt, [Kreisfreie Städte und Landkreise](https://www.destatis.de/DE/Themen/Laender-Regionen/Regionales/Gemeindeverzeichnis/Administrativ/04-kreise.html) (GV-ISys), übernommen über das npm-Paket `landkreise-deutschland` 3.0.0 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), © Statistisches Bundesamt (Destatis) | 31.12.2018 (Eisenach 2021 eingegliedert, wird weggelassen) |
| *optional:* Kreise, Gemeinden, Gemeindeverbände | Statistisches Bundesamt, [Gemeindeverzeichnis GV100AD](https://www.destatis.de/DE/Themen/Laender-Regionen/Regionales/Gemeindeverzeichnis/_inhalt.html) | [Datenlizenz Deutschland – Namensnennung 2.0](https://www.govdata.de/dl-de/by-2-0), © Statistisches Bundesamt | noch nicht importiert |

Nicht genutzt: PLZ-Daten der Deutschen Post (kostenpflichtig lizenziert), OpenPLZ-API direkt (dieselben Daten wie oben).

**Bekannte Grenzen**
- Die PLZ-Zuordnung ist geometrisch aus OSM bestimmt, nicht amtlich. Einzelne Straßen an Gemeindegrenzen können eine zusätzliche Gemeinde zu einer PLZ hinzufügen.
- Postfach- und Großkunden-PLZ fehlen (keine Straßen). Für sie fragt BürgerAI nach dem Bundesland.
- Rund 120 Gemeinden ohne Straßen (z. B. unbewohnte Gemeinden) fehlen in den OSM-Daten. Mit dem GV100AD-Import werden sie ohne PLZ ergänzt.

## Import ausführen

```bash
# 1. PLZ-Daten (≈ 55 MB) holen
git clone --depth 1 https://github.com/openpotato/openplzapi.data /tmp/openplz

# 2a. Kreisliste (klein) aus dem npm-Paket
mkdir -p /tmp/kreise && curl -sL https://registry.npmjs.org/landkreise-deutschland/-/landkreise-deutschland-3.0.0.tgz | tar xz -C /tmp/kreise

# 3. Erst nur ansehen, was sich ändert, dann schreiben
./bai gebiete-import --plz /tmp/openplz/src/de/osm/streets.updated.csv --plz-stand "openplzapi.data@$(git -C /tmp/openplz rev-parse --short HEAD)" \
    --kreise /tmp/kreise/package/data/districts.csv --kreise-stand 31.12.2018 --nur-diff
./bai gebiete-import ... (gleiche Optionen ohne --nur-diff)

# 4. Prüfen
./bai daten && ./bai szenarien --pruefen && python -m pytest
```

**Besser (amtlich, mit Gemeindeverbänden):** Statt 2a das aktuelle GV100AD von Destatis herunterladen (Gemeindeverzeichnis → „Gebietsstand“ → Datei `GV100AD_TTMMJJ.zip`, entpacken) und `--gv100ad GV100AD_TTMMJJ.txt` statt `--kreise …` angeben. Der Gebietsstand wird aus der Datei gelesen. Passen die Stände von OSM und GV100AD nicht zusammen (Gemeindeschlüssel aus den PLZ-Daten fehlen im Verzeichnis), bricht der Import mit einer Meldung ab.

Der Import ist wiederholbar. Vor dem Schreiben zeigt er neue, entfallene und umbenannte Gebiete, verschobene Gemeinden und geänderte PLZ. Das ist die Grundlage für die Prüfung von Datenänderungen vor der Freigabe (Phase 4).

## Länderdaten (`data/laender/<kürzel>/geburt.json`)

Von Hand gepflegt, recherchiert per Websuche am 25.10.2026. Die Behördenseiten selbst waren aus der Entwicklungsumgebung nicht erreichbar, daher ist der Prüfstatus höchstens `teilweise`. Jede Datei nennt ihre Quellen. Übersicht: `./bai abdeckung`.
