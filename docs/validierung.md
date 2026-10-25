# Validierung gegen Primärquellen

## Phase 1

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
3. Beträge und Fristen vergleichen (`data/fachmodule/familie/geburt.json`, `data/laender/by/geburt.json`).
4. Zusätzlich gegen offizielle Rechner gegenprüfen: Elterngeldrechner (familienportal.de), KiZ-Lotse (arbeitsagentur.de).
5. Passt alles: in der Datei `"pruefstatus": "verifiziert"`, `"geprueft_am"` und `"geprueft_von"` setzen. Passt etwas nicht: Regel/Daten korrigieren, Testfall ergänzen, dann verifizieren.
6. `./bai daten && ./bai szenarien --pruefen && python -m pytest` ausführen.

Besonders prüfen (bisher nur aus Fachwissen, ohne Abgleich):
- Elterngeld: 32-Stunden-Grenze (§ 1 Abs. 6 BEEG), Regeln für Nicht-EU-Staatsangehörige (§ 1 Abs. 7).
- Kindergeld: Sechs-Monats-Frist für die rückwirkende Zahlung (§ 66 Abs. 3 EStG).
- Elternzeit: Anmeldung 7 Wochen vorher, schriftlich (§ 16 BEEG).
- Familienversicherung: Ausschluss nach § 10 Abs. 3 SGB V.
- Gebietsdaten: AGS München 09162000, Freising 09178124; PLZ 80xxx/81xxx = München, 85354/85356 = Freising.


## Bundesweite Abdeckung (Issue #40)

**Abnahmekriterium:** „Stichprobe von mindestens 3 Gemeinden je Land gegen die Behördenseiten geprüft.“

| Teil | Stand 25.10.2026 |
|------|------------------|
| Gebiete und PLZ | ✅ automatisch importiert (400 Kreise, 10.712 Gemeinden, 8.159 PLZ), Prüfstatus `ungeprueft` – siehe [datenquellen.md](datenquellen.md) |
| Elterngeldstelle je Land | ✅ erfasst für alle 16 Länder, recherchiert per Websuche (`teilweise` bzw. `ungeprueft`) |
| Landesleistungen | ✅ Bayern (Familiengeld) und Sachsen (Landeserziehungsgeld) erfasst, übrige Länder als „keine“ dokumentiert |
| Stichprobe gegen Behördenseiten | ⏳ **offen** – die Behördenseiten waren aus der Entwicklungsumgebung nicht erreichbar; Tabelle unten ist vorbereitet |

Aktuellen Stand anzeigen: `./bai abdeckung` (je Land) und `./bai gebiet <PLZ>` bzw. `./bai pruefen --plz <PLZ> -d`.

### Stichprobe: 3 Gemeinden je Land

Je Land die Landeshauptstadt und zwei zufällig gewählte Gemeinden (Hamburg und Berlin haben nur eine). Zu prüfen:

1. **Gebiet:** Gehört die PLZ zur Gemeinde, und liegt die Gemeinde im genannten Kreis? Abgleich mit der Seite der Gemeinde oder dem Gemeindeverzeichnis von Destatis.
2. **Elterngeldstelle:** Stimmt die Stelle? Abgleich mit der Seite des Landes bzw. Kreises oder mit der Suche „Elterngeldstelle finden“ im Familienportal.
3. **Jugendamt/Standesamt:** Ist der Fallback-Text richtig (z. B. keine kreisangehörige Stadt mit eigenem Jugendamt)?
4. Ergebnis in die Spalte „geprüft“ (Datum, Kürzel; Abweichungen darunter notieren). Bei Abweichungen: Daten korrigieren, Szenario oder Test ergänzen.

| Land | Gemeinde (AGS) | PLZ (Beispiel) | Kreis | Elterngeldstelle laut BürgerAI | geprüft |
|---|---|---|---|---|---|
| SH | Kiel (01002000) | 24103 | Kreisfreie Stadt Kiel | LASG Schleswig-Holstein, Elterngeldstelle Neumünster | offen |
| SH | Auufer (01061005) | 25548 | Kreis Steinburg | LASG Schleswig-Holstein, Elterngeldstelle Heide | offen |
| SH | Neritz (01062050) | 23843 | Kreis Stormarn | LASG Schleswig-Holstein, Elterngeldstelle Lübeck | offen |
| HH | Hamburg (02000000) | 20095 | Kreisfreie Stadt Hamburg | Elterngeldstelle des Bezirksamts Ihres Wohnbezirks | offen |
| NI | Hannover (03241001) | 30159 | Region Hannover | Elterngeldstelle – Region Hannover | offen |
| NI | Polle (03255033) | 37647 | Landkreis Holzminden | Elterngeldstelle – Landkreis Holzminden | offen |
| NI | Rosche (03360018) | 29571 | Landkreis Uelzen | Elterngeldstelle – Landkreis Uelzen | offen |
| HB | Bremen (04011000) | 27568 | Kreisfreie Stadt Bremen | Elterngeldstelle – Kreisfreie Stadt Bremen | offen |
| HB | Bremerhaven (04012000) | 27568 | Kreisfreie Stadt Bremerhaven | Elterngeldstelle – Kreisfreie Stadt Bremerhaven | offen |
| NW | Köln (05315000) | 50667 | Kreisfreie Stadt Köln | Elterngeldstelle – Kreisfreie Stadt Köln | offen |
| NW | Kamen (05978020) | 59174 | Kreis Unna | Elterngeldstelle – Kreis Unna | offen |
| NW | Reken (05554044) | 48734 | Kreis Borken | Elterngeldstelle – Kreis Borken | offen |
| HE | Wiesbaden (06414000) | 55246 | Kreisfreie Stadt Wiesbaden | Hessisches Amt für Versorgung und Soziales Wiesbaden – Elterngeldstelle | offen |
| HE | Schrecksbach (06634021) | 34637 | Schwalm-Eder-Kreis | Hessisches Amt für Versorgung und Soziales Kassel – Elterngeldstelle | offen |
| HE | Waldsolms (06532022) | 35647 | Lahn-Dill-Kreis | Hessisches Amt für Versorgung und Soziales Gießen – Elterngeldstelle | offen |
| RP | Mainz (07315000) | 55116 | Kreisfreie Stadt Mainz | Elterngeldstelle – Kreisfreie Stadt Mainz | offen |
| RP | Harbach (07132045) | 57572 | Landkreis Altenkirchen (Westerwald) | Elterngeldstelle – Landkreis Altenkirchen (Westerwald) | offen |
| RP | Nierstein (07339043) | 55283 | Landkreis Mainz-Bingen | Elterngeldstelle – Landkreis Mainz-Bingen | offen |
| BW | Stuttgart (08111000) | 70173 | Stadtkreis Stuttgart | L-Bank – Elterngeldstelle | offen |
| BW | Großbottwar (08118021) | 71723 | Landkreis Ludwigsburg | L-Bank – Elterngeldstelle | offen |
| BW | Mosbach (08225058) | 74821 | Neckar-Odenwald-Kreis | L-Bank – Elterngeldstelle | offen |
| BY | München (09162000) | 80331 | Kreisfreie Stadt München | Zentrum Bayern Familie und Soziales (ZBFS) – Elterngeldstelle | offen |
| BY | Krün (09180122) | 82493 | Landkreis Garmisch-Partenkirchen | Zentrum Bayern Familie und Soziales (ZBFS) – Elterngeldstelle | offen |
| BY | Ascha (09278116) | 94347 | Landkreis Straubing-Bogen | Zentrum Bayern Familie und Soziales (ZBFS) – Elterngeldstelle | offen |
| SL | Saarbrücken (10041100) | 66111 | Regionalverband Saarbrücken | Landesamt für Soziales Saarland – Elterngeldstelle | offen |
| SL | Riegelsberg (10041517) | 66292 | Regionalverband Saarbrücken | Landesamt für Soziales Saarland – Elterngeldstelle | offen |
| SL | Weiskirchen (10042117) | 66709 | Landkreis Merzig-Wadern | Landesamt für Soziales Saarland – Elterngeldstelle | offen |
| BE | Berlin (11000000) | 10115 | Kreisfreie Stadt Berlin | Elterngeldstelle im Jugendamt Ihres Bezirks | offen |
| BB | Potsdam (12054000) | 14467 | Kreisfreie Stadt Potsdam | Elterngeldstelle – Kreisfreie Stadt Potsdam | offen |
| BB | Oberuckersee (12073430) | 17291 | Landkreis Uckermark | Elterngeldstelle – Landkreis Uckermark | offen |
| BB | Rheinsberg (12068353) | 16818 | Landkreis Ostprignitz-Ruppin | Elterngeldstelle – Landkreis Ostprignitz-Ruppin | offen |
| MV | Rostock (13003000) | 18055 | Kreisfreie Stadt Rostock | Landesamt für Gesundheit und Soziales (LAGuS) – Elterngeld | offen |
| MV | Rollwitz (13075115) | 17309 | Landkreis Vorpommern-Greifswald | Landesamt für Gesundheit und Soziales (LAGuS) – Elterngeld | offen |
| MV | Ritzerow (13071123) | 17153 | Landkreis Mecklenburgische Seenplatte | Landesamt für Gesundheit und Soziales (LAGuS) – Elterngeld | offen |
| SN | Dresden (14612000) | 01067 | Kreisfreie Stadt Dresden | Elterngeldstelle – Kreisfreie Stadt Dresden | offen |
| SN | Hohndorf (14521290) | 09394 | Erzgebirgskreis | Elterngeldstelle – Erzgebirgskreis | offen |
| SN | Kirchberg (14524130) | 08107 | Landkreis Zwickau | Elterngeldstelle – Landkreis Zwickau | offen |
| ST | Magdeburg (15003000) | 39104 | Kreisfreie Stadt Magdeburg | Elterngeldstelle – Kreisfreie Stadt Magdeburg | offen |
| ST | Hohenberg-Krusemark (15090245) | 39596 | Landkreis Stendal | Elterngeldstelle – Landkreis Stendal | offen |
| ST | Schnaudertal (15084442) | 06712 | Burgenlandkreis | Elterngeldstelle – Burgenlandkreis | offen |
| TH | Erfurt (16051000) | 99084 | Kreisfreie Stadt Erfurt | Elterngeldstelle – Kreisfreie Stadt Erfurt | offen |
| TH | Belrieth (16066005) | 98617 | Landkreis Schmalkalden-Meiningen | Elterngeldstelle – Landkreis Schmalkalden-Meiningen | offen |
| TH | Hetschburg (16071031) | 99438 | Landkreis Weimarer Land | Elterngeldstelle – Landkreis Weimarer Land | offen |

### Bekannte offene Punkte

- **Kreisangehörige Städte mit eigener Stelle:** In mehreren Ländern (u. a. NRW, Niedersachsen, Rheinland-Pfalz) haben große kreisangehörige Städte ein eigenes Jugendamt und teils eine eigene Elterngeldstelle. Brandenburg: Schwedt/Oder laut Zuständigkeitsverordnung. Diese Ausnahmen sind noch nicht erfasst; die Texte weisen darauf hin.
- **Bremen:** Die Namen der Elterngeldstellen in Bremen und Bremerhaven sind nicht recherchiert, nur die Aufteilung nach Stadt.
- **Schleswig-Holstein, Hessen:** Zuordnung Kreis → Standort stammt aus je einer Quelle (Landesseite SH, Flyer RP Gießen 2024).
- **Standesamt am Geburtsort:** BürgerAI zeigt bundesweit (außer München) nur „Standesamt des Geburtsorts“ ohne Kontaktdaten.

## Lebenslage Umzug (Issue #41, Schritt 1)

Alle Quellen haben den Status `teilweise`. Die Gesetzestexte (gesetze-im-internet.de, auch Spiegel wie dejure.org) und die Behördenseiten waren aus der Entwicklungsumgebung nicht abrufbar. Die Inhalte stammen aus Suchergebnissen, die mehrere Gesetzesportale bzw. die Behördenseite selbst wiedergeben. Die Notiz jeder Quelle sagt, was bestätigt ist.

### Für die manuelle Prüfung

| Quelle | Prüfen |
|--------|--------|
| `bmg_17`, `bmg_19` | Anmeldefrist zwei Wochen nach Einzug; Abmeldung nur bei Wegzug ins Ausland; Wohnungsgeberbestätigung |
| `fzv_15` | Ob die neue Anschrift ausdrücklich zu den unverzüglich mitzuteilenden Halterdaten gehört; Kennzeichen weiterführen |
| `rbstv_8` | Amtliche Fassung des § 8 RBStV (nur über einen Abdruck in einer Gerichtsentscheidung gefunden), URL ergänzen |
| `wogg_25`, `wogg_28` | Beginn des Bewilligungszeitraums; Unwirksamkeit des Bescheids bei Auszug |
| `sgb2_22` | Zuständigkeit des bisherigen Jobcenters für Umzugskosten (Abs. 6), Zusicherung zur neuen Miete (Abs. 4), aktuelle Fassung |
| `sgb3_44` | Umzugskosten als Teil des Vermittlungsbudgets; ob der Antrag vor Vertragsschluss nötig ist |
| `sgb1_60` | Mitwirkungspflicht; ob ein Umzug ausdrücklich genannt ist |
| `muenchen_wohnsitz`, `muenchen_hundesteuer`, `berlin_wohnsitz` | Fristen und Online-Wege auf den Behördenseiten; Münchner Hundesteuersatzung (risi.muenchen.de, Stand 2017) auf Aktualität |
| `fim_hundesteuer` | Volltext der FIM-Beschreibung (bisher nur Suchergebnis) |

### Landesleistungen

Für alle 16 Länder ist `landesleistungen: keine` eingetragen. Grundlage ist eine Websuche nach Umzugs-, Zuzugs- und Rückkehrprämien für Privatpersonen. Gefunden wurden nur Programme, die nicht an Umziehende zahlen (Brandenburg: Zuzugsinitiativen; Mecklenburg-Vorpommern: Wohnsitzprämie an Hochschulen). Die Lebenslage „Umzug“ der Landesportale ist noch nicht je Land geprüft. Findet sich dort eine Leistung, wird sie erfasst und der Eintrag auf `erfasst` gesetzt.

### Nicht erfasst

Bewusst nicht erfasst und im Bericht mit Begründung genannt: Abmeldung bei Umzug ins Ausland, Umzugskosten in der Steuererklärung, Begrüßungsgeld für Studierende (Quellen veraltet oder widersprüchlich, z. B. Kiel 100 € oder 150 €), Zweitwohnungsteuer, Kita und Schule, Nachsendeauftrag und Versorger.

## Lebenslage Geringes Einkommen (Issue #41, Schritt 2)

Wie bei Umzug: Alle Quellen sind `teilweise` geprüft, weil Gesetzestexte und Behördenseiten nur über Suchergebnisse erreichbar waren. Die Notiz jeder Quelle sagt, was bestätigt ist.

### Für die manuelle Prüfung

| Quelle | Prüfen |
|--------|--------|
| `bmas_neue_grundsicherung`, `sgb2_7` | Inkrafttreten 1.7.2026, Name „Grundsicherungsgeld“, Altersgrenzen, Drei-Stunden-Grenze der Erwerbsfähigkeit (§ 8 SGB II, nicht über die Suche bestätigt) |
| `regelbedarf_2026` | Regelbedarf 563 € bzw. 506 € (nur Sekundärquelle) |
| `sgb12_41` | Voraussetzungen der Grundsicherung im Alter und bei Erwerbsminderung |
| `wogg_7`, `fim_wohngeld` | Ausschlüsse vom Wohngeld und ihre Ausnahmen |
| `sgb2_28`, `bkgg_6b`, `betanet_but` | Berechtigte, Antragsweg, Antragsfrist von 12 Monaten (nur eine Quelle) |
| `rbstv_4` | Befreiungsgründe; ob Asylbewerberleistungen genannt sind (nicht über die Suche bestätigt); amtliche Fassung und URL |
| `berlin_ticket_s`, `berlinecho_ticket_s` | Preis 2026 (27,50 € nur laut Bericht), Übergangsregel |
| `hamburg_sozialrabatt` | Rabatt 35,50 €, berechtigte Leistungen |
| `hessenpass_mobil` | **Widersprüchlich:** Preis 39 € oder 44 €, Berechtigte nur aus Ratgebern; amtliche Seite des Landes suchen |
| `vbb_mobilitaetsticket` | Berechtigte außer Grundsicherungsgeld, Preis 2026 |
| `muenchen_pass` | Einkommensgrenzen (Tabelle auf der Seite nicht erfasst) |
| `sgb5_62` | Belastungsgrenze und Chroniker-Regel |

| `nrw_deutschlandticket_sozial` | Preis je Kreis und Verbund, ob alle Kreise teilnehmen, Anteil der Landesförderung |
| `bw_landesfamilienpass` | Berechtigte Gruppen, ob „Grundsicherung“ auch das Grundsicherungsgeld umfasst |
| `bremen_stadtticket`, `saarbruecken_sozialcard` | Preise 2026, Aktualität der Faltblätter |

### Landesleistungen (alle 16 Länder)

| Land | Ergebnis | Grundlage |
|------|----------|-----------|
| Baden-Württemberg | erfasst: Landesfamilienpass | service-bw |
| Berlin | erfasst: Berlin-Ticket S | service.berlin.de |
| Brandenburg | erfasst: Mobilitätsticket | VBB |
| Hamburg | erfasst: hvv-Sozialrabatt | Sozialbehörde |
| Hessen | erfasst: Hessenpass mobil (widersprüchlich) | Berichte |
| Nordrhein-Westfalen | erfasst: DeutschlandTicket Sozial | Verkehrsverbünde |
| Bayern | keine (Sozialpässe kommunal, München-Pass erfasst) | BayernPortal |
| Bremen | keine (StadtTicket und Bremer Pass der Stadt Bremen erfasst, Bremerhaven offen) | service.bremen.de |
| Mecklenburg-Vorpommern | keine (nur Senioren- und Azubi-Ticket) | VMV |
| Niedersachsen | keine (nur regional) | Bericht (sekundär) |
| Rheinland-Pfalz | keine (nur kommunal) | FIM |
| Saarland | keine (SOZIALCARD gilt nur in Saarbrücken, erfasst) | Stadt Saarbrücken |
| Sachsen | keine (nur Bildungsticket gefördert) | Bericht (sekundär) |
| Sachsen-Anhalt | keine (Pässe kommunal; FamilienPass nicht einkommensabhängig) | FIM, Landtag 2013 |
| Schleswig-Holstein | keine (Landes-Sozialticket nur gefordert) | Förderdatenbank |
| Thüringen | keine (Familienkarte nicht einkommensabhängig) | Aufbaubank |

„Keine“ heißt: Die Websuche am 25.10.2026 hat keine landeseigene Leistung gefunden. Die Landesportale sind nicht vollständig durchgesehen. Für Niedersachsen und Sachsen gibt es nur Sekundärquellen.
