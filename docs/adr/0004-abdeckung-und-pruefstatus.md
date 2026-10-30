# ADR 0004: Abdeckungsstatus und Prüfstatus getrennt führen

**Status:** angenommen · **Datum:** 24.10.2026

## Kontext
Im Architektur-Dokument vermischt der „Abdeckungsstatus“ zwei Fragen: Wie spezifisch sind die Daten für den Ort? Und wie gut sind sie geprüft?

## Entscheidung
- **Abdeckung** (berechnet je Ort): `erfasst` (bis 0.3: `vollstaendig`), wenn die gewählte Variante auf der Ebene liegt, auf der die Leistung verwaltet wird (`verwaltungsebene`), sonst `allgemein` (Fallback auf eine höhere Ebene). Seit ADR 0007 ersetzt das den Pilot-Status: Je Land gibt es zusätzlich `erfasst`/`fehlt` für die Landesleistungen.
- **Prüfstatus** (je Quelle): `verifiziert`, `teilweise`, `ungeprueft`, `widerspruechlich`. Ein Eintrag zeigt den schlechtesten Status seiner Quellen.
- `verifiziert` setzt nur ein Mensch nach Prüfung des Volltexts, mit `geprueft_am` und `geprueft_von` (wird von der Konsistenzprüfung erzwungen).
- Bei widersprüchlichen Quellen (Beispiel: Bayerisches Familiengeld) gibt die Regel bewusst Unklar aus.

## Nachtrag 30.10.2026: Änderungen nach der Prüfung (#64)

**Kontext:** Eine verifizierte Quelle kann sich nach der Abnahme ändern (Gesetzesänderung, neue Behördenseite). Der Änderungswächter (`./bai quellen --aenderungen`, wöchentlich in GitHub Actions) erkennt das am Fingerabdruck des geprüften Texts.

**Entscheidung:**
- Der Prüfstatus fällt **nicht automatisch** zurück. Nicht jede Textänderung berührt die Aussage der Regel (Redaktion, Verweise, andere Absätze); das zu beurteilen bleibt beim Menschen, wie die Abnahme selbst.
- Stattdessen meldet der Wächter die Änderung als Issue mit Diff. Bis zur Klärung kann die Quelle mit `--vermerken` das Feld `seit_pruefung_geaendert` (Datum) bekommen; die Ergebnisse zeigen dann „Quelle seit Prüfung geändert“ neben dem unveränderten Prüfstatus.
- Klärung: unwesentlich → `--fingerabdruck <id>` (neuer Bezugstext, Hinweis entfällt); wesentlich → `--zuruecksetzen <id>`, Daten und Protokoll anpassen, `--fingerabdruck <id>`, nach erneuter Prüfung `--abnehmen` (Hinweis entfällt).
- Fingerabdrücke und Bezugstexte liegen bei den Protokollen (`docs/pruefprotokolle/fingerabdruecke.json`, `texte/`), nicht in den Daten: Sie sind Prüfbelege, keine Wissensbasis.
