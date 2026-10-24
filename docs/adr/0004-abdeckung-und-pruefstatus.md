# ADR 0004: Abdeckungsstatus und Prüfstatus getrennt führen

**Status:** angenommen · **Datum:** 24.10.2026

## Kontext
Im Architektur-Dokument vermischt der „Abdeckungsstatus“ zwei Fragen: Wie spezifisch sind die Daten für den Ort? Und wie gut sind sie geprüft?

## Entscheidung
- **Abdeckung** (berechnet je Ort): `vollstaendig`, wenn die gewählte Variante auf der Ebene liegt, auf der die Leistung verwaltet wird (`verwaltungsebene`), sonst `allgemein` (Fallback auf eine höhere Ebene). Ist eine Leistung für einen Ort gar nicht erfasst, warnt der Bericht, dass Land oder Kommune nicht im Pilot liegen.
- **Prüfstatus** (je Quelle): `verifiziert`, `teilweise`, `ungeprueft`, `widerspruechlich`. Ein Eintrag zeigt den schlechtesten Status seiner Quellen.
- `verifiziert` setzt nur ein Mensch nach Prüfung des Volltexts, mit `geprueft_am` und `geprueft_von` (wird von der Konsistenzprüfung erzwungen).
- Bei widersprüchlichen Quellen (Beispiel: Bayerisches Familiengeld) gibt die Regel bewusst Unklar aus.
