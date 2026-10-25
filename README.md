# BürgerAI

Eine KI, der man erklärt, in welcher Lebenslage man sich befindet (z. B. Schwangerschaft, Geburt, Heirat). Sie sucht die passenden Leistungen und Anträge der zuständigen Behörden heraus und zeigt sie mit Anleitung.

**Aktueller Stand: Phase 2 – nutzbarer Stand ohne LLM (Web-Oberfläche).** Alle Ergebnisse kommen aus einer deterministischen Regel-Engine. Pilot: Lebensereignis **Geburt**, Bund + **Bayern**, Kommunen **München** und **Freising**.

> Unverbindliche Orientierung, keine Rechtsberatung.

## Schnellstart (Web-Oberfläche)

```bash
./bai web                   # dann im Browser http://localhost:8000 öffnen
```

Ablauf: Postleitzahl eingeben → Fragen per Buttons, Auswahl, Datum oder Zahl beantworten (immer mit „Weiß nicht“) → die Checkliste rechts aktualisiert sich nach jeder Antwort.

| Funktion | Wo |
|----------|-----|
| Beispiel-Familie laden (alle Szenarien) | Startseite → „Zum Testen: Beispiel-Familie laden“ |
| Angabe ändern | „Ihre Angaben“ → „ändern“ |
| Fragen überspringen | „Fragen beenden, nur Ergebnis“ |
| Checkliste abhaken | Kästchen je Leistung (bleibt im Browser gespeichert) |
| Fristen auf einen Blick / in den Kalender | „Fristen auf einen Blick“, Knopf „Fristen in Kalender (.ics)“ |
| Warum Ja/Nein/Unklar, Unterlagen, Anleitung, Quellen | aufklappbar je Leistung |
| Anderes Datum simulieren | „Ihre Angaben“ → „Datum simulieren“ |
| Angaben speichern/öffnen | Knöpfe über der Checkliste (gleiches Format wie `szenarien/`, also auch mit `./bai pruefen -s datei.json` nutzbar) |
| Drucken | Knopf „Drucken“ (klappt alle Details auf) |

Optionen: `./bai web --port 8001`, `--oeffnen` (Browser öffnen), `--host 0.0.0.0` (im Netzwerk erreichbar, nur bewusst nutzen).

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

### In GitHub Codespaces

Auf GitHub **Code → Codespaces → Create codespace** wählen. Die Umgebung richtet sich automatisch ein (Python 3.12, `.venv`, pytest, einmaliger Komplett-Check) und startet die Web-Oberfläche auf Port 8000. Der Browser-Tab öffnet sich automatisch; sonst unten im Reiter **Ports** bei „BürgerAI Web“ (8000) auf das Weltkugel-Symbol klicken.

- Läuft die Oberfläche nicht (z. B. nach einem Neustart): `./scripts/web-start.sh` oder `./bai web` im Terminal.
- Log: `/tmp/buergerai-web.log`. Beenden: `pkill -f "buergerai web"`.
- Bestehender Codespace von Phase 1: einmal **Strg+Shift+P → „Codespaces: Rebuild Container“**, damit die Portfreigabe greift. Alternativ einfach `./bai web` starten und Port 8000 im Reiter Ports öffnen.
- Der Port ist standardmäßig privat (nur mit Ihrem GitHub-Login erreichbar).

Für den Terminal-Dialog: `./bai`. Tests laufen auch über die Test-Ansicht von VS Code.

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
| Web-Oberfläche | `./bai web` |
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
  web/                Web-Oberfläche: api (JSON-Logik), server (http.server), static/ (HTML, CSS, JS)
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

## Stand Phase 2

- ✅ Formularbasierter Intake (Buttons, Auswahl, Datum, Zahl, „Weiß nicht“), fragt nur, was das Ergebnis noch ändert
- ✅ Einfache Web-UI ohne Framework und ohne Laufzeit-Abhängigkeiten ([ADR 0006](docs/adr/0006-web-oberflaeche-ohne-framework.md)), auch am Handy nutzbar
- ✅ Checkliste mit Fristen (inkl. Kalenderdatei), Zuständigkeit, Unterlagen, Anleitung, Begründung und Quellen
- ✅ Gleiche Ergebnisse wie im Terminal (Test über alle Szenarien), 60/60 Anforderungen mit Tests
- ⏳ Abnahme: einmal manuell in Codespaces durchklicken (siehe oben)

Nächste Phase: LLM-Schicht (Phase 3) mit Freitext-Intake. Die Web-Oberfläche bleibt als Notbremse ohne LLM bestehen.

## Lizenz

Apache 2.0, siehe [LICENSE](LICENSE).
