# Validierung gegen Primärquellen – Phase 1

**Abnahmekriterium Phase 1:** „Alle Testfälle der Pilotregion grün und gegen Quellen geprüft.“

| Teil | Stand 24.10.2026 |
|------|------------------|
| Testfälle grün | ✅ 143 Tests, 7 Szenarien, 51/51 Anforderungen abgedeckt |
| Gegen Quellen geprüft | ⏳ **offen** – keine Quelle ist `verifiziert`; 9 `teilweise`, 13 `ungeprueft`, 2 `widerspruechlich` |

Aktuellen Stand anzeigen: `./bai quellen --offen`

## Was bisher geprüft wurde (Status `teilweise`)

Abgleich per Websuche über mehrere Quellen. Die amtlichen Seiten (gesetze-im-internet.de, zbfs.bayern.de) waren aus der Entwicklungsumgebung nicht direkt abrufbar – daher noch nicht `verifiziert`.

| Angabe | Ergebnis |
|--------|----------|
| Elterngeld: Einkommensgrenze 175.000 € (Geburten ab 1.4.2025), 200.000 € (1.4.2024–31.3.2025) | bestätigt |
| Elterngeld: rückwirkend höchstens 3 Lebensmonate vor dem Antragsmonat (§ 7 BEEG) | bestätigt (FIM-Leistungsbeschreibung Bayern/Berlin) |
| Kindergeld: 259 € ab 1.1.2026 (2025: 255 €) | bestätigt |
| Kinderzuschlag: bis 297 € (2026), Mindesteinkommen 900 € Paare / 600 € Alleinerziehende | Mehrheit der Quellen; eine Quelle weicht ab |
| Mutterschaftsgeld: GKV bis 13 €/Tag; privat/familienversichert einmalig bis 210 € vom BAS; Schutzfrist 6 Wochen vor, 8 Wochen nach der Geburt | bestätigt |
| Geburtsanzeige: innerhalb einer Woche, Geburtstag zählt nicht mit, gebührenfrei | bestätigt (FIM-Stammtext); Paragraf (§ 18 PStG) noch im Volltext prüfen |
| München: Geburtenbüro München / München-Pasing, 12 € je Urkunde, gebührenfreie Urkunden für Elterngeld/Kindergeld/Mutterschaftshilfe | laut Seite der Stadt München |

## Widersprüchlich

**Bayerisches Familiengeld / Kinderstartgeld:** Das StMAS-Infoblatt (11/2024) nennt die Abschaffung für Kinder ab Geburt 1.1.2025. Spätere Landtagsdrucksachen (u. a. 19/8839) nennen den Stichtag 1.9.2026 mit einkommensabhängiger Übergangsregel (100.000 €). Das angekündigte Kinderstartgeld (3.000 €) wurde laut Berichten nicht eingeführt. → Die Regel gibt für Geburten 1.1.2025–31.8.2026 **Unklar** aus. Klären: beschlossene Fassung im Bayerischen GVBl. oder Auskunft des ZBFS.

## Checkliste für die manuelle Prüfung

Für jede Quelle aus `./bai quellen --offen`:

1. URL im Browser öffnen und Volltext lesen.
2. Jede Bedingung, die auf die Quelle verweist, vergleichen: `./bai erklaeren <leistung> -s <szenario>` zeigt die Bedingungen mit Quellen-IDs.
3. Beträge und Fristen vergleichen (`data/bund/geburt.json`, `data/laender/by/geburt.json`).
4. Zusätzlich gegen offizielle Rechner gegenprüfen: Elterngeldrechner (familienportal.de), KiZ-Lotse (arbeitsagentur.de).
5. Passt alles: in der Datei `"pruefstatus": "verifiziert"`, `"geprueft_am"` und `"geprueft_von"` setzen. Passt etwas nicht: Regel/Daten korrigieren, Testfall ergänzen, dann verifizieren.
6. `./bai daten && ./bai szenarien --pruefen && python -m pytest` ausführen.

Besonders prüfen (bisher nur aus Fachwissen, ohne Abgleich):
- Elterngeld: 32-Stunden-Grenze (§ 1 Abs. 6 BEEG), Regeln für Nicht-EU-Staatsangehörige (§ 1 Abs. 7).
- Kindergeld: Sechs-Monats-Frist für die rückwirkende Zahlung (§ 66 Abs. 3 EStG).
- Elternzeit: Anmeldung 7 Wochen vorher, schriftlich (§ 16 BEEG).
- Familienversicherung: Ausschluss nach § 10 Abs. 3 SGB V.
- Gebietsdaten: AGS München 09162000, Freising 09178124; PLZ 80xxx/81xxx = München, 85354/85356 = Freising.
