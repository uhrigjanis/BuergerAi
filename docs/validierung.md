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

### Landesleistungen (alle 16 Länder, je Land gesucht am 25.10.2026)

| Land | Ergebnis | Was gefunden wurde |
|------|----------|--------------------|
| Bremen | **erfasst: Begrüßungsgeld** (150 €, Studium oder Ausbildung) | Radio Bremen, Hochschule Bremen; Antragsweg und Frist widersprüchlich |
| Baden-Württemberg | keine | nur Förderung der freiwilligen Ausreise |
| Bayern | keine | „Bayerisches Rückkehrprogramm“ betrifft die Ausreise |
| Berlin | keine | Umzugsprämie nur für Mieter landeseigener Wohnungsunternehmen (Sekundärquelle) |
| Brandenburg | keine | Förderung von Zuzugsinitiativen, keine Zahlungen an Personen |
| Hamburg | keine | Prämie nur für die Freigabe rollstuhlgerechter Wohnungen |
| Hessen | keine | Umzugszuschuss nur für Ärztinnen und Ärzte (KV Hessen) |
| Mecklenburg-Vorpommern | keine | Wohnsitzprämie an Hochschulen; Fachkräfteförderung für Unternehmen |
| Niedersachsen | keine | nur kommunale Prämien (nur Sekundärquelle) |
| Nordrhein-Westfalen | keine | Landesumzugskostengesetz nur für Landesbedienstete |
| Rheinland-Pfalz | keine | Landesinitiative Rückkehr betrifft die Ausreise |
| Saarland | keine | nur Programme für Unternehmen (nur Sekundärquelle) |
| Sachsen | keine | Rückkehrförderung betrifft die Ausreise |
| Sachsen-Anhalt | keine | Rückkehrförderung betrifft die Ausreise; Beratung ohne Geldleistung |
| Schleswig-Holstein | keine | Umzugskostenregeln nur für Landesbedienstete |
| Thüringen | keine | Rückkehrprämie 2019 nur vorgeschlagen, nicht eingeführt |

„Keine“ heißt: Die Websuche je Land hat keine Landesleistung für Umziehende gefunden. Die Landesportale sind nicht vollständig durchgesehen.

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

## Lebenslage Pflege (Issue #41, Schritt 3)

Recherche am 26.10.2026, wieder nur über Suchergebnisse: Alle Quellen sind `teilweise` geprüft, widersprüchliche Angaben `widerspruechlich`. Die Notiz jeder Quelle sagt, was bestätigt ist.

### Für die manuelle Prüfung

| Quelle | Prüfen |
|--------|--------|
| `bmg_leistungsbetraege_2026`, `bmg_pflegeleistungen_nachschlagen` | Beträge 2026; Pflegehilfsmittel 42 € und Wohnumfeld 4.180 € nur über Ratgeber abgeglichen |
| `betanet_pflegeantrag` | 25 Arbeitstage, Leistungen rückwirkend ab Antrag (Sekundärquelle) |
| `bmg_pflegeunterstuetzungsgeld` | zehn Arbeitstage je Kalenderjahr und pflegebedürftiger Person (seit PUEG) |
| `bmbfsfj_familienpflegezeit`, `bt_18_8854`, `compass_infoblatt_pflegezeit` | Schwellen 15 und 25 Beschäftigte, Ankündigungsfristen, Zählweise der Beschäftigten |
| `sgb11_44` | Voraussetzungen der Rentenversicherung für Pflegepersonen (Gesetzestext nicht erreichbar) |
| `pflege_im_heim_bund` | Beträge für vollstationäre Pflege und Leistungszuschlag 2026 fehlen |
| `lfp_landespflegegeld` | **Widersprüchlich:** Antragsfrist (31.3. des Folgejahres oder 31.12.) |
| `berlin_lpflgg`, `bb_landesteilhabegeld`, `nrw_blindengeld` | **Widersprüchlich:** Höhe des Blindengelds |
| `ni_landesblindengeld`, `sl_blindheitshilfe`, `dresden_landesblindengeld`, `sh_blindengeld`, `th_sinnesbehindertengeld`, `lwv_hessen_blindengeld`, `bremen_landespflegegeld` | Höhe 2026 nicht amtlich bestätigt |
| `paderborn_pflegewohngeld`, `sh_pflege_bezahlen`, `vdk_hilfe_zur_pflege` | Einkommens- und Vermögensgrenzen, Antragsweg; in MV und SH keine Grenzen erfasst |

### Landesleistungen (alle 16 Länder)

| Land | Blindengeld (Name, Höhe laut Quelle) | Weitere Landesleistung | Grundlage |
|------|--------------------------------------|------------------------|-----------|
| Baden-Württemberg | Landesblindenhilfe, 410 € | – | service-bw |
| Bayern | Blindengeld, 809 € (seit 1.7.2026) | Landespflegegeld 500 € im Jahr | ZBFS, Landesamt für Pflege |
| Berlin | Landespflegegeld (LPflGG), Höhe widersprüchlich | – | Senatsverwaltung |
| Brandenburg | Landesteilhabegeld, 425 € bzw. 443,02 € | – | BRAVORS |
| Bremen | Landespflegegeld für Blinde, Höhe nicht bestätigt | – | service.bremen.de |
| Hamburg | Blindengeld, 695,50 € | – | hamburg.de |
| Hessen | Landesblindengeld, 86 % der Blindenhilfe | – | LWV Hessen |
| Mecklenburg-Vorpommern | Landesblindengeld, bis 430 € | Pflegewohngeld | Landesregierung, VdK |
| Niedersachsen | Landesblindengeld, Höhe nicht bestätigt | – | FIM |
| Nordrhein-Westfalen | Blindengeld (GHBG), 913,19 € bzw. 951,92 € | Pflegewohngeld | FIM, Kreis Paderborn |
| Rheinland-Pfalz | Landesblindengeld, 410 € (Stand 1.1.2025) | – | Kreis Mainz-Bingen |
| Saarland | Blindheitshilfe, Höhe nicht bestätigt | – | Landesamt für Soziales |
| Sachsen | Landesblindengeld, Höhe nicht bestätigt | – | Stadt Dresden |
| Sachsen-Anhalt | Blindengeld, bis 460,44 € (Stand 1.7.2025) | – | Landesamt (Formular 06/2026) |
| Schleswig-Holstein | Landesblindengeld, Höhe nicht bestätigt | Pflegewohngeld | Landesregierung |
| Thüringen | Sinnesbehindertengeld, Höhe nicht bestätigt | – | FIM |

„–“ heißt: Die Suche nach Landespflegegeld und Pflegewohngeld hat für das Land nichts gefunden. Gehörlosen- und Taubblindengeld sind nicht erfasst (folgt mit Behinderung).

## Lebenslage Wohneigentum (Issue #41, Schritt 4)

Recherche am 26.10.2026 über Suchergebnisse. Alle Quellen `teilweise`, widersprüchliche `widerspruechlich`.

### Für die manuelle Prüfung

| Quelle | Prüfen |
|--------|--------|
| `kfw_300`, `kfw_308`, `kfw_124`, `kfw_297` | Kredithöchstbeträge, Einkommensgrenze, Zeitpunkt des Antrags (vor Kauf- bzw. Bauvertrag), Ausschluss bei vorhandenem Eigentum |
| `heizung_2026_juli` | **Widersprüchlich:** Fördersätze seit 21.7.2026 (Einkommensbonus, Höchstsatz 70 % oder 80 %); amtliche KfW-Seite 458 lesen |
| `bafa_em_2026` | Fördersätze und iSFP-Bonus ab 30.000 € (nur Sekundärquelle) |
| `grest_saetze`, `grestg` | Steuersätze aller Länder in den Landesgesetzen; Thüringen 5,0 % (eine Übersicht nennt 6,5 %) |
| `hessengeld_wibank` | Antragsfrist (31.12.2029 nur laut Ratgeber) |
| `bb_wohneigentumfoerderr_2026` | **Widersprüchlich:** nimmt das Programm 2026 Anträge an? Fördergebiete |
| `isb_eigentum` | **Widersprüchlich:** Höhe der Tilgungszuschüsse |
| `tab_familien_wohneigentum` | **Widersprüchlich:** Mittel 2026 gebunden? |
| `lbank_z15`, `nbank_eigentum`, `sikb_eigentum_2026`, `st_wohneigentum_2026`, `sh_wofoerl_2026` | Einkommensgrenzen und Konditionen 2026 |
| `bremen_eigenheimzuschuss` | Höhe und ob das Programm 2026 läuft |

### Landesleistungen (alle 16 Länder)

| Land | Grunderwerbsteuer | Landesförderung | Grundlage |
|------|-------------------|-----------------|-----------|
| Baden-Württemberg | 5,0 % | Z15-Darlehen (L-Bank) | L-Bank |
| Bayern | 3,5 % | Zinsverbilligungsprogramm mit 5.000 € je Kind | Bauministerium |
| Berlin | 6,0 % | keine gefunden | Websuche |
| Brandenburg | 6,5 % | WohneigentumförderR 2026 (Status widersprüchlich) | BRAVORS |
| Bremen | 5,5 % | keine für das Land; Eigenheimzuschuss der Stadt Bremen | BAB |
| Hamburg | 5,5 % | IFB-Eigenheimdarlehen | IFB |
| Hessen | 6,0 % | Hessengeld | WIBank |
| Mecklenburg-Vorpommern | 6,0 % | keine (nur Modernisierung) | Förderdatenbank |
| Niedersachsen | 5,0 % | Eigentumsförderung NBank | NBank |
| Nordrhein-Westfalen | 6,5 % | Eigentumsförderung (NRW.BANK, Bewilligungsbehörde) | Stadt Münster |
| Rheinland-Pfalz | 5,0 % | ISB-Darlehen | ISB |
| Saarland | 6,5 % | SIKB-Eigentumsförderung | SIKB |
| Sachsen | 5,5 % | Familienwohnen (SAB) | Stadt Dresden |
| Sachsen-Anhalt | 5,0 % | neues Programm 2026 (IB) | Staatskanzlei |
| Schleswig-Holstein | 6,5 % | soziale Wohnraumförderung (IB.SH) | WoFöRL 2026 |
| Thüringen | 5,0 % | Erwerbszuschuss für Familien (Mittel 2026 gebunden) | TAB |

## Lebenslage Ausbildung, Studium oder Meister (Issue #41, Schritt 5)

Recherche am 26.10.2026 über Suchergebnisse. Alle Quellen `teilweise`, widersprüchliche `widerspruechlich`.

### Für die manuelle Prüfung

| Quelle | Prüfen |
|--------|--------|
| `bmftr_bafoeg`, `dsw_bafoeg_saetze` | Bedarfssätze (475 €, 380 €, 59 €), Altersgrenze 45 und Ausnahmen, Zeitpunkt des Antrags |
| `ba_bab_2026` | Voraussetzungen der eigenen Wohnung, Höchstsatz 2026 (822 € nur laut Ratgeber) |
| `ba_kindergeld_2026` | 259 €, Altersgrenze 25 |
| `aufstiegs_bafoeg_drv` | Zuschuss 50 %, Erlass 50 %, Höchstbetrag 15.000 € (Sekundärquelle); Stand der Reform (Kabinett 15.7.2026) |
| `hh_meisterpraemie` | **Widersprüchlich:** 1.000 € oder 1.300 € |
| `be_meisterbonus`, `st_meisterbonus_plus` | Höhe 2026 |
| `ni_meisterpraemie` | Antragsfrist, Laufzeit über 2026 hinaus |
| `th_meisterbonus` | gilt der Weg auch für Handwerksmeister? |

### Meisterbonus bzw. Aufstiegsprämie (alle 16 Länder)

| Land | Prämie | Wer | Frist | Grundlage |
|------|--------|-----|-------|-----------|
| Baden-Württemberg | Meisterprämie 1.500 € | nur Handwerk | Stichtage 31.5. und 30.11. | Stadt Heidelberg (HWK) |
| Bayern | Meisterbonus 3.000 € | DQR 6/7 | Ergebnis höchstens 2 Jahre alt | Richtlinie |
| Berlin | Meister- und MeisterinnenBONUS, Höhe 2026 offen | nur Handwerk | – | Richtlinie 2026/27 |
| Brandenburg | keine (nur Gründungsprämie) | – | – | Förderdatenbank |
| Bremen | Aufstiegsfortbildungsprämie 1.300 € | DQR 6/7 | – | Richtlinie ab 1.3.2025 |
| Hamburg | Meisterprämie 1.000 € bzw. 1.300 € | DQR 6/7 | 3 Monate | Förderdatenbank |
| Hessen | Aufstiegsprämie 3.500 € | DQR 6/7 | 3 Monate | Merkblatt Ministerium |
| Mecklenburg-Vorpommern | Meister-Extra 2.000 € | Handwerk und Industrie | 6 Monate | Landesregierung |
| Niedersachsen | Meisterprämie 4.000 € | nur Handwerk | laut NBank | NBank-Richtlinie |
| Nordrhein-Westfalen | Meisterprämie 2.500 € | nur Handwerk | 3 Monate | Landesregierung |
| Rheinland-Pfalz | Aufstiegsbonus I 2.000 € | DQR 6/7 | 4 Monate | Förderdatenbank |
| Saarland | Aufstiegsbonus 2.000 € | DQR 6/7 | 3 Monate | Richtlinie 1.1.2026 |
| Sachsen | Meisterbonus 3.000 € | DQR 6 | – | Medienservice Sachsen |
| Sachsen-Anhalt | Meisterbonus PLUS, 1.000 € laut Bericht | DQR 6 | Ergebnis höchstens 1 Jahr alt | IHK Magdeburg |
| Schleswig-Holstein | keine (nur Gründungsprämie) | – | – | FIM |
| Thüringen | Meisterbonus 2.000 € | DQR 6/7 | – | IHK Gera |

## Lebenslage Behinderung (Issue #41, Schritt 6)

Recherche am 26.10.2026 über Suchergebnisse. Alle Quellen `teilweise`, widersprüchliche `widerspruechlich`.

### Für die manuelle Prüfung

| Quelle | Prüfen |
|--------|--------|
| `sgb9_152` | Feststellung, Ausweis ab GdB 50 (Gesetzestext nicht erreichbar) |
| `wertmarke_2026` | Preis 104 € bzw. 53 €, kostenlose Wertmarke (nur Sekundärquelle) |
| `berlin_lageso_kfz` | Kfz-Steuer: Befreiung und Ermäßigung, Verhältnis zur Freifahrt (ein Ratgeber widerspricht bei H, Bl, aG) |
| `berlin_rundfunk_rf` | Ermäßigung auf 6,12 €, rückwirkend drei Jahre |
| `sachsen_zusatzurlaub`, `ihk_schwerbehinderung` | Zusatzurlaub, Voraussetzungen der Gleichstellung |
| `th_feststellung` | **Widersprüchlich:** Landkreise und Städte (seit 2008) oder Landesamt TLVLV |
| `nw_feststellung` | nur Sekundärquelle; amtliche Seite einer Stadt bzw. eines Kreises ergänzen |

### Zuständige Stelle für Feststellung und Wertmarke (alle 16 Länder)

| Land | Stelle |
|------|--------|
| Baden-Württemberg | Versorgungsamt beim Landratsamt bzw. Stadtkreis |
| Bayern | Zentrum Bayern Familie und Soziales (ZBFS), Regionalstelle |
| Berlin | LAGeSo – Versorgungsamt |
| Brandenburg | Landesamt für Soziales und Versorgung (LASV), Cottbus |
| Bremen | Amt für Versorgung und Inklusion (AVIB) |
| Hamburg | Versorgungsamt Hamburg |
| Hessen | Hessisches Amt für Versorgung und Soziales (HAVS) am Wohnort |
| Mecklenburg-Vorpommern | Landesamt für Gesundheit und Soziales (LAGuS) |
| Niedersachsen | Landesamt für Soziales, Jugend und Familie, Außenstelle |
| Nordrhein-Westfalen | Kreis bzw. kreisfreie Stadt |
| Rheinland-Pfalz | Landesamt für Soziales, Jugend und Versorgung (LSJV) |
| Saarland | Landesamt für Soziales, Abteilung Schwerbehinderung |
| Sachsen | Landratsamt bzw. kreisfreie Stadt |
| Sachsen-Anhalt | Landesverwaltungsamt, Halle |
| Schleswig-Holstein | Landesamt für Arbeitsschutz, Soziales und Gesundheit (LASG), Außenstelle |
| Thüringen | Landratsamt bzw. kreisfreie Stadt (widersprüchlich) |

Landesleistung der Lebenslage ist das Blindengeld (Tabelle unter Pflege). Gehörlosen- und Taubblindengeld sind nicht erfasst.

## Lebenslagen Job verloren und Selbstständig machen (Issue #41, Schritt 6)

Recherche am 26.10.2026 über Suchergebnisse. Alle Quellen `teilweise`, widersprüchliche `widerspruechlich`.

### Für die manuelle Prüfung

| Quelle | Prüfen |
|--------|--------|
| `ba_arbeitsuchend_2026`, `ba_alg`, `ba_sperrzeit` | Fristen § 38 SGB III (Änderung durch Gesetz vom 24.7.2026?), Anwartschaft, Sperrzeit 12 Wochen |
| `kschg_4`, `insolvenzgeld_fim` | Drei Wochen ab Zugang; zwei Monate ab Insolvenzereignis |
| `ihk_gruendungszuschuss` | 150 Tage Restanspruch (eine Ratgeberseite widerspricht) |
| `sgb2_16b` | Einstiegsgeld: Hauptberuf, Höhe |
| `steuerliche_erfassung`, `gewerbeanmeldung`, `handwerksrolle` | Fristen und Ausnahmen |
| `be_meistergruendung`, `st_meistergruendung` | nur Sekundärquellen |
| `bb_meistergruendung` | **Widersprüchlich:** Höhe und Antragsstatus |
| `th_meistergruendung`, `hh_gruendung_handwerk` | Höhe nicht amtlich |
| alle `*_keine_erwerbslosenberatung` | „keine“ beruht auf Websuchen; Landeshaushalte prüfen |

### Landesleistungen (alle 16 Länder)

| Land | Job verloren: Beratung | Selbstständig: Meistergründungsprämie |
|------|------------------------|----------------------------------------|
| Baden-Württemberg | Arbeitslosenberatungszentren | Tilgungszuschuss L-Bank (10 %, max. 10.000 €) |
| Bayern | keine | keine (Meisterbonus, LfA-Kredite) |
| Berlin | BALZ (Senat) | bis 25.000 € |
| Brandenburg | keine | Meistergründungsprämie (widersprüchlich) |
| Bremen | keine | keine |
| Hamburg | keine | Zuschuss zum Hamburg-Kredit bei Ausbildungsplatz |
| Hessen | keine | keine (Beratung, Mikrodarlehen) |
| Mecklenburg-Vorpommern | keine | 7.500 € + 2.500 € je Arbeitsplatz |
| Niedersachsen | unabhängige Erwerbslosenberatungsstellen | 10.000 € bei neuem Arbeitsplatz |
| Nordrhein-Westfalen | Beratungsstellen Arbeit | bis 11.500 € (+2.000 € bei Übernahme) |
| Rheinland-Pfalz | keine | Aufstiegsbonus II 2.500 € |
| Saarland | Arbeitskammer (Landesrecht) | Gründer- und Nachfolgebonus 2.500 € |
| Sachsen | keine | keine (InnoStartBonus u. a.) |
| Sachsen-Anhalt | keine | 10.000 € (seit 7/2026) |
| Schleswig-Holstein | keine | bis 7.500 € + 2.500 € |
| Thüringen | keine | Meistergründungsprämie (Höhe offen) |

## Lebenslage Todesfall (Issue #41, Schritt 6)

Recherche am 26.10.2026 über Suchergebnisse. Alle Quellen `teilweise`, widersprüchliche `widerspruechlich`. Die Bestattungsfristen ändern sich derzeit in mehreren Ländern (Reformen 2024–2026); Übersichtsseiten im Netz sind oft veraltet.

### Für die manuelle Prüfung

| Quelle | Prüfen |
|--------|--------|
| `fim_sterbefall`, `stuttgart_sterbefall` | Dritter Werktag, Samstag zählt nicht (§§ 28, 29 PStG) |
| `drv_vorschuss` | 30 Tage, Renten Service der Deutschen Post |
| `drv_renten_wegen_todes`, `rente_antragsfrist` | Mindestehedauer ein Jahr (nur Sekundärquelle); zwölf Monate rückwirkend |
| `bgb_1944`, `ag_achim_ausschlagung` | Sechs Wochen ab Kenntnis, Gebühr |
| `berlin_bestattungskosten`, `koeln_bestattungskosten` | § 74 SGB XII |
| `he_bestattung`, `mv_bestattung`, `rp_bestattung`, `sh_bestattung` | nur Sekundärquellen; Gesetzestext prüfen |
| `rp_bestattung` | **Widersprüchlich:** 14 Tage (Gesetz 2025) gegen 10 Tage (ältere Texte) |
| `sl_bestattung` | **Widersprüchlich:** 10 Tage (Fassung 2021) gegen 7 Tage (2009) |
| `be_bestattung`, `hb_bestattung`, `hh_bestattung` | keine feste Höchstfrist im Gesetz gefunden |

### Bestattungsfrist (alle 16 Länder)

| Land | Frist | Datum berechnet |
|------|-------|-----------------|
| Baden-Württemberg | 96 Stunden, wenn nicht in einer Leichenhalle aufgebahrt | nein |
| Bayern | 8 Tage, ohne Samstage, Sonn- und Feiertage | nein |
| Berlin | keine feste Höchstfrist im Gesetz gefunden (Friedhofsordnung) | nein |
| Brandenburg | 10 Tage | ja |
| Bremen | keine feste Höchstfrist gefunden; Behörde handelt nach 10 Tagen | nein |
| Hamburg | Bestattung binnen 10 Tagen veranlassen (sonst Meldung) | nein |
| Hessen | 10 Tage (seit 2025) | ja |
| Mecklenburg-Vorpommern | 10 Tage (soll) | ja |
| Niedersachsen | 8 Tage (soll) | ja |
| Nordrhein-Westfalen | 10 Tage | ja |
| Rheinland-Pfalz | 14 Tage (seit 2025, widersprüchlich) | ja |
| Saarland | 10 Tage (Erdbestattung, widersprüchlich) | ja |
| Sachsen | 8 Tage, ohne Samstage, Sonn- und Feiertage | nein |
| Sachsen-Anhalt | 10 Tage (soll) | ja |
| Schleswig-Holstein | 9 Tage | ja |
| Thüringen | 10 Tage | ja |

## Lebenslage Schulstart (Issue #41, Schritt 6)

Recherche am 26.10.2026 über Suchergebnisse. Alle Quellen `teilweise`, widersprüchliche `widerspruechlich`. Viele Ratgeberseiten nennen veraltete Stichtage.

### Für die manuelle Prüfung

| Quelle | Prüfen |
|--------|--------|
| `bildungsserver_stichtage` | Übersicht aller Länder (DIPF); als Zweitquelle je Land genutzt |
| `bmbfsfj_ganztag` | Rechtsanspruch § 24 Abs. 4 SGB VIII ab 1.8.2026, aufwachsend |
| `bw_einschulung`, `mv_einschulung`, `rp_einschulung`, `sl_einschulung` | nur Bildungsserver; Seiten der Kultusministerien prüfen |
| `by_einschulung` | nur Sekundärquelle (Korridor 1.7.–30.9.) |
| `hh_einschulung` | **Widersprüchlich:** 1. Juli (Bildungsserver) gegen 30. Juni bzw. 30. September (Ratgeber) |
| `bb_einschulung` | Wechsel auf 30. Juni nur in einer Ratgeberseite erwähnt |
| alle | Zählung des Stichtags (Geburtstag am Stichtag bzw. am Tag danach) |

### Stichtag der Schulpflicht (alle 16 Länder)

| Land | Schulpflichtig, wer sechs wird bis | Besonderheit |
|------|------------------------------------|--------------|
| Baden-Württemberg | 30. Juni | früher 30. September |
| Bayern | 30. September | Korridor 1.7.–30.9.: Eltern entscheiden |
| Berlin | 30. September | Anmeldung im Oktober des Vorjahres |
| Brandenburg | 30. September | Anmeldung 2027/28 ab 2.11.2026 |
| Bremen | 30. Juni | 1.7.–30.9. auf Antrag |
| Hamburg | 1. Juli (widersprüchlich) | Vorstellung der Viereinhalbjährigen |
| Hessen | 1. Juli (geboren) bzw. 30. Juni (sechstes Lebensjahr vollendet) | Anmeldung März/April des Vorjahres |
| Mecklenburg-Vorpommern | 30. Juni | |
| Niedersachsen | 30. September | 1.7.–30.9.: Aufschub per Erklärung bis 1. Mai |
| Nordrhein-Westfalen | 30. September | Anmeldung bis 15. November des Vorjahres |
| Rheinland-Pfalz | 31. August | |
| Saarland | 30. Juni | |
| Sachsen | 30. Juni | bis 30.9. mit Anmeldung schulpflichtig; Anmeldung 1.8.–15.9. |
| Sachsen-Anhalt | 30. Juni | |
| Schleswig-Holstein | 30. Juni | |
| Thüringen | 1. August (am 1. August sechs) | |

## Lebenslage Heirat (Issue #41, Schritt 6)

Recherche am 26.10.2026 über Suchergebnisse. Alle Quellen `teilweise`.

### Für die manuelle Prüfung

| Quelle | Prüfen |
|--------|--------|
| `berlin_eheschliessung` | Frühestens sechs Monate vorher, sechs Monate gültig (§§ 11, 12 PStG) |
| `bund_ausweis_name` | Ausweis ungültig nach Namensänderung; acht Wochen vorher nur mit Bescheinigung (bisher nur für Hessen belegt) |
| `bmf_steuerklasse_heirat` | IV/IV automatisch; Stand der geplanten Abschaffung von III/V |
| `vdek_familienversicherung` | Grenzen 2026 (565 €, 603 €); amtliche Quelle (GKV-Spitzenverband) ergänzen |
| `rp_eheschliessung`, `sh_eheschliessung` | Merkblätter von 2017 bzw. 2021; Gebühren evtl. veraltet |
| `sn_eheschliessung` | Quelle ist der Leitfaden des OLG zur Ehefähigkeit, nicht das Serviceportal Amt24 |

### Landesleistungen (alle 16 Länder)

Keine. In allen Ländern wird die Eheschließung beim Standesamt nach Bundesrecht (PStG, BGB) angemeldet; die Länder regeln nur die Gebühren. Je Land ist eine eigene Quelle hinterlegt (`*_eheschliessung` in `data/laender/*/heirat.json`).

## Lebenslage Ruhestand (Issue #41, Schritt 6)

Recherche am 26.10.2026 über Suchergebnisse. Alle Quellen `teilweise`.

### Für die manuelle Prüfung

| Quelle | Prüfen |
|--------|--------|
| `drv_regelaltersgrenze`, `betanet_regelaltersgrenze` | Tabelle der Regelaltersgrenze; Rentenbeginn im Folgemonat (Geburtstag am Ersten) |
| `drv_vorzeitige_rente` | nur Sekundärquelle: 35/45 Jahre, Abschläge, schwerbehinderte Menschen |
| `kvdr_9_10` | 9/10-Regel, drei Jahre je Kind |
| `mv_seniorenticket` | Preis 2026 (43 €) nur aus Sekundärquellen |
| `hh_seniorenticket` | Start 1.5.2026 umgesetzt? |
| `he_seniorenticket` | Umfang der Landesförderung nicht belegt |
| alle `*_kein_seniorenticket` | „keine“ beruht auf Übersichtsartikeln; Landesseiten prüfen |

### Seniorenticket des Landes (alle 16 Länder)

| Land | Seniorenticket | Ab |
|------|----------------|----|
| Mecklenburg-Vorpommern | Deutschlandticket mit 20 € Landeszuschuss | 65 |
| Hamburg | hvv Deutschlandticket für Senioren (49 €) | 67 |
| Hessen | Seniorenticket Hessen (398 € im Jahr) | 65 |
| Berlin, Brandenburg | keine (VBB-Abo 65plus seit 2026 eingestellt) | |
| alle übrigen | keine (nur Angebote von Verbünden oder Städten) | |
