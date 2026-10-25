# ADR 0004: Abdeckungsstatus und Prüfstatus getrennt führen

**Status:** angenommen · **Datum:** 24.10.2026

## Kontext
Im Architektur-Dokument vermischt der „Abdeckungsstatus“ zwei Fragen: Wie spezifisch sind die Daten für den Ort? Und wie gut sind sie geprüft?

## Entscheidung
- **Abdeckung** (berechnet je Ort): `erfasst` (bis 0.3: `vollstaendig`), wenn die gewählte Variante auf der Ebene liegt, auf der die Leistung verwaltet wird (`verwaltungsebene`), sonst `allgemein` (Fallback auf eine höhere Ebene). Seit ADR 0007 ersetzt das den Pilot-Status: Je Land gibt es zusätzlich `erfasst`/`fehlt` für die Landesleistungen.
- **Prüfstatus** (je Quelle): `verifiziert`, `teilweise`, `ungeprueft`, `widerspruechlich`. Ein Eintrag zeigt den schlechtesten Status seiner Quellen.
- `verifiziert` setzt nur ein Mensch nach Prüfung des Volltexts, mit `geprueft_am` und `geprueft_von` (wird von der Konsistenzprüfung erzwungen).
- Bei widersprüchlichen Quellen (Beispiel: Bayerisches Familiengeld) gibt die Regel bewusst Unklar aus.
