# BürgerAI

Eine KI, der man erklärt, in welcher Lebenslage man sich befindet (z. B. Schwangerschaft, Geburt, Heirat). Sie sucht die passenden Leistungen und Anträge der zuständigen Behörden heraus und zeigt sie mit Anleitung.

**Aktueller Stand: Phase 1 – Wissenskern ohne LLM.** Alle Ergebnisse kommen aus einer deterministischen Regel-Engine. Pilot: Lebensereignis **Geburt**, Bund + **Bayern**, Kommunen **München** und **Freising**.

> Unverbindliche Orientierung, keine Rechtsberatung.

## Schnellstart (Terminal)

Voraussetzung: Python 3.10 oder neuer. Keine weiteren Pakete nötig.

```bash
./bai                       # geführter Dialog: fragt nur, was für das Ergebnis nötig ist
```

Optional mit virtueller Umgebung, pytest und einmaligem Komplett-Check:

```bash
./scripts/setup.sh          # legt .venv an, installiert, prüft Daten, Tests und Szenarien
source .venv/bin/activate   # danach ist auch der Befehl "buergerai" verfügbar
```

## Manuell testen

| Was | Befehl |
|-----|--------|
| Geführter Dialog | `./bai` oder `./bai interaktiv --plz 85354` |
| Dialog-Angaben speichern | `./bai interaktiv --speichern ich.json` (später: `./bai pruefen -s ich.json`) |
| Fertiges Szenario ansehen | `./bai pruefen -s muenchen_verheiratet_angestellt` |
| … mit Unterlagen, Schritten, Quellen | `./bai pruefen -s freising_unverheiratet_privat --details` |
| Angaben direkt setzen | `./bai pruefen --plz 80331 -f kind_geboren=nein -f errechneter_termin=15.12.2026 -f eltern_verheiratet=nein` |
| Szenario abwandeln | `./bai pruefen -s muenchen_hohes_einkommen -f zve_eltern=170000` |
| Anderes Datum simulieren | `./bai pruefen -s nur_plz --stichtag 2027-01-15` |
| Warum Ja/Nein/Unklar? | `./bai erklaeren elterngeld -s muenchen_hohes_einkommen` |
| Ort außerhalb des Pilots | `./bai pruefen --plz 10115 --land BE` oder `-s berlin_ausserhalb_pilot` |
| Alle Szenarien prüfen | `./bai szenarien --pruefen` |
| Maschinenlesbar | `./bai pruefen -s nur_plz --json` |
| Gebietshierarchie | `./bai gebiet 80331` |
| Namen aller Angaben (für `-f`) | `./bai fakten` |
| Leistungen und Varianten | `./bai leistungen` |
| Quellen und Prüfstatus | `./bai quellen --offen` |
| Datenkonsistenz | `./bai daten` |
| Testmatrix (Anforderung → Tests) | `./bai anforderungen --details` |
| Automatische Tests | `python -m pytest` |

Im Dialog: `?` oder Enter = „weiß nicht“, `q` = fertig und Ergebnis anzeigen.
Werte für `-f`: `ja`/`nein`, Zahlen, Datum als `TT.MM.JJJJ` oder `JJJJ-MM-TT`, Auswahlwerte laut `./bai fakten`, `unbekannt`.

### Szenarien

Unter `szenarien/` liegen Testprofile mit erwarteten Ergebnissen. Sie lassen sich laden und mit `-f` abwandeln. Eigene Szenarien legt man über `--speichern` an oder kopiert eine vorhandene Datei.

| Szenario | Zeigt |
|----------|-------|
| `muenchen_verheiratet_angestellt` | Normalfall, alles erfasst |
| `freising_unverheiratet_privat` | Fallback auf Landesdaten, Vaterschaft/Sorge, BAS-Mutterschaftsgeld, abgelaufene Frist |
| `muenchen_alleinerziehend_drittstaat` | ehrliches „Unklar“ bei Aufenthaltstitel |
| `muenchen_hohes_einkommen` | Elterngeld-Einkommensgrenze, Familienversicherung unklar |
| `muenchen_familiengeld_uebergang` | widersprüchliche Rechtslage (Bayerisches Familiengeld) |
| `berlin_ausserhalb_pilot` | Nicht-Pilotland, nur Bundesdaten mit Warnung |
| `nur_plz` | Startpunkt: fast alles unklar, viele Rückfragen |

## So funktioniert es

```
PLZ/Land ──► Gebietshierarchie (Gemeinde → Kreis → Land → Bund)
                 │
Lebensereignis ──► Leistungen ──► spezifischste gültige Variante je Leistung
                                      │
Angaben (Fakten) ───────────────────► Regel-Engine: Ja / Nein / Unklar + Begründung + Rückfragen
                                      │
                                      ▼
                     Bericht: sortiert nach Voraussetzungen, Ergebnis und Frist,
                     mit Zuständigkeit, Betrag, Fristen, Unterlagen und Quellen
```

- **Dreiwertige Logik:** Fehlende Angaben ergeben „Unklar“, nie „Nein“. Rückfragen kommen nur, wenn sie das Ergebnis noch ändern können ([ADR 0003](docs/adr/0003-dreiwertige-logik.md)).
- **Abdeckung und Prüfstatus:** Jeder Eintrag zeigt, ob Daten für den Ort vorliegen oder nur allgemeine Daten, und wie gut die Quellen geprüft sind ([ADR 0004](docs/adr/0004-abdeckung-und-pruefstatus.md)).
- **Je Elternteil:** Elterngeld und Elternzeit werden für beide Elternteile einzeln geprüft.

## Projektstruktur

```
src/buergerai/      Code: modell, wissensbasis, gebiete, regeln, fakten, fristen, planer, ausgabe, cli
data/               Wissensbasis (getrennt vom Code)
  fakten.json         Faktenkatalog: Angaben mit Frage und Typ
  bund/               Bundesgebiete, Quellen, Leistungen und Bundesvarianten (Geburt)
  laender/by/         Bayern: Kreise, Gemeinden, Landesvarianten
  kommunen/09162000/  München: kommunale Varianten
szenarien/          Testprofile für manuelles Testen und Regression
tests/              pytest, jeweils mit @pytest.mark.anforderung("ANF-…")
docs/
  anforderungen.json  Anforderungen mit IDs (Quelle der Testmatrix)
  validierung.md      Stand der Prüfung gegen Primärquellen
  adr/                Architekturentscheidungen
```

### Daten pflegen

- Neue Kommune: `data/kommunen/<AGS>/geburt.json` mit Varianten; per `"erbt_von": "<varianten-id>"` übernimmt man Regel, Verfahren und Quellen und überschreibt nur, was vor Ort anders ist.
- Regelknoten: `alle`, `eine`, `nicht` (mit `text`), `fakt` (mit `op`, `wert`, `text`, `quellen`) und `pruefung_noetig`. Operatoren: `== != < <= > >= in nicht_in`.
- Nach jeder Änderung: `./bai daten && ./bai szenarien --pruefen && python -m pytest`.

## Stand Phase 1

- ✅ Datenmodell v2 mit Gebietshierarchie, Leistungsvarianten, Abdeckungs- und Prüfstatus
- ✅ Regeln für Bund und Bayern (12 Leistungen rund um die Geburt), Engine, Tests je Anforderung (51/51 abgedeckt)
- ⏳ Validierung gegen Primärquellen: teilweise erfolgt, Volltextprüfung durch einen Menschen offen – siehe [docs/validierung.md](docs/validierung.md)

Nächste Phase: formularbasierter Intake mit einfacher Web-UI (Phase 2). Der geführte Terminal-Dialog ist dafür bereits die Logik-Grundlage.

## Lizenz

Apache 2.0, siehe [LICENSE](LICENSE).
