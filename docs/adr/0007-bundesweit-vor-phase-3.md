# ADR 0007: Bundesweite Abdeckung vor der LLM-Schicht

**Status:** angenommen · **Datum:** 25.10.2026 · **Issue:** #40

## Kontext
Der ursprüngliche Plan sah die Erweiterung auf weitere Regionen erst nach Beta und Veröffentlichung vor (Phase 5). Eine Freitextsuche (Phase 3) bringt aber erst dann einen Mehrwert, wenn das Ergebnis dahinter für alle Nutzer stimmt. Außerhalb Bayerns kannte die Wissensbasis nur Bundesdaten und gab vor allem Warnungen aus.

## Entscheidung

### Reihenfolge
Das Lebensereignis **Geburt** wird zuerst für **ganz Deutschland** angebunden, dann folgt Phase 3 (LLM, Freitext-Intake). ADR 0001 (Pilot Bayern) bleibt als Ausgangspunkt gültig; das Feld `pilot` entfällt.

### Spike Stufe 0: Freising komplett erfassen
- **Jugendamt** (Landratsamt Freising, Amt für Jugend und Familie): mit einer Websuche gefunden (Merkblatt des Amts als Quelle), Prüfstatus `teilweise`. Adresse, Termine und Öffnungszeiten waren nicht auffindbar.
- **Standesamt** Freising: Nach zwei Suchen gab es nur Verzeichniseinträge (Bayernportal, Telefonbuch) mit widersprüchlichen Öffnungszeiten, keine Seite der Stadt. **Nicht erfasst**, Freising bleibt beim Landes-Fallback (ANF-BY-03).
- Aufwand: etwa 10–15 Minuten je Stelle, und das Ergebnis ist trotzdem nur `teilweise` geprüft. Hochgerechnet auf rund 10.700 Gemeinden und 400 Kreise sind das weit über 1.000 Stunden.
- **Folgerung:** Von Hand werden nur die 16 Länder gepflegt (Elterngeldstelle, Landesleistungen). Gebiete und PLZ werden automatisch importiert. Für Standesämter und Jugendämter je Gemeinde bzw. Kreis braucht es einen automatischen Import aus einem Zuständigkeitsfinder (Kandidat: PVOG/FIM-Leistungsschlüssel). Das ist ein eigenes Folge-Issue. Bis dahin gilt der Landes-/Bundes-Fallback mit ehrlichem Abdeckungsstatus.

### Gebiete und PLZ (Stufe 1)
- Import mit `buergerai gebiete-import` nach `data/generiert/gebiete.json`, getrennt von handgepflegten Daten, mit Quellversion, Importdatum und Diff zur vorherigen Fassung.
- Quellen und Lizenzen: siehe [docs/datenquellen.md](../datenquellen.md). PLZ ↔ Gemeinde kommt aus OpenStreetMap (OpenPLZ, ODbL), weil Destatis keine PLZ liefert. Die Lizenzen der Deutschen Post wären kostenpflichtig.
- PLZ ↔ Gemeinde ist n:m (rund 1.450 mehrdeutige PLZ). Die Gemeindeauswahl ist sortiert und nennt den Kreis.
- Gemeindeverbände: Der Import liest sie aus dem amtlichen GV100AD (Destatis). In der aktuellen Datei fehlen sie noch, weil Destatis aus der Entwicklungsumgebung nicht erreichbar war. Sie werden als Attribut `verband` der Gemeinde geführt, nicht als eigene Ebene. Eine Ebene wird erst gebraucht, wenn Varianten daran hängen (Standesamt einer Verwaltungsgemeinschaft).
- Postfach- und Großkunden-PLZ haben keine Straßen und damit keine Gemeinde. Für sie bleibt die Rückfrage nach dem Bundesland (ANF-GEB-04).

### Abdeckung statt Pilot
- Je **Leistung** (berechnet): `erfasst`, wenn die Variante auf der Verwaltungsebene liegt (z. B. Elterngeldstelle des Landes, Jugendamt des Kreises), sonst `allgemein`. Die Warnung im Bericht nennt die Leistungen, bei denen die Stelle vor Ort fehlt, außer denen mit Ergebnis Nein.
- Je **Land** (Daten, `abdeckung` mit `landesleistungen: erfasst | keine`): Fehlt der Eintrag, ist der Status `fehlt` und der Bericht warnt. Die Konsistenzprüfung stellt sicher, dass `erfasst` nur mit eigener Landesleistung und `keine` nur ohne steht.
- `buergerai abdeckung` zeigt je Land, für wie viele Gemeinden die Stelle je Leistung erfasst ist.
- Zuständigkeiten dürfen Platzhalter `{kreis}`, `{gemeinde}`, `{land}` enthalten. So nennt ein Landes-Fallback trotzdem den Kreis („Jugendamt – Landkreis Kassel“), ohne 400 Varianten von Hand.

### Länder (Stufe 2)
- Elterngeld je Land: zentral (BW, BY, MV, SL), zentral mit Standort je Kreis (HE, SH: Varianten auf Kreisebene), Bezirksamt (BE, HH), Kreis bzw. kreisfreie Stadt (BB, HB, NI, NW, RP, SN, ST, TH: Landesvariante mit `{kreis}`).
- Landesleistungen: Bayern (Familiengeld, eingestellt) und Sachsen (Landeserziehungsgeld). Alle anderen Länder sind als `keine` dokumentiert.

## Folgen
- Die Wissensbasis hat rund 11.100 Gebiete und lädt in etwa 0,2 s (Test: unter 2 s, ANF-DAT-13). JSON bleibt ausreichend (ADR 0002).
- Alle Länderdaten stammen aus Websuchen (Prüfstatus höchstens `teilweise`). Die Stichprobe gegen Behördenseiten ist offen, siehe [docs/validierung.md](../validierung.md).
- Offen für Folge-Issues: Standesamt je Gemeinde und Jugendamt je Kreis automatisch importieren (PVOG), GV100AD-Import mit Gemeindeverbänden ausführen, kreisangehörige Städte mit eigenem Jugendamt bzw. eigener Elterngeldstelle (z. B. Schwedt/Oder) als Ausnahmen erfassen.
