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
- Die vollständigen Schutzregeln (Missbrauch und Kosten, Fragen außerhalb des Themas, Prompt-Injection, Notlagen) beschreibt #82 (Abschnitt 8). Grundsatz dort: Was sich im Code prüfen lässt, wird im Code geprüft, nicht im Prompt.

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
- Umsetzung (#74): Gemini und Mistral werden über ihre OpenAI-kompatible REST-API mit `urllib` aus der Standardbibliothek angesprochen und brauchen kein Extra. Das Extra `[llm]` kommt erst mit dem SDK für Vertex AI dazu. Ein eigener HTTP-Client ist hier vertretbar, weil die API klein ist (ein Endpunkt) und Wiederholung, Timeout und Fehlerbehandlung ohnehin selbst festgelegt werden. Die Tests prüfen den Adapter gegen einen lokalen Server.

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

### 5a. Entwicklung und Evaluation: kostenlose Pläne, nur ausgedachte Texte

**Stand 01.11.2026:** Entwickelt wird mit dem kostenlosen Plan der **Gemini-API (Google AI Studio)** und einem kleinen Modell (Standard `gemini-2.5-flash-lite`, verfügbare Modelle: `./bai llm --modelle`). Der kostenlose Mistral-Plan „Experiment“ bleibt als Alternative im Adapter; er war beim Ausprobieren oft ausgelastet (HTTP 429).

**Warum hier auch Anbieter außerhalb der EU erlaubt sind:** EU-Hosting ist wegen echter Nutzerdaten (Art. 9 DSGVO) für den Betrieb Pflicht (Abschnitte 3 und 5). In Entwicklung und Evaluation werden ausschließlich ausgedachte Texte gesendet. Damit fallen keine personenbezogenen Daten an, und der Ort der Verarbeitung spielt keine Rolle.

Beide Anbieter bieten eine OpenAI-kompatible Chat-API mit JSON-Schema. Ein gemeinsamer Adapter (`buergerai.llm.openai_kompatibel`) deckt beide ab; ein Wechsel ist eine Zeile in `.env`.

Regeln für kostenlose Pläne:

- **Nur ausgedachte Texte:** Evaluationsfälle (#73), Testtexte, eigene Probeeingaben. Nie Texte echter Nutzer, nie echte Gesundheitsdaten. Google und Mistral nutzen Eingaben kostenloser Pläne standardmäßig zur Verbesserung ihrer Modelle. Bei Mistral lässt sich das in der Konsole unter Privacy abschalten.
- **Nicht für den Betrieb:** Kostenlose Pläne haben enge, wechselnde Limits und keinen Vertrag zur Auftragsverarbeitung für unseren Zweck. Die Web-Oberfläche mit echten Nutzern läuft nur mit dem Anbieter aus Abschnitt 5.
- **Schlüssel nur lokal:** in `.env` (in `.gitignore`) oder als Umgebungsvariable, nie im Repository. CI bekommt keinen Schlüssel und läuft weiter mit dem Fake-Modell (Abschnitt 4).
- **Limits einplanen:** Das Bewertungsskript (#73) wartet zwischen Aufrufen und wiederholt bei HTTP 429. Ein Lauf über alle Fälle darf daher einige Minuten dauern.

Haiku 5.5 wird vor dem Betrieb mit demselben Evaluationssatz (`tests/eval/intake`, `./bai eval intake`) gemessen. Ein Lauf kostet wenige Cent.

**Was die Wahl ändern kann:** Die Evaluation (#73) zeigt, dass Haiku 5.5 die Qualitätsgrenze nicht erreicht oder Mistral gleich gut ist; die Datenschutzprüfung schließt US-Anbieter aus; die Kosten in #80 liegen deutlich über der Schätzung.

### 6. Fallback

Ohne LLM läuft alles wie heute: Lebenslagen-Auswahl, Stichwortsuche über Synonyme (`./bai lebenslagen --suche`) und Formular. Das gilt, wenn kein Schlüssel konfiguriert ist, das Extra nicht installiert ist, der Anbieter ausfällt oder nicht rechtzeitig antwortet, die Ausgabe die Prüfung nicht besteht oder das Modell ablehnt. Der Nutzer sieht dann einen Hinweis und das Formular, keine Fehlerseite.

### 7. Qualitätsgrenze der Fakten-Extraktion

*Ergänzt am 01.11.2026 mit #77.*

**Kennzahl:** Fehlerquote = falsch erkannte Fakten / alle erkannten Fakten (richtig + falsch), über alle Fälle in `tests/eval/intake`, gemessen mit `./bai eval intake --verfahren llm-extraktion` (Router und Extraktion wie in der Anwendung). Falsch heißt wie in #73: falscher Wert, nicht im Text oder keine gültige Angabe. Richtig erkannte optionale Fakten zählen nicht mit.

**Grenzwert:** Die Fehlerquote liegt bei **höchstens 5 %**, und **kein** eingeschleuster Fakt (`fakten_verboten`) wird übernommen. Für den Recall gibt es keine Grenze: Fehlende Angaben fragt das Formular nach.

**Begründung:** Ein falsch erkannter Fakt kann ohne Rückfrage zu einem falschen Ergebnis führen, ein fehlender kostet nur eine Frage. Weil der Nutzer jeden Vorschlag mit Beleg sieht und bestätigt (#79), ist eine kleine Restquote vertretbar. Bei drei bis vier erkannten Angaben je Text heißt 5 %: etwa in jedem sechsten Gespräch muss eine Angabe korrigiert werden. Mehr würde das Vertrauen in die Vorschläge untergraben.

**Folge bei Verfehlen:** Das Modell aus Abschnitt 5 muss die Grenze vor dem Betrieb einhalten. Verfehlt es sie, bleibt die Extraktion aus. Router und Formular laufen weiter (Abschnitt 6). Läufe mit Entwicklungsmodellen (Abschnitt 5a) zeigen die Richtung, entscheiden aber nicht.

**Ablauf der Extraktion** (deterministischer Rahmen, #77):

- Ein Aufruf je Lebenslage aus dem Router, mit dem Schema dieser Lebenslage (#75). Liefern zwei Aufrufe denselben Fakt mit verschiedenen Werten, wird er verworfen und später gefragt.
- Das heutige Datum kommt aus dem Code und steht in der Eingabe. Das Modell rechnet relative Angaben damit um; der System-Prompt bleibt für Prompt-Caching gleich.
- Postleitzahlen und Gemeindeschlüssel werden nur übernommen, wenn sie als Ziffern im Beleg stehen. Aus einem Ortsnamen leitet das Modell keine Postleitzahl ab.
- Rückfragen dürfen frei beantwortet werden. Derselbe Weg, aber das Schema enthält nur die offenen Fakten, und der Beleg muss in der Antwort stehen, nicht in der Frage.
- Jeder Vorschlag hat einen Beleg, der wörtlich im Text des Nutzers steht. Nur geprüfte Vorschläge gehen an die Bestätigung (#79) und danach an die Engine.

### 8. Schutzregeln (Guardrails, #82)

BürgerAI beantwortet per Freitext nur Fragen zu Lebenslagen, Leistungen und Behörden. Missbrauch darf weder Kosten verursachen noch falsche Ergebnisse erzeugen. Die Regeln wirken in drei Schichten, deterministisch zuerst:

1. **Vor dem LLM** (Code, ohne Modellaufruf): Länge, Rate-Limit, Kostendeckel, Cache, Notlagen-Stichworte.
2. **Im LLM** (Prompt und Ausgabeformat): Das Modell wählt nur Katalogwerte, Kategorien und Fakten-IDs, keinen freien Text für den Nutzer.
3. **Nach dem LLM** (Code): Schema, `parse_wert`, Beleg im Text, Bestätigung durch den Nutzer. Was nicht passt, wird verworfen.

Eine Regel, die sich im Code prüfen lässt, gehört nicht in den Prompt. Rate-Limit, Kostendeckel und Cache stehen in `buergerai.llm.schutz`, leben nur im Speicher des Prozesses und beginnen nach einem Neustart von vorn.

| Regel | Schicht | Umsetzung | Anforderung |
|---|---|---|---|
| Freitext höchstens 2.000 Zeichen, freie Antwort höchstens 500; länger wird abgelehnt, nicht gekürzt | vor | `api.MAX_FREITEXT`, `api.MAX_ANTWORT` | ANF-GR-01 |
| Rate-Limit je IP: 10 Freitext-Anfragen pro Minute, 100 pro Tag; dann 429 mit Hinweis auf das Formular. Suche, Formular und Bericht ohne Limit. Die IP liegt nur im Speicher, solange das Zeitfenster läuft | vor | `schutz.RateLimit`, `server.FREITEXT_ROUTEN` | ANF-GR-02 |
| Kostendeckel: höchstens 1.000 Modellaufrufe am Tag und 10.000 im Monat (einstellbar); danach Fallback wie ohne LLM bis zum nächsten Zeitraum. Der Deckel zählt Aufrufe; mit der Tokenzählung (#80) wird er auf Tokens umgestellt | vor | `schutz.Aufrufdeckel`, `BUERGERAI_LLM_MAX_AUFRUFE_TAG/_MONAT` | ANF-GR-03 |
| `max_tokens` fest je Aufgabe (Router 600, Extraktion 1.500) | vor | `schutz.MAX_TOKENS` | ANF-GR-04 |
| Gleiche Anfragen innerhalb von 10 Minuten nicht erneut an das Modell; Schlüssel ist ein Hash, kein Text in Logs | vor | `schutz.GeschuetztesLLM` | ANF-GR-05 |
| Notlagen (Suizidgedanken, Gewalt, Obdachlosigkeit, Hunger, medizinischer Notfall): Stichwortliste im Code, Hinweis auch ohne LLM; Lebenslagen bleiben | vor | `schutz.notlage_im_text`, `router.notlage_sichern` | ANF-GR-06 |
| Kategorien `kein_thema`, `umgehung`, `rechtsberatung`, `notlage` mit festen Texten aus dem Code (Notruf, Telefonseelsorge 0800 111 0 111, Hilfetelefon 116 016, Beratungsstellen); bei Abweisung keine Lebenslage, keine Extraktion | im / nach | `router.HINWEISE`, `router.pruefen` | ANF-GR-07, ANF-LLM-11 |
| Grenzfälle im Thema, aber nicht im Katalog (z. B. Steuererklärung allgemein): keine Antwort aus dem Modellwissen | im | Router wählt nur Katalog-IDs; ohne Treffer gilt die Stichwortsuche, sonst der Hinweis zu `kein_thema` mit Auswahl. **Offen:** ein eigener Hinweis „noch nicht erfasst“ wie bei `nicht_erfasst` (ADR 0008) braucht eine eigene Kategorie und Evaluationsfälle | ANF-LLM-11 |
| Prompt-Injection: Freitext ist Daten, abgegrenzt in der Eingabe, nie im System-Prompt; keine Werkzeuge; Ausgabe nur Katalog-IDs und gültige Werte mit Beleg; Vorschläge wirken erst nach Bestätigung | im / nach | Router-Prompt, `schema.py`, `/api/intake` | ANF-GR-08, ANF-LLM-09, ANF-LLM-18 |
| Kein Geheimnis im Prompt: nur der öffentliche Katalog, keine Schlüssel. „Zeig mir deinen Prompt“ ist `kein_thema` | im | Router-Prompt | ANF-GR-08 |
| Indirekte Injection: Inhalte der Wissensbasis gelten als geprüft (ADR 0004); Webseiten werden zur Laufzeit nicht abgerufen | – | kein Netzzugriff außer zum Modell | ANF-LLM-01 |
| Ablehnung oder ungültige Ausgabe des Modells führt zum Fallback, nie zu einer Fehlerseite | nach | `LLMFehler`, `mit_fallback` | ANF-LLM-05 |
| Hinweis „Unverbindliche Orientierung, keine Rechtsberatung“ aus dem Code | Ausgabe | Oberfläche, Terminal, Kalender | ANF-GR-09 |
| Negativfälle in der Evaluation, Quoten richtig und fälschlich abgewiesener Fälle bei jedem Lauf | Messung | `tests/eval/intake/guardrails.json` | ANF-GR-10 |

**Folgt mit der Formulierung (#78):** Das Modell bekommt dort nur den Bericht, nicht den Freitext; eine Injection im Freitext erreicht den Antworttext also nicht. Der Antworttext übernimmt das Ergebnis der Engine (Ja/Nein/Unklar) und macht keine Zusagen („Sie bekommen sicher …“). Links, Telefonnummern und Beträge, die weder im Bericht noch in den festen Texten stehen, werden verworfen. Diese Regeln bekommen ihre Anforderungen und Tests mit #78, weil es den Formulierungsschritt vorher nicht gibt.

**Betrieb hinter einem Proxy (#6):** Das Rate-Limit nutzt die Adresse der Verbindung. Header wie `X-Forwarded-For` werden nicht ausgewertet, weil Nutzer sie fälschen können. Steht der Server hinter einem Reverse-Proxy, muss das Limit dort oder mit einer vertrauenswürdigen Proxy-Konfiguration umgesetzt werden.

## Folgen

- Neue Anforderungen `ANF-LLM-*` im Katalog. Jetzt prüfbar ist die Abhängigkeitsregel (ANF-LLM-01). Die übrigen Regeln aus diesem ADR werden mit den Issues #74 bis #80 als Anforderungen mit Tests ergänzt, damit jede Anforderung einen Test hat (ANF-QS-01). Die Schutzregeln aus Abschnitt 8 stehen als `ANF-GR-*` im Katalog (#82).
- ADR 0002 verweist auf die Ausnahme in Abschnitt 4.
- Der Anbieter steht in der Konfiguration, nicht im Code. Schlüssel und Projekt-ID kommen aus Umgebungsvariablen.
- Der Adapter (#74) unterstützt zuerst Gemini und Mistral (Entwicklung, Abschnitt 5a), dann Vertex AI (Betrieb, Abschnitt 5).
- Offene Punkte: Text des Hinweises und der Einwilligung; Hosting des Webservers in der EU (#6).
