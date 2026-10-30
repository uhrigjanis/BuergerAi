# ADR 0009: LLM-Schicht – Rollen, Grenzen, Datenschutz und Anbieter

**Status:** angenommen · **Datum:** 30.10.2026 · **Issue:** #72 (Teil von #71)

## Kontext

Phase 3 (#71) soll Freitext verstehen: „Wir bekommen im März ein Kind und ziehen nach Freising.“ Ein LLM erkennt die Lebenslagen, entnimmt die Angaben und formuliert die Antwort. Bevor Code entsteht, legt dieses ADR fest, was das LLM darf, wie mit den Daten umgegangen wird und welcher Anbieter genutzt wird.

Rahmenbedingungen:

- Ob ein Anspruch besteht, entscheidet allein die Regel-Engine (#1, ADR 0003, ADR 0008 §1 und §5).
- Freitexte können Gesundheitsdaten enthalten (Schwangerschaft, Pflegegrad, Behinderung). Das sind besondere Kategorien nach Art. 9 DSGVO.
- Der Kern hat keine Laufzeitabhängigkeiten (ADR 0002). CI läuft ohne Netz und ohne Schlüssel.
- Vorgabe für den Anbieter: **Verarbeitung in der EU und günstig.** Das Projekt hat kein Budget für feste Serverkosten.

## Entscheidung

### 1. Rollen des LLM

Das LLM hat genau drei Aufgaben. Jede Ausgabe wird deterministisch geprüft, bevor sie wirkt. Was die Prüfung nicht besteht, wird verworfen, nicht repariert.

| Rolle | Eingabe | Ausgabe | Prüfung |
|---|---|---|---|
| **Router** | Freitext, Steckbriefe der Lebenslagen (Synonyme, Beispielsätze, Abgrenzungen) | Liste von Lebenslagen-IDs | jede ID steht im Katalog (#76) |
| **Extraktion** | Freitext, JSON-Schema der Fakten der erkannten Module | Fakten-IDs mit Werten | Schema und `parse_wert`; unbekannte IDs und Werte werden verworfen (#75, #77) |
| **Formulierung** | strukturierter Bericht (`/api/bericht`) | verständlicher Antworttext | Leistungen, Beträge, Fristen und Stellen im Text müssen im Bericht stehen (#78) |

Den Ablauf steuert deterministischer Code (ADR 0008 §5): Router, dann Extraktion je Modul, dann Engine, dann Bericht. Rückfragen kommen aus der Engine und erscheinen als Formularfelder, nicht als LLM-Dialog.

Erkannte Angaben bestätigt der Nutzer, bevor sie in den Bericht eingehen („Wir haben verstanden: …“, #79).

### 2. Grenzen: „Orchestrator steuern“ heißt aus dem Katalog wählen

- Das LLM wählt nur aus Einträgen des Katalogs: Lebenslagen, Fakten-IDs, Auswahlwerte. Freie Aktionen oder Werkzeuge außerhalb des Katalogs gibt es nicht. Es gibt keine Websuche, keinen Code, keine Dateizugriffe.
- Das LLM entscheidet nie über Ansprüche. Es nennt keine Leistung, keinen Betrag, keine Frist und keine Stelle, die nicht im Bericht steht.
- Das LLM schreibt keine Regeln und ändert keine Daten unter `data/`.
- Eingaben werden als Daten behandelt, nicht als Anweisungen. Eine Prompt-Injection im Freitext kann wegen der Prüfungen höchstens falsche Angaben vorschlagen, die der Nutzer dann sieht und bestätigen muss.

### 3. Datenschutz

- **Datenminimierung:** An das Modell geht nur der Freitext und der Ausschnitt des Katalogs, der für die Aufgabe nötig ist. Keine PLZ, keine IP-Adresse, keine Nutzerkennung. Für die Formulierung geht der Bericht ohne Freitext an das Modell.
- **Keine Speicherung von Freitexten** auf unserer Seite. Die Web-API bleibt zustandslos (ADR 0008 §4). Freitexte stehen weder in Dateien noch in Logs.
- **Logging ohne personenbezogene Daten:** Erlaubt sind Zeitpunkt, Aufgabe (Router, Extraktion, Formulierung), Modell, Tokenzahlen, Dauer, Ergebnis der Prüfung (z. B. „2 Fakten verworfen“) und erkannte IDs ohne Werte. Nicht erlaubt sind Freitext, Faktenwerte und Antworttexte (#80).
- **Hinweis an die Nutzer** vor der Freitext-Eingabe: dass ein KI-Dienst in der EU den Text verarbeitet, dass keine Namen oder Diagnosen nötig sind, und dass das Formular ohne KI weiter zur Verfügung steht. Die Freitext-Eingabe ist freiwillig. Wer sie nutzt, willigt ausdrücklich ein (Art. 9 Abs. 2 lit. a DSGVO).
- **Auftragsverarbeitung:** Vor dem Betrieb wird ein Vertrag zur Auftragsverarbeitung (Art. 28 DSGVO) mit dem Anbieter abgeschlossen. Training auf unseren Daten muss ausgeschlossen sein. Prompt-Caching ist erlaubt, weil der Cache nur den festen Prompt-Anfang (Katalog) betrifft, nicht den Freitext.
- **Bezug zu #6 (EU-Hosting):** Die Modellaufrufe laufen in der EU (Abschnitt 5). Für den Webserver gilt dieselbe Vorgabe.

### 4. Abhängigkeiten: Ausnahme zu ADR 0002

- Der LLM-Client kommt als optionales Extra `[llm]` in `pyproject.toml`. `dependencies` bleibt leer.
- Code, der das Paket des Anbieters importiert, liegt nur im Adapter (`buergerai.llm`, #74). Der Import steht in der Funktion, nicht oben im Modul, damit der Kern ohne Extra lädt.
- Kern, Tests und CI laufen ohne Extra, ohne Netz und ohne Schlüssel. Tests nutzen ein Fake-Modell (#74).

### 5. Anbieter

**Gewählt: Claude Haiku 5.5 über Google Cloud Vertex AI, Multi-Region `eu`.** Mistral Small (La Plateforme, EU) wird in der Evaluation als Zweitanbieter mitgemessen. Der Adapter (#74) kapselt den Anbieter, ein Wechsel ist eine Konfigurationsänderung.

Vergleich (Preise je Million Tokens, Eingabe / Ausgabe, Stand 30.10.2026):

| Option | Verarbeitung | Preis | Bewertung |
|---|---|---|---|
| **Claude Haiku 5.5 auf Vertex AI, `eu`** | EU (Multi-Region, Google als Auftragsverarbeiter) | $0,11 / $0,55 (Grundpreis $0,10 / $0,50 plus 10 % für Multi-Region) | **gewählt:** günstig, EU, kleines Modell reicht für alle drei Rollen (#71) |
| Claude Haiku 5.5 auf Amazon Bedrock, EU-Profil | EU (Routing über mehrere EU-Regionen; in Frankfurt kein eigener Endpunkt) | Grundpreis plus 10 % für regionales Routing | gleichwertig, falls ein AWS-Konto bevorzugt wird; Haiku 5.5 ist auf Bedrock laut Anthropic-Doku noch nicht für alle Kunden freigeschaltet |
| Mistral Small über La Plateforme | EU, Anbieter mit Sitz in der EU | etwa $0,15–0,20 / $0,60 (Quellen uneinheitlich, vor Nutzung auf mistral.ai prüfen); kostenlos im Plan „Experiment“ (Abschnitt 5a) | **für Entwicklung und Evaluation (Abschnitt 5a), Zweitanbieter:** ähnlich günstig, kein US-Konzern; Training auf API-Daten muss abgeschaltet werden |
| Anthropic-API direkt | global oder USA (`inference_geo` kennt nur `global` und `us`) | $0,10 / $0,50 | verworfen: keine EU-Verarbeitung |
| Selbst gehostetes Open-Weight-Modell (Ollama/vLLM) bei einem EU-Hoster | EU, volle Kontrolle | GPU-Server laufen dauerhaft, grob mehrere hundert Euro im Monat | verworfen: feste Kosten weit über den Tokenkosten, Betriebsaufwand |
| IONOS / STACKIT (EU-Cloud mit Open-Weight-Modellen) | EU, deutsche Anbieter | nutzungsabhängig | Alternative, falls ein US-Konzern als Auftragsverarbeiter ausgeschlossen werden soll; Qualität der verfügbaren Modelle wird erst geprüft, wenn das nötig wird |

**Kostenschätzung:** Eine Sitzung braucht etwa drei Aufrufe (Router, Extraktion, Formulierung) mit zusammen rund 10.000 Eingabe- und 1.000 Ausgabetokens. Auf Vertex `eu` sind das ohne Caching etwa 0,17 US-Cent. 10.000 Sitzungen im Monat kosten damit etwa 17 US-Dollar, mit Prompt-Caching des Katalogs weniger. Gemessen wird das in #80.

**Begründung:**

- Haiku 5.5 ist das günstigste Modell im Vergleich und für Routing und Extraktion gedacht. Die Mehrkosten für EU-Verarbeitung sind 10 %, also wenige Dollar im Monat.
- Vertex statt Bedrock, weil Haiku 5.5 auf Vertex in der EU-Multi-Region angeboten wird und auf Bedrock noch nicht allgemein freigeschaltet ist. Ist das später anders, ist Bedrock gleichwertig.
- Ein selbst gehostetes Modell kostet schon im Leerlauf mehr als der erwartete Jahresverbrauch über eine API.
- Restrisiko: Google ist ein US-Konzern (CLOUD Act). Die Daten werden in der EU verarbeitet, aber nicht von einem EU-Unternehmen. Deshalb läuft Mistral in der Evaluation mit. Ist die Qualität gleich, kann der Wechsel ohne Codeänderung erfolgen.

**Vor Inbetriebnahme prüfen** (nicht vor der Entwicklung, weil Tests mit dem Fake-Modell laufen):

- Haiku 5.5 im Model Garden für die Region `eu` freigeschaltet, Preis bestätigt.
- Auftragsverarbeitungsvertrag, kein Training auf Kundendaten, Aufbewahrung der Anfragen.
- Ob Prompt-Caching in der Multi-Region `eu` verfügbar ist.

### 5a. Entwicklung und Evaluation: Mistral La Plateforme, Plan „Experiment“ (kostenlos)

Für die Entwicklung (#75 bis #79) und die Evaluation (#73) wird der kostenlose Plan „Experiment“ von Mistral genutzt, mit Mistral Small. Mistral ist ein EU-Unternehmen und verarbeitet in der EU. Damit braucht die Entwicklung kein Budget, und Mistral ist als Zweitanbieter von Anfang an im Adapter.

Regeln für den kostenlosen Plan:

- **Nur ausgedachte Texte:** Evaluationsfälle (#73), Testtexte, eigene Probeeingaben. Nie Texte echter Nutzer, nie echte Gesundheitsdaten. Auf diesem Plan nutzt Mistral Eingaben und Ausgaben standardmäßig zum Training.
- **Training abschalten:** In der Admin-Konsole unter Privacy die Weitergabe zur Verbesserung („Anonymous improvement data“) ausschalten, bevor der Schlüssel genutzt wird.
- **Nicht für den Betrieb:** Der Plan ist zum Ausprobieren gedacht, hat enge Limits (etwa 1 Anfrage pro Sekunde, bei Last nachrangig) und keinen Vertrag zur Auftragsverarbeitung für unseren Zweck. Die Web-Oberfläche mit echten Nutzern läuft nur mit dem Anbieter aus Abschnitt 5 oder einem bezahlten Plan.
- **Schlüssel nur lokal:** Der API-Schlüssel steht in einer Umgebungsvariablen, nie im Repository. CI bekommt keinen Schlüssel und läuft weiter mit dem Fake-Modell (Abschnitt 4).
- **Limits einplanen:** Das Bewertungsskript (#73) wartet zwischen Aufrufen und wiederholt bei HTTP 429. Ein Lauf über alle Fälle darf daher einige Minuten dauern.

Haiku 5.5 wird vor dem Betrieb mit demselben Evaluationssatz gemessen. Ein Lauf kostet wenige Cent.

**Was die Wahl ändern kann:** Die Evaluation (#73) zeigt, dass Haiku 5.5 die Qualitätsgrenze nicht erreicht oder Mistral gleich gut ist; die Datenschutzprüfung schließt US-Anbieter aus; die Kosten in #80 liegen deutlich über der Schätzung.

### 6. Fallback

Ohne LLM läuft alles wie heute: Lebenslagen-Auswahl, Stichwortsuche über Synonyme (`./bai lebenslagen --suche`) und Formular. Das gilt, wenn kein Schlüssel konfiguriert ist, das Extra nicht installiert ist, der Anbieter ausfällt oder nicht rechtzeitig antwortet, die Ausgabe die Prüfung nicht besteht oder das Modell ablehnt. Der Nutzer sieht dann einen Hinweis und das Formular, keine Fehlerseite.

## Folgen

- Neue Anforderungen `ANF-LLM-*` im Katalog. Jetzt prüfbar ist die Abhängigkeitsregel (ANF-LLM-01). Die übrigen Regeln aus diesem ADR werden mit den Issues #74 bis #80 als Anforderungen mit Tests ergänzt, damit jede Anforderung einen Test hat (ANF-QS-01).
- ADR 0002 verweist auf die Ausnahme in Abschnitt 4.
- Der Anbieter steht in der Konfiguration, nicht im Code. Schlüssel und Projekt-ID kommen aus Umgebungsvariablen.
- Der Adapter (#74) unterstützt zuerst Mistral (Entwicklung, Abschnitt 5a), dann Vertex AI (Betrieb, Abschnitt 5).
- Offene Punkte: Text des Hinweises und der Einwilligung; Hosting des Webservers in der EU (#6).
