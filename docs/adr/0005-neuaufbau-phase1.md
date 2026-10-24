# ADR 0005: Neuaufbau von Phase 1 statt Weiterentwicklung des ersten Entwurfs

**Status:** angenommen · **Datum:** 24.10.2026

## Kontext
Der erste Entwurf (Pull Requests 33 und 35) hatte 22 fehlschlagende und 13 nicht lauffähige Tests, eine abstürzende CLI, fehlende Angaben wurden als „Nein“ gewertet, und die Daten enthielten Platzhalter und veraltete Fakten (z. B. erfundene Telefonnummern, AGS 09176112 für München statt 09162000, Familienkasse als Elterngeldstelle, Bayerisches Familiengeld als aktuelle Leistung).

## Entscheidung
Code, Daten und Tests der Phase 1 wurden neu aufgebaut. Das Architektur-Dokument im Wiki bleibt die fachliche Grundlage; Abweichungen sind in ADR 0002–0004 beschrieben.
