# ADR 0002: Standardbibliothek und JSON-Dateien statt PostgreSQL/Neo4j in Phase 1

**Status:** angenommen · **Datum:** 24.10.2026

## Kontext
Das Architektur-Dokument nennt PostgreSQL, Neo4j und Redis. Für Phase 1 (≈ 15 Varianten) wäre das reiner Betriebsaufwand.

## Entscheidung
- Wissensbasis als **versionierte JSON-Dateien** unter `data/`, getrennt vom Code. Jede Datei darf beliebige Objekttypen enthalten; der Loader führt alles zusammen und prüft die Konsistenz.
- **Keine Laufzeit-Abhängigkeiten** (nur Python-Standardbibliothek, ≥ 3.10). Abhängigkeitsgraph per topologischer Sortierung statt Neo4j.
- Testwerkzeug: pytest.

## Folgen
- Änderungen an Daten sind im Git-Diff nachvollziehbar (gut für Review vor Freigabe, Phase 4).
- Ein späterer Umzug in eine Datenbank ist möglich, weil der Zugriff über `Wissensbasis` gekapselt ist.
