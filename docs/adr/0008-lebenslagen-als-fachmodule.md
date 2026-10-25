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

## Folgen

- Neue Lebenslagen sind überwiegend Datenarbeit. Code ändert sich nur, wenn ein neues Merkmal für alle gebraucht wird.
- Der Kernumbau ändert das Datenformat (`lebenslagen` statt `ereignisse`, `fuer` als Rollenliste, Einstiegsfragen statt `grunddaten`). Faktennamen, CLI (`-f mutter.…`) und gespeicherte Angaben bleiben gültig (siehe Abschnitt 7). Alte Datenfelder lehnt der Loader mit einem Hinweis auf den neuen Namen ab.
- Die Fachmodule enthalten schon jetzt Synonyme und Beispielsätze, die erst in Phase 3 voll genutzt werden. Das ist bewusster Vorlauf: Es ist günstiger, sie beim Erfassen einer Lebenslage mitzuschreiben als nachträglich.
- Entschieden am 25.10.2026: Geburt gehört zum Fachmodul Familie; die Reihenfolge in Abschnitt 6 gilt.
- Offene Punkte: genaue Rollenliste und Umgang mit mehreren Kindern; Leistungsschlüssel aus FIM/LeiKa als stabile IDs (Katalog-Schritt in #41).
