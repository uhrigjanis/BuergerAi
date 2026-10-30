# Prüfprotokolle

Je Quelle ein Protokoll `<quelle-id>.md`: Was behauptet die Wissensbasis, was steht im Volltext der Quelle, stimmt es überein? Das Protokoll ist die Grundlage für die Abnahme durch einen Menschen (ADR 0004, ANF-QS-02) und die Vorlage für die Pflege in Phase 4.

## Ablauf

1. **Verwendungen ansehen:** `./bai quellen --verwendung <id>` listet jede Bedingung, Frist, jeden Betrag, jede Zuständigkeit und jedes Gebiet, das die Quelle zitiert, mit Datei und JSON-Pfad.
2. **Gerüst anlegen:** `./bai quellen --protokoll <id>` schreibt `docs/pruefprotokolle/<id>.md` nach der Vorlage unten, die Tabelle ist mit allen Verwendungen vorbefüllt. Ein vorhandenes Protokoll wird nicht überschrieben.
3. **Volltext lesen:** aktuelle Fassung abrufen. Bei Gesetzen „zuletzt geändert durch …“, bei Behördenseiten das Abrufdatum eintragen.
4. **Abgleichen:** je Zeile den Wortlaut (mit Absatz) zitieren und das Ergebnis setzen. Bei Fristen auch Beginn, Dauer, „Tag zählt mit?“ und das Ende an Wochenenden prüfen; bei Beträgen den Gültigkeitszeitraum.
5. **Bei Abweichung:** Daten oder Regel korrigieren und einen Test oder ein Szenario ergänzen, das den Fehler gefunden hätte. Unter „Abweichungen und Folgeaktionen“ den PR nennen.
6. **Verlinken:** In der Quelle (`data/**/quellen`) in `notiz` auf `docs/pruefprotokolle/<id>.md` verweisen und höchstens `teilweise` setzen. `./bai daten` warnt bei geprüften Quellen ohne verlinktes Protokoll.
7. `./bai daten && ./bai szenarien --pruefen && python -m pytest`

**Claude setzt nie `verifiziert`,** höchstens `teilweise` mit vollständigem Protokoll.

Nur die Quellen der Pilotregion (Phase 1, Issue #45): `./bai quellen --phase1 --offen`

## Abnahme durch einen Menschen

Protokoll lesen, Zitate an der Quelle nachsehen, dann:

```
./bai quellen --abnehmen <id> --von "Vorname Nachname"
```

Der Befehl setzt `pruefstatus: verifiziert`, `geprueft_am` (heute, oder `--am TT.MM.JJJJ` bzw. `--am JJJJ-MM-TT`) und `geprueft_von` und trägt die Abnahme im Protokoll ein. Er ändert in der Datendatei nur diese Felder, auch in von Hand formatierten und in generierten Dateien. Er verweigert, wenn

- das Protokoll fehlt oder nicht in der Notiz verlinkt ist,
- eine Zeile kein Ergebnis hat oder eine Abweichung (❌) zeigt,
- eine Zeile ⚠️ zeigt – nach Klärung mit `--trotz-hinweisen`,
- der Name mit „Claude“ beginnt.
- es schon einen Fingerabdruck gibt (z. B. vom Protokoll) und sich der Text seitdem geändert hat – der Diff wird gezeigt; nach Prüfung `--fingerabdruck <id>`, dann erneut abnehmen – oder der Text gerade nicht abrufbar ist (der alte Fingerabdruck bliebe sonst stehen). Abgerufen wird dabei immer frisch, ohne Zwischenspeicher.

Nach der Abnahme speichert der Befehl den Fingerabdruck des Texts für den [Änderungswächter](#änderungswächter).

Abnahme zurücknehmen (z. B. nach einer Gesetzesänderung): `./bai quellen --zuruecksetzen <id>`. Danach committen.

Gebietsquellen (`destatis_kreise`, `openplz_strassen`): Der Gebietsimport behält die Abnahme, solange dieselbe Datenversion importiert wird. Bei einer neuen Version fällt der Status auf `ungeprueft` zurück, mit Hinweis in der Ausgabe.

## Link-Prüfung

`./bai quellen --links [--phase1]` ruft jede Quellen-URL ab und meldet HTTP-Fehler, nicht erreichbare Adressen und Umleitungen auf andere Hosts. Ohne Netz (z. B. in der Cloud-Umgebung) kommt ein Hinweis statt einer Fehlerliste. Exit-Code: 0 alles erreichbar, 1 Fehler gefunden, 2 kein Netz. Abgerufen wird per GET, nicht HEAD: Viele Behördenserver beantworten HEAD mit 403 oder 405, das ergäbe falsche Fehler. Der Inhalt wird nicht gelesen.

## Automatischer Abgleich

```
./bai quellen --abgleich [ID …] [--phase1] [--in-protokoll]
```

Holt den Text der Quelle und prüft zweierlei:

1. **Zitate:** Jedes Zitat in „…“ aus der Spalte „Wortlaut der Quelle“ muss wörtlich im Text stehen. Leerzeichen, Anführungszeichen, Striche und Silbentrennung werden vereinheitlicht; „…“ im Zitat gilt als Lücke.
2. **Zahlen:** Schwellenwerte, Stichtage, Fristen und Beträge der Regeln, die die Quelle zitieren, werden im zitierten Paragrafen gesucht, in deutschen Schreibweisen („175 000“, „1. Januar 2025“, „einer Woche“). Nicht gefunden ist nur ein Hinweis.

Bundesgesetze kommen als XML von gesetze-im-internet.de (`<kürzel>/xml.zip`), mit dem Stand „Zuletzt geändert durch …“; der Paragraf ergibt sich aus der URL der Quelle. Andere Seiten werden als HTML-Text gelesen, PDFs als „manuell“ gemeldet. Abrufe liegen 24 Stunden in `.cache/quellen/` (`--ohne-cache` umgeht das).

Ohne ID: alle Quellen mit Protokoll; mit `--phase1`: alle Quellen der Pilotregion. `--in-protokoll` schreibt das Ergebnis als Abschnitt „Automatischer Abgleich“ ins Protokoll. Exit-Code: 0 alle Zitate gefunden, 1 Zitat fehlt, 2 kein Netz.

**macOS mit Python von python.org:** Meldet der Abgleich `CERTIFICATE_VERIFY_FAILED`, fehlen Python die Stammzertifikate. Entweder einmal „Install Certificates.command“ im Ordner `/Applications/Python 3.x/` ausführen oder das Zertifikatsbündel von macOS mitgeben: `SSL_CERT_FILE=/etc/ssl/cert.pem ./bai quellen --abgleich …`.

**In GitHub Actions** (`.github/workflows/quellen.yml`) läuft der Abgleich samt Link-Prüfung bei jedem PR, der Daten oder Protokolle ändert, und lässt sich manuell starten. Das Ergebnis steht in der Zusammenfassung des Laufs. Fehlende Zitate lassen den Lauf scheitern, fehlende Zahlen und tote Links nicht.

## Änderungswächter

Eine geprüfte Quelle darf nicht unbemerkt veralten (#64). Dafür gibt es je Quelle einen **Fingerabdruck**: den Text des geprüften Abschnitts (`texte/<id>.txt`) mit Prüfsumme und Stand (`fingerabdruecke.json`).

| Was | Befehl |
|-----|--------|
| Fingerabdruck bei der Abnahme | automatisch mit `--abnehmen` (ohne Netz: Hinweis, später nachholen) |
| Fingerabdruck für Quellen mit Protokoll, die noch keinen haben | `./bai quellen --fingerabdruck` |
| Neu erfassen nach unwesentlicher Änderung | `./bai quellen --fingerabdruck <id> …` (entfernt auch den Hinweis) |
| Änderungen suchen, mit Diff | `./bai quellen --aenderungen [<id> …] [--phase1]` |
| Hinweis „seit Prüfung geändert“ in den Ergebnissen setzen | `./bai quellen --aenderungen <id> --vermerken` |

Verglichen wird bei Bundesgesetzen der Text des Paragrafen aus der URL; der Stand („Zuletzt geändert durch …“) wird nur angezeigt, weil gesetze-im-internet.de Änderungen teils vor dem Stand nachträgt. Ändert ein Gesetz nur andere Paragrafen, bleibt die Quelle unverändert. Bei anderen Seiten zählt der Inhaltsbereich; Navigation, „Seite aktualisiert am …“ und Ähnliches blendet die Ausschlussliste in `src/buergerai/aenderungen.py` aus (`AUSSCHLUSS`, je Host Anfangs- und Endmarke, Stand-Zeile, auszublendende Zeilen). Exit-Code: 0 nichts geändert, 1 Befund (Text geändert, URL geändert oder entfernt), 2 kein Netz. Wer `AUSSCHLUSS` ändert, erfasst im selben PR die Fingerabdrücke der betroffenen Quellen neu (`--fingerabdruck <id> …`), sonst meldet der nächste Lauf sie als geändert.

**Wöchentlich** (`.github/workflows/aenderungen.yml`, montags, auch manuell startbar) legt der Wächter je geänderter Quelle ein Issue „Quelle geändert: <id>“ an oder aktualisiert es, mit Diff, betroffenen Verwendungen und nächsten Schritten.

Der Prüfstatus fällt nicht automatisch zurück (ADR 0004, Nachtrag #64). Ein Mensch entscheidet:

- **unwesentlich** (Redaktion, Verweise): `--fingerabdruck <id>`, committen, Issue schließen;
- **wesentlich**: bei verifizierter Quelle `--zuruecksetzen <id>`; Daten und Protokoll anpassen, `--fingerabdruck <id>` (neuer Bezugstext), nach erneuter Prüfung `--abnehmen`.

Grenzen: Quellen, die mehrere Paragrafen abdecken (z. B. `beeg_15_16`), werden nur mit dem Paragrafen aus der URL verglichen. PDFs werden nicht ausgelesen. gesetze-im-internet.de ist von GitHub-Runnern aus bisher nicht erreichbar; Bundesgesetze dort als „nicht erreichbar“, lokal prüfen.

## Ergebnis je Zeile

| Symbol | Bedeutung |
|---|---|
| ✅ | stimmt mit dem Wortlaut überein |
| ❌ | weicht ab – Korrektur nötig (mit Test oder Szenario) |
| ⚠️ | unklar oder nur teilweise belegt – offene Frage benennen |

## Vorlage

```markdown
# Prüfprotokoll: <quelle-id>

- Quelle: <Titel>, <URL>
- Fassung/Stand: <z. B. zuletzt geändert durch Art. X G v. TT.MM.JJJJ> · abgerufen am <Datum>
- Geprüft von: Claude (Recherche) · Abnahme: <Name, Datum>

## Verwendungen in der Wissensbasis

| # | Verwendung in der Wissensbasis | Fundstelle | Wortlaut der Quelle (Zitat, Absatz) | Ergebnis |
|---|---|---|---|---|
| 1 | elterngeld_bund: Bedingung „Arbeitet höchstens 32 Stunden pro Woche“ | `fachmodule/familie/geburt.json` `varianten[7].regel.alle[3]` | § 1 Abs. 6 Nr. 1 BEEG: „…“ | ✅ |

## Abweichungen und Folgeaktionen

- …
```
