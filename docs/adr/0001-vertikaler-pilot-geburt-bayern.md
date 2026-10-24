# ADR 0001: Vertikaler Pilot – Geburt in Bayern (München, Freising)

**Status:** angenommen · **Datum:** 24.10.2026

## Kontext
Der Plan sieht vor, erst ein Lebensereignis in einer Pilotregion komplett und getestet umzusetzen.

## Entscheidung
- Lebensereignis: **Geburt** (vor und nach der Geburt).
- Pilotland: **Bayern**. Alle 16 Länder sind als Gebiete angelegt, damit Orte außerhalb ehrlich als „nicht im Pilot“ erkannt werden.
- Pilotkommunen: **München** (mit kommunalen Daten zum Standesamt) und **Freising** (bewusst ohne Kommunaldaten). Freising zeigt, wie der Fallback auf Landesdaten aussieht, und dient als Ausgangspunkt für den Spike „eine Kommune komplett erfassen“ aus Phase 0.

## Folgen
Weitere Länder/Kommunen werden als neue Dateien unter `data/laender/<kürzel>/` bzw. `data/kommunen/<AGS>/` ergänzt, ohne Code zu ändern.
