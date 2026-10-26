# ADR 0008: Lebenslagen als Fachmodule (Experten) auf einer gemeinsamen Engine

**Status:** angenommen · **Datum:** 25.10.2026 · **Issue:** #41

## Kontext

Issue #41 erweitert BürgerAI von einer Lebenslage (Geburt) auf rund zehn: Familie, Wohnen und Bauen, Pflege, Behinderung, Schule und Ausbildung, Arbeit, Heirat, Umzug, Ruhestand, Todesfall, geringes Einkommen. Für Phase 3 (LLM, Freitext-Intake) ist ein Experte je Fachgebiet geplant. Die Frage ist, ob und wie dieses Experten-Denken schon jetzt in die Architektur gehört.

Drei Beobachtungen bestimmen die Antwort:

1. **Leistungen gehören zu mehreren Lebenslagen.** Wohngeld passt zu Wohnen, Umzug, Ruhestand und geringem Einkommen. Kinderzuschlag zu Familie und geringem Einkommen. Getrennte Experten mit eigenen Regeln würden dieselbe Leistung mehrfach und irgendwann widersprüchlich prüfen.
2. **Die Liste mischt zwei Arten.** Heirat, Umzug, Todesfall, Ruhestand und Geburt sind *Ereignisse* mit Datum und Fristen. Pflege, Behinderung, geringes Einkommen, Arbeit und Ausbildung sind *Situationen*, die länger andauern und quer zu den Ereignissen liegen. Eine Person kann beides gleichzeitig haben (Geburt plus geringes Einkommen).
3. **Die Engine ist schnell genug und soll es bleiben.** Gemessen am 25.10.2026: Laden der Wissensbasis 0,24 s (0,14 s ohne Konsistenzprüfung), ein Bericht für Geburt 1 ms (13 Leistungen, 76 Varianten, 11.129 Gebiete). Fast die ganze Ladezeit entfällt auf die Gebiete. Leistungen und Regeln sind im Vergleich klein.

Das Wiki-Dokument „Architektur“ verwendet „Experte“ für *funktionale* Rollen (Gebiets-, Anspruchs-, Verfahrens-Experte). Diese Rollen gibt es im Code schon als Module (`gebiete`, `regeln`, `planer`, `ausgabe`). Dieses ADR meint *fachliche* Experten. Um Verwechslung zu vermeiden, heißen sie hier **Fachmodule**.

## Entscheidung

### 1. Ein Fachmodul ist ein Datenpaket, kein eigener Code

Es gibt **eine** Regel-Engine und **einen** Planer für alle Lebenslagen. Ein Fachmodul bündelt alles Fachliche einer Lebenslage als Daten:

| Bestandteil | Zweck jetzt (ohne LLM) | Zweck in Phase 3 (LLM) |
|---|---|---|
| Steckbrief: `id`, Name, `typ` (`ereignis` oder `situation`), Kurzbeschreibung | Auswahl in Web und CLI | Beschreibung für den Router |
| Einstiegsfragen (Gating-Fakten, z. B. „Ist ein Pflegegrad festgestellt?“) | werden vor den Detailfragen gestellt | dieselben Fakten extrahiert das LLM zuerst |
| eigene Fakten mit Präfix (z. B. `pflege.pflegegrad`) | Faktenkatalog nach Lebenslage gruppiert | JSON-Schema für die Extraktion, nur dieser Ausschnitt |
| Leistungen, für die das Modul „Heimat“ ist, plus Verweise auf fremde Leistungen | welche Leistungen geprüft werden | – |
| Synonyme, Beispielsätze, Abgrenzungen („Hauskauf gehört zu Wohnen, nicht zu Umzug“) | einfache Stichwortsuche als Einstieg | Router- und Extraktions-Prompt, Evaluationsdaten |
| Szenarien und Anforderungen | Regressionstests | zusätzlich Freitext-Testfälle je Szenario |

Ein Fachmodul kann mehrere auswählbare Lebenslagen enthalten. **Geburt gehört zum Fachmodul `familie`** und ist dort eine Lebenslage vom Typ `ereignis` (einschließlich Schwangerschaft). Weitere Familien-Lebenslagen (z. B. Kinderbetreuung, Unterhaltsvorschuss) kommen in dasselbe Modul. Der Experte ist das Modul, ausgewählt werden die Lebenslagen.

Damit ist der Experte für Phase 3 vollständig beschrieben, ohne dass jetzt LLM-Code entsteht. Der LLM-Experte wird später aus diesen Daten erzeugt. Er schreibt nie Regeln, entscheidet nie über Ansprüche und nennt keine Leistung, die nicht in der Wissensbasis steht (ADR 0003, Akzeptanzkriterium in #41).

**Verworfen: ein Experte als eigene Klasse oder eigene Engine je Lebenslage.** Gründe: doppelte Leistungen und Fakten (Beobachtung 1), mehrere Durchläufe statt einem, Ergebnisse aus mehreren Experten müssten nachträglich zusammengeführt und auf Widersprüche geprüft werden. Wenn ein Fachgebiet wirklich eigene Logik braucht (z. B. Berechnung von Wohngeld), wird sie als benannte Funktion in der gemeinsamen Engine ergänzt, die die Regel-JSON aufruft, nicht als Sonderweg im Modul.

### 2. Datenlayout

```
data/
  kern/fakten.json               Fakten, die alle brauchen: Haushalt, Personen, Einkommen, Wohnort
  fachmodule/<id>/modul.json     Steckbrief: fachmodul, lebenslagen, rollen
  fachmodule/<id>/fakten.json    Fakten des Moduls
  fachmodule/<id>/<lage>.json    Leistungen und Bundesvarianten (z. B. familie/geburt.json)
  laender/<kürzel>/<lage>.json   Landesvarianten und Abdeckungsnachweis je Lebenslage (wie bisher)
  kreise/…, kommunen/…           wie bisher
  generiert/                     wie bisher
```

- Die bisherigen Dateien `data/bund/geburt.json` und `data/fakten.json` werden das erste Fachmodul `familie` (mit der Lebenslage `geburt`) und `kern`. Die Lebenslagen-ID `geburt` bleibt, damit Szenarien und Abdeckungsnachweise der Länder gültig bleiben. Die Szenarien sichern ab, dass sich dabei kein Ergebnis ändert.
- `Leistung.ereignisse` wird zu `Leistung.lebenslagen` (Liste). Die Datei, in der eine Leistung steht, ist ihr Heimatmodul. Andere Module verweisen nur darauf.
- Konsistenzprüfung: Ein Modul darf nur Kern-Fakten, eigene Fakten und ausdrücklich importierte Fakten anderer Module verwenden. Das hält die Schemata für das LLM klein und verhindert Namenskollisionen. Zu welchem Modul ein Fakt gehört, ergibt sich aus seinem Ablageort.

### 3. Änderungen am Kern, bevor die zweite Lebenslage kommt

Diese Punkte betreffen alle Module. Sie werden einmal gebaut, mit Geburt als Prüfstein, dann folgt die erste neue Lebenslage.

1. **Mehrere Lebenslagen je Anfrage.** `Anfrage.ereignis` wird `Anfrage.lebenslagen: list[str]`. Eine Leistung erscheint einmal, auch wenn mehrere gewählte Lebenslagen auf sie verweisen, und zeigt an, zu welchen sie gehört.
2. **Haushaltsmodell mit Rollen statt `mutter`/`partner`.** Rollen: `antragsteller`, `partner`, `kind`, dazu modulspezifische wie `pflegebeduerftig` oder `verstorben`. `person.*` wird je Rolle aufgelöst, die die Leistung in `fuer` nennt. Kinder zunächst über abgeleitete Zählfakten (z. B. `kern.anzahl_kinder_unter_18`), nicht über eine Prüfung je Kind. Das ist der größte Umbau und kommt deshalb zuerst.
3. **Ortsbezug je Leistung.** `Leistung.ortsbezug`: `wohnort` (Standard), `immobilie`, `wohnort_alt`, `wohnort_am_stichtag`. Für jeden benötigten Ortsbezug wird eine eigene Gebietshierarchie aufgelöst (z. B. aus `wohnen.plz_immobilie`). Beim Umzug gibt es so alten und neuen Wohnort ohne Sonderlogik.
4. **Neue Merkmale an der Leistung:** Art `foerderprogramm` mit `rechtsanspruch: false` und Hinweis „solange Mittel reichen“, `beantragt_von` (`selbst`, `arbeitgeber`, `angehoerige`, …), Leistungen nur auf Landesebene ohne Bundes-Fallback mit dem ehrlichen Hinweis „gibt es in Ihrem Land nicht“, wenn eine gewählte Lebenslage betroffen ist.
5. **Fragen priorisieren.** Mit zehn Lebenslagen wird die Liste offener Fragen lang. Reihenfolge: Grunddaten, dann Einstiegsfragen der gewählten Module, dann Detailfragen nach Entscheidungskraft (Anzahl der unklaren Leistungen, die eine Antwort entscheiden kann, gewichtet nach Pflicht und naher Frist). Die Engine liefert die nötigen Daten schon (`Eintrag.fehlend`), die Berechnung ist ein Durchlauf über die Einträge. Regeln stellen Gating-Fakten an den Anfang von `alle`, damit ein Nein die Detailfragen gar nicht erst auslöst (das kann die Engine schon).

### 4. Performance

Ziel: Die deterministische Antwort bleibt im Bereich weniger Millisekunden, egal wie groß der Katalog wird. Rechenaufwand soll von der Zahl der *gewählten* Lebenslagen abhängen, nicht von der Größe der Wissensbasis.

Annahme für den Endausbau von #41: etwa 500 Leistungen, 5.000 Varianten (inklusive kommunaler Förderprogramme), 600 Fakten. Das ist gegenüber den Gebieten klein und bleibt im Speicher.

Maßnahmen:

- **Indizes beim Laden** statt Suchen je Anfrage: Leistungen je Lebenslage, Varianten je (Leistung, Gebiet), Fakten je Modul, „hat Landesdaten“ je Lebenslage. Heute läuft `_hat_landesdaten` bei jeder Anfrage über alle Varianten. Das wird ein Nachschlagen.
- **Nur gewählte Module auswerten.** `planen` geht über die Leistungen der gewählten Lebenslagen, nicht über alle.
- **Kein Datenbankwechsel.** JSON und Standardbibliothek bleiben (ADR 0002). Neu bewerten, wenn das Laden länger als 2 s dauert, der Speicher über 200 MB steigt oder Daten außerhalb von Git gepflegt werden müssen. Erste Ausweichstufe wäre ein vorab erzeugter, geprüfter Snapshot der Wissensbasis, keine Datenbank.
- **Zustandslos bleiben.** Die Web-API bekommt bei jeder Anfrage alle Angaben. Bei 1–5 ms je Bericht ist das billiger als Sitzungen auf dem Server, und es bleibt datenschutzfreundlich.
- **Budgets als Tests.** Wie ANF-DAT-13 (Laden unter 2 s) kommen Anforderungen mit festen Grenzen dazu, z. B. ein Bericht mit drei Lebenslagen unter 20 ms und eine Testwissensbasis in Zielgröße (synthetisch erzeugt), damit Regressionen auffallen, bevor die echten Daten da sind.

### 5. Ausblick Phase 3: wie die Fachmodule zu LLM-Experten werden

```
Freitext ──► Router (Lebenslagen erkennen, mehrere möglich)
                │   Kandidaten vorab über Synonyme, LLM nur zur Entscheidung
                ▼
     je erkanntem Modul: Fakten extrahieren (nur dessen Schema)  ── parallel
                │
                ▼
     Fakten zusammenführen ──► gleiche Engine wie heute ──► Bericht
                                      │
                                      ▼
                       offene Fragen als Formular, nicht als LLM-Dialog
```

- **Latenz:** Router plus der langsamste Extraktionsaufruf, nicht die Summe. Der statische Teil jedes Experten (Steckbrief, Schema, Beispiele) ist ein fester Prompt-Anfang und eignet sich für Prompt-Caching. Bei wenigen erkannten Modulen kann ein einziger Aufruf mit den zusammengefügten Schemata günstiger sein als mehrere. Das wird gemessen, nicht vorab festgelegt.
- **LLM nur am Eingang:** Rückfragen kommen aus der Engine und werden als Formularfelder gestellt (wie heute). Das LLM wird nicht bei jeder Antwort neu aufgerufen.
- **Ohne LLM nutzbar:** Die Stichwortsuche über Synonyme und die Lebenslagen-Auswahl bleiben die Notbremse, wenn das LLM nicht verfügbar ist (README, Phase 3).
- **Messbar:** Jedes Szenario bekommt optional einen Freitext. Daraus entsteht je Modul ein Evaluationssatz für Router und Extraktion.

### 6. Reihenfolge der Lebenslagen

| Schritt | Inhalt | Warum an dieser Stelle |
|---|---|---|
| 0 | Kernumbau (Abschnitt 3) mit Geburt im Fachmodul Familie als erstem Modul | jede spätere Lebenslage baut darauf auf, die Geburt-Szenarien prüfen ihn |
| 1 | **Umzug** | wenige Fakten, vor allem Pflichten mit Fristen, prüft zwei Ortsbezüge (alt und neu) |
| 2 | **Geringes Einkommen** | erste Situation quer zu Ereignissen, prüft Leistungen in mehreren Lebenslagen (Wohngeld, Kinderzuschlag, Bildung und Teilhabe) und die Fragenpriorisierung |
| 3 | **Pflege** | große Reichweite, Landesleistungen mit unterschiedlicher Zuständigkeit (Landespflegegeld, Landesblindengeld) |
| 4 | **Wohnen und Eigentum** | Förderprogramme, Ortsbezug Immobilie, Hessengeld als Landesleistung ohne Gegenstück |
| 5 | Schule, Ausbildung, Studium | Meisterbonus als „gibt es nur in manchen Ländern“ |
| 6 | Behinderung, Arbeit, Heirat, Ruhestand, Todesfall | nach Bedarf, Modell ist dann vollständig |

Die Reihenfolge weicht vom Vorschlag im Issue nur darin ab, dass geringes Einkommen vor Pflege und Wohnen kommt: Es testet die Mehrfachzuordnung früh, solange der Umbau noch billig ist.

### 7. Umsetzung von Schritt 0 (25.10.2026)

Gebaut wie oben beschrieben, mit diesen Abweichungen vom Plan:

- **Ablage:** `data/fachmodule/<id>/` statt `data/lebenslagen/`. Ein gesonderter Katalog `lebenslagen.json` entfällt, die Steckbriefe liegen in `modul.json` je Modul.
- **Rollen ohne Umbenennung:** Rollen sind Daten (`rollen` mit `id`, `name`, `wer` und optionaler `vorbedingung` als Regelknoten). Das Familien-Modul definiert `mutter` und `partner` (Vorbedingung: lebt im Haushalt). Neue Module bringen eigene Rollen mit (z. B. `pflegebeduerftig`). Deshalb müssen keine Faktennamen, Szenarien oder gespeicherten Angaben umgestellt werden. `fuer` ist `"haushalt"` oder eine Liste von Rollen.
- **Faktennamen:** Die Geburt-Fakten behalten ihre Namen. Neue Module verwenden ihr Präfix (`pflege.pflegegrad`). Erlaubt sind als Präfix nur Rollen und das eigene Modul.
- **Grunddaten werden Einstiegsfragen:** Das Feld `grunddaten` am Fakt entfällt. Jede Lebenslage nennt ihre `einstiegsfragen`. So fragt eine Anfrage nur zu Umzug nicht nach der Geburt.
- **Ortsbezug als Fakt:** `ortsbezug` nennt einen Fakt vom neuen Typ `ort` (PLZ oder Gemeindeschlüssel), statt fester Werte wie `immobilie`. Ist der Ort unbekannt, gilt nur der Bund. Gehört eine PLZ zu mehreren Gemeinden, gilt der gemeinsame Teil der Hierarchien, ohne Rückfrage.
- **Zusätzlich:** Fristen können sich auf jeden Datumsfakt beziehen (Einzugsdatum, Kaufdatum). `./bai lebenslagen --suche` ist die Stichwortsuche über Synonyme und Beispielsätze. Landesleistungen anderer Länder erscheinen als „Nur in anderen Ländern“.
- **Noch offen:** In der Web-Oberfläche lassen sich Lebenslagen erst wählen, wenn es eine zweite gibt (Schritt 1). Die API nimmt `lebenslagen` schon an.

Gemessen mit einer synthetischen Wissensbasis in Zielgröße (`tests/test_performance.py`, 503 Leistungen, 5.046 Varianten, 601 Fakten, alle Gebiete): Laden 0,3 s; ein Bericht mit 3 Lebenslagen und 81 Leistungen etwa 7 ms. Der Bericht für Geburt allein sank von 1,0 auf 0,8 ms. Die Indizes entstehen beim Laden, die Quellen je Variante werden zwischengespeichert.

### 8. Umsetzung von Schritt 1: Umzug (25.10.2026)

- **Eigenes Fachmodul `umzug`** mit einer Lebenslage. Die PLZ der Anfrage ist die neue Wohnung; der bisherige Wohnort ist der Ortsfakt `umzug.ort_alt`. Leistungen am alten Ort (Hundesteuer abmelden, Umzugskosten vom bisherigen Jobcenter) nutzen ihn als `ortsbezug`.
- **Abgeleitete Ortsvergleiche:** Ein abgeleiteter Fakt kann einen Ortsfakt mit dem Wohnort vergleichen (`ableitung`: `gleiche_gemeinde`, `gleicher_kreis`, `gleiches_land`). Fehlt der Ort, wird der Ort erfragt, nicht der abgeleitete Fakt. So braucht die Regel „nicht bei Umzug innerhalb derselben Gemeinde“ keine Sonderlogik.
- **Haushaltsfakten im Kern:** `bezieht_wohngeld`, `bezieht_buergergeld` und `arbeitsuchend_gemeldet` liegen im Kern, weil auch geringes Einkommen und Arbeit sie brauchen.
- **Nicht erfasst:** Jede Lebenslage kann bewusst nicht erfasste Themen mit Begründung nennen (`nicht_erfasst`). Der Bericht zeigt sie (Akzeptanzkriterium aus #41).
- **Nur echte Landesleistungen als „nur in anderen Ländern“:** Kommunale Varianten (z. B. Münchner Hundesteuer) erscheinen dort nicht mehr. Sonst stünde die Leistung einer Stadt bei allen anderen Gemeinden.
- **Akzeptanzkriterium Landesleistung (nachgeholt):** Die erste, allgemeine Suche fand keine Landesleistung, und zunächst stand für alle Länder `keine` mit einer gemeinsamen Sekundärquelle. Die Nachrecherche je Land fand das Begrüßungsgeld des Landes Bremen (150 € bei Zuzug für Studium oder Ausbildung). Es nutzt den abgeleiteten Fakt `umzug.gleiches_land`. Die übrigen 15 Länder haben `keine` mit je einer eigenen Quelle.

### 9. Umsetzung von Schritt 2: Geringes Einkommen (25.10.2026)

- **Fachmodul `einkommen`** mit der Lebenslage `geringes_einkommen` (Typ `situation`). Viele Regeln hängen am Bezug anderer Leistungen (Grundsicherungsgeld, Sozialhilfe, Wohngeld, Kinderzuschlag, Asylbewerberleistungen). Diese Angaben liegen im Kern, weil weitere Lebenslagen sie brauchen.
- **Geteilte Leistung:** Der Kinderzuschlag bleibt im Modul Familie und gehört zusätzlich zu `geringes_einkommen`. Damit er je Lebenslage passend fragt, gibt es den Regelknoten `{"lebenslage": …, "regel": …}`: Der Zweig gilt nur, wenn die Lebenslage gewählt ist, sonst als nicht erfüllt. Bei Geburt zählt das Neugeborene, sonst die Zahl der Kinder im Haushalt (`kinder_im_haushalt`). Die Prüfung stellt sicher, dass ein solcher Knoten nur Lebenslagen der eigenen Leistung nennt.
- **Grundsicherungsgeld:** Seit dem 1.7.2026 heißt das Bürgergeld Grundsicherungsgeld. Die ID des Fakts `bezieht_buergergeld` bleibt, damit gespeicherte Angaben gültig bleiben; Texte nennen beide Namen.
- **Akzeptanzkriterium Landesleistung erfüllt, alle Länder recherchiert:** Das Sozialticket ist eine Leistung ohne Bundesvariante mit Varianten in Berlin, Brandenburg, Hamburg, Hessen und NRW; Baden-Württemberg hat den Landesfamilienpass. Für die übrigen 10 Länder ist „keine“ mit Quelle eingetragen. Kommunale Angebote (München, Stadt Bremen, Saarbrücken) sind Gemeindevarianten und erscheinen andernorts nicht als „nur in anderen Ländern“.
- **Bedarfsrechnungen bleiben Prüfpunkte:** Ob Einkommen und Vermögen reichen, rechnen Jobcenter, Sozialamt, Wohngeldbehörde und Familienkasse. Die Engine liefert dafür höchstens „Unklar“ mit Hinweis auf den zuständigen Rechner oder die Stelle (ADR 0003).

### 10. Umsetzung von Schritt 3: Pflege (26.10.2026)

- **Fachmodul `pflege`** mit der Lebenslage `pflege` (Typ `situation`). Die nutzende Person ist entweder selbst pflegebedürftig oder pflegt einen Angehörigen (`pflege.rolle`). Die Fakten sprechen von „der pflegebedürftigen Person“ und von „Ihnen“ als Pflegeperson.
- **Keine Rollen:** Anders als in Abschnitt 7 vermutet, braucht Pflege keine Rollen `pflegebeduerftig` und `pflegeperson`. Rollen werten eine Regel je Person aus (Mutter, anderer Elternteil). Bei Pflege gibt es je Leistung genau eine berechtigte Person, die sich aus der Leistung ergibt; dafür reicht die Angabe `pflege.rolle` in der Regel.
- **Ort der pflegebedürftigen Person:** Landesleistungen (Landespflegegeld, Blindengeld, Pflegewohngeld) und die Hilfe zur Pflege haben den Ortsbezug `pflege.ort`. Der Fakt hat `nur_wenn` (nur bei Angehörigen). Die Engine wendet das auch auf den Ortsbezug an: Ist die Bedingung nicht erfüllt, gilt der Wohnort der Anfrage; ist sie offen, wird zuerst danach gefragt.
- **Ort unbekannt heißt offen, nicht „anderswo“:** Fehlt der Ort einer Leistung oder ist er „weiß nicht“, erschien eine Landesleistung bisher als „nur in anderen Ländern“, beim Blindengeld mit allen 16 Ländern. Jetzt nennt ein Hinweis die Landesleistungen, die sich ohne den Ort nicht prüfen lassen. Das betrifft auch andere Module mit Ortsbezug.
- **Blindengeld als Landesleistung in allen Ländern:** Es gibt keine Bundesvariante; jedes Land hat eine eigene Variante mit eigener Stelle und Quelle. Name und Höhe stehen im Hinweis der Variante, die Höhe nur, wenn eine Quelle sie nennt; widersprüchliche Angaben sind gekennzeichnet. Das Blindengeld gehört fachlich auch zu Behinderung und bekommt dort später eine zweite Lebenslage.
- **Akzeptanzkriterium Landesleistung erfüllt, alle Länder recherchiert:** Landespflegegeld nur in Bayern, Pflegewohngeld in NRW, Schleswig-Holstein und Mecklenburg-Vorpommern, Blindengeld überall. Damit ist die Abdeckung für alle 16 Länder `erfasst`.

### 11. Umsetzung von Schritt 4: Wohneigentum (26.10.2026)

- **Fachmodul `wohnen`** mit der Lebenslage `wohneigentum` (Typ `ereignis`): kaufen oder bauen, um selbst darin zu wohnen. Wohnberechtigungsschein und Mietwohnungen folgen als eigene Lebenslage im selben Modul; Schritt 4 bleibt dadurch klein genug für ein Review.
- **Ortsbezug Immobilie:** Wie in Abschnitt 3 geplant, ist der Ort der Immobilie ein eigener Ortsfakt (`wohnen.ort_immobilie`). Grunderwerbsteuer, Landesförderung und Hessengeld gelten dort; Bundesprogramme brauchen keinen Ort. Dafür war kein Umbau der Engine nötig.
- **Pflicht mit Landesvarianten:** Die Grunderwerbsteuer hat eine Bundesvariante (ohne Satz) und je Land eine Variante mit dem Steuersatz. Die speziellste Variante gewinnt; ohne Ort bleibt die Bundesangabe.
- **Einkommensgrenze je Kinderzahl:** Die KfW-Grenze (90.000 € plus 10.000 € je weiterem Kind) steht als Fallunterscheidung im Regelbaum, nicht als Rechenoperation. Bei mehr als fünf Kindern bleibt sie ein Prüfpunkt.
- **Akzeptanzkriterium Landesleistung erfüllt, alle Länder recherchiert:** Das Hessengeld ist eine Landesleistung ohne Gegenstück. Die Wohneigentumsförderung des Landes hat Varianten in 12 weiteren Ländern; Berlin und Mecklenburg-Vorpommern haben keine, Bremen nur in der Stadt Bremen (Gemeindevariante).

### 12. Umsetzung von Schritt 5: Ausbildung, Studium oder Meister (26.10.2026)

- **Fachmodul `bildung`** mit der Lebenslage `ausbildung_studium` (Typ `ereignis`). Schule folgt als eigene Lebenslage im selben Modul; ihre Leistungen (Schülerbeförderung, Lernmittel) sind je Land und Kreis verschieden und hätten den PR verdoppelt.
- **„Gibt es nur in manchen Ländern“:** Der Meisterbonus hat keine Bundesvariante. 14 Länder haben eine Variante mit eigener Stelle und Frist; Brandenburg und Schleswig-Holstein haben `keine` mit Quelle. Länder, die nur Handwerksmeister fördern, fragen danach; die anderen prüfen das DQR-Niveau als Prüfpunkt.
- **Fristen ab einem Datumsfakt:** Die Antragsfristen der Prämien rechnen ab `bildung.pruefung_datum` (Abschnitt 7: Fristen können sich auf jeden Datumsfakt beziehen). Weil eine fehlende Bezugsgröße einer Frist keine Rückfrage auslöst, stehen Prüfung und Datum als bedingte Einstiegsfragen in der Lebenslage (`nur_wenn`: nur bei Aufstiegsfortbildung bzw. bestandener Prüfung).
- **Wohnort statt Arbeitsort:** Viele Prämien gelten bei Wohnsitz *oder* Arbeitsort im Land. Geprüft wird der Wohnort; der Hinweis der Variante nennt den Arbeitsort. Ein eigener Ortsfakt für den Arbeitsort folgt mit dem Modul Arbeit.

### 13. Umsetzung von Schritt 6, Teil 1: Behinderung (26.10.2026)

- **Fachmodul `behinderung`** mit der Lebenslage `behinderung` (Typ `situation`). Schritt 6 wird in einzelne PRs je Lebenslage geteilt (Behinderung, dann Arbeit, Heirat, Ruhestand, Todesfall, Schule).
- **Zuständigkeit je Land als Variante:** Feststellung und Wertmarke sind Bundesrecht, aber jedes Land bestimmt die Behörde. Statt einer Landesleistung gibt es je Land eine Variante, die sich nur in der Zuständigkeit und Quelle unterscheidet. So nennt der Bericht z. B. das ZBFS in Bayern und die kreisfreie Stadt in NRW.
- **Geteilter Fakt statt Doppelung:** Das Merkzeichen Bl ist der Fakt `pflege.blind` aus dem Modul Pflege; Behinderung importiert ihn (`importiert_fakten`). Die Frage ist neutral formuliert. Das Blindengeld der Länder gehört zu beiden Lebenslagen.
- **Ortsbezug mit Bedingung außerhalb der Lebenslage (Engine):** Das Blindengeld hat den Ortsbezug `pflege.ort` mit `nur_wenn` auf `pflege.rolle`. Gehört diese Bedingung nicht zu den Einstiegsfragen der gewählten Lebenslagen, gilt jetzt der Wohnort, statt nach der Pflege zu fragen. Wer Pflege mitwählt, wird wie bisher gefragt.

### 14. Umsetzung von Schritt 6, Teil 2: Arbeit (26.10.2026)

- **Fachmodul `arbeit`** mit zwei Lebenslagen: `jobverlust` und `selbststaendig` (beide `ereignis`). Ein Modul, weil Arbeitsagentur, Jobcenter und Kammern in beiden vorkommen; die Lebenslagen bleiben getrennt wählbar.
- **Frist mit „nicht vor“ (Engine):** § 38 SGB III verlangt die Meldung drei Monate vor dem Ende, bei kürzerem Vorlauf drei Tage nach Kenntnis. Eine Frist kann jetzt `nicht_vor: {bezug, tage}` haben; es gilt das spätere Datum. Ohne Kündigungsdatum bleibt die Drei-Monats-Frist. Die Prüfung verlangt einen erlaubten Datumsfakt.
- **Bedingte Datumsfragen:** Zugang der Kündigung und Datum der Insolvenz sind Einstiegsfragen mit `nur_wenn` auf den Grund; gefragt wird nur, was zum Grund passt.
- **Geteilte Leistung:** Das Grundsicherungsgeld (Modul Einkommen) gehört auch zu `jobverlust`.
- **Landesleistungen:** Bei Jobverlust nur Beratung (Art `information`), weil Geldleistungen Bundesrecht sind; bei Gründung die Meistergründungsprämien. Gründerkredite der Landesförderbanken stehen unter „nicht erfasst“.

### 15. Umsetzung von Schritt 6, Teil 3: Todesfall (26.10.2026)

- **Fachmodul `todesfall`** mit der Lebenslage `todesfall` (`ereignis`).
- **Landesrecht als Landesleistung:** „Bestattung veranlassen“ (Art `pflicht`) hat keine Bundesvariante, sondern je Land eine Variante mit der Frist aus dem Bestattungsgesetz. Damit greift die bestehende Abdeckungsprüfung (`erfasst` braucht eine Landesleistung). Geldleistungen der Länder gibt es im Todesfall nach der Recherche nicht.
- **Ort ist der Sterbeort:** Die Leistung hat den Ortsbezug `todesfall.sterbeort` (Einstiegsfrage). Wer in Köln wohnt und dessen Vater in München gestorben ist, bekommt die bayerische Frist.
- **Kein falsches Datum:** Wo die Frist Werktage zählt (Bayern, Sachsen) oder es keine feste Frist für alle Fälle gibt, steht die Frist nur als Text. Die Anzeigefrist beim Standesamt (dritter Werktag) wird vorsichtig als dritter Kalendertag berechnet; der Text sagt das.
- **Bedingte Fragen:** Das Datum der Kenntnis vom Erbe wird nur gefragt, wenn das Ausschlagen erwogen wird; der Rentenbezug nur bei Ehepartnern.

## Folgen

- Neue Lebenslagen sind überwiegend Datenarbeit. Code ändert sich nur, wenn ein neues Merkmal für alle gebraucht wird.
- Der Kernumbau ändert das Datenformat (`lebenslagen` statt `ereignisse`, `fuer` als Rollenliste, Einstiegsfragen statt `grunddaten`). Faktennamen, CLI (`-f mutter.…`) und gespeicherte Angaben bleiben gültig (siehe Abschnitt 7). Alte Datenfelder lehnt der Loader mit einem Hinweis auf den neuen Namen ab.
- Die Fachmodule enthalten schon jetzt Synonyme und Beispielsätze, die erst in Phase 3 voll genutzt werden. Das ist bewusster Vorlauf: Es ist günstiger, sie beim Erfassen einer Lebenslage mitzuschreiben als nachträglich.
- Entschieden am 25.10.2026: Geburt gehört zum Fachmodul Familie; die Reihenfolge in Abschnitt 6 gilt.
- Offene Punkte: genaue Rollenliste und Umgang mit mehreren Kindern; Leistungsschlüssel aus FIM/LeiKa als stabile IDs (Katalog-Schritt in #41).
