# BürgerAI

Eine KI, der man erklärt, in welcher Lebenslage man sich befindet (z. B. Schwangerschaft, Geburt, Heirat). Sie sucht die passenden Leistungen und Anträge der zuständigen Behörden heraus und zeigt sie mit Anleitung.

**Aktueller Stand: Phase 2 + bundesweite Abdeckung + Fachmodule, ohne LLM.** Alle Ergebnisse kommen aus einer deterministischen Regel-Engine. Lebenslage **Geburt** (Fachmodul Familie) für **ganz Deutschland**: alle 16 Länder, 400 Kreise und rund 10.700 Gemeinden mit PLZ. Besonders detailliert: Bayern, München und Freising. Weitere Lebenslagen kommen als Fachmodule dazu ([ADR 0008](docs/adr/0008-lebenslagen-als-fachmodule.md), #41).

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
- Nach `git pull`: Server neu starten (`pkill -f "buergerai web"; ./scripts/web-start.sh`) und die Seite mit Strg+Umschalt+R bzw. Cmd+Umschalt+R neu laden. Unten auf der Seite steht die Version; passt sie nicht zum Server, zeigt die Seite eine Warnung.
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
| Beliebiger Ort in Deutschland | `./bai pruefen --plz 50667 -d` oder `-s koeln_unverheiratet` |
| PLZ mit mehreren Gemeinden | `./bai interaktiv --plz 85356` (Gemeinde wählen) bzw. `./bai pruefen --plz 85356 --gemeinde 09177133` |
| Postfach-PLZ (keine Gemeinde) | `./bai pruefen --plz 80001 --land BY` |
| Abdeckung je Land | `./bai abdeckung` |
| Gebiete und PLZ neu importieren | `./bai gebiete-import …` (siehe [docs/datenquellen.md](docs/datenquellen.md)) |
| Alle Szenarien prüfen | `./bai szenarien --pruefen` |
| Maschinenlesbar | `./bai pruefen -s nur_plz --json` |
| Gebietshierarchie | `./bai gebiet 80331` |
| Namen aller Angaben (für `-f`), nach Fachmodul | `./bai fakten` |
| Fachmodule und Lebenslagen | `./bai lebenslagen` |
| Lebenslage per Stichwort finden | `./bai lebenslagen --suche "Wir bekommen ein Baby"` |
| Lebenslage(n) wählen | `./bai pruefen -s nur_plz --lebenslage geburt` (mehrfach möglich, Standard: `geburt`) |
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
| `muenchen_postfach_plz` | PLZ ohne Gemeinde: Rückfrage nach dem Bundesland, Warnung |
| je ein Szenario pro Land, z. B. `kiel_…`, `baunatal_…` (Hessen), `dresden_…` (Landeserziehungsgeld), `koeln_unverheiratet`, `bremerhaven_…` (mehrdeutige PLZ) | Elterngeldstelle des Landes, Jugendamt mit Kreisname; geprüft über `erwartet_stellen` |
| `nur_plz` | Startpunkt: fast alles unklar, viele Rückfragen |

## So funktioniert es

```
PLZ/Land ──► Gebietshierarchie (Gemeinde → Kreis → Land → Bund)
                 │
Lebenslage(n) ──► Leistungen ──► spezifischste gültige Variante je Leistung (am Wohnort oder Ortsbezug)
                                      │
Angaben (Fakten) ───────────────────► Regel-Engine: Ja / Nein / Unklar + Begründung + Rückfragen
                                      │
                                      ▼
                     Bericht: sortiert nach Voraussetzungen, Ergebnis und Frist,
                     mit Zuständigkeit, Betrag, Fristen, Unterlagen und Quellen
```

- **Dreiwertige Logik:** Fehlende Angaben ergeben „Unklar“, nie „Nein“. Rückfragen kommen nur, wenn sie das Ergebnis noch ändern können ([ADR 0003](docs/adr/0003-dreiwertige-logik.md)).
- **Abdeckung und Prüfstatus:** Jeder Eintrag zeigt, ob die zuständige Stelle vor Ort erfasst ist oder nur allgemeine Angaben vorliegen, und wie gut die Quellen geprüft sind ([ADR 0004](docs/adr/0004-abdeckung-und-pruefstatus.md), [ADR 0007](docs/adr/0007-bundesweit-vor-phase-3.md)).
- **Je Person:** Leistungen können je Rolle geprüft werden (z. B. Elterngeld für Mutter und anderen Elternteil). Rollen stehen in den Daten.
- **Fachmodule:** Jede Lebenslage gehört zu einem Fachmodul (dem späteren Experten). Ein Modul ist ein Datenpaket, alle Module laufen auf derselben Engine ([ADR 0008](docs/adr/0008-lebenslagen-als-fachmodule.md)).

## Projektstruktur

```
src/buergerai/      Code: modell, wissensbasis, gebiete, regeln, fakten, fristen, planer, suche, ausgabe, cli
  web/                Web-Oberfläche: api (JSON-Logik), server (http.server), static/ (HTML, CSS, JS)
data/               Wissensbasis (getrennt vom Code)
  kern/               Fakten, die alle Fachmodule nutzen (Wohnort, Haushalt, Einkommen, Personen)
  fachmodule/<id>/    je Fachmodul: modul.json (Steckbrief, Lebenslagen, Rollen), fakten.json, Leistungen und Bundesvarianten
    familie/            Familie und Kinder mit der Lebenslage Geburt
  bund/               Bund und Länder (Gebiete), Quellen
  generiert/          automatisch importiert: alle Kreise, Gemeinden und PLZ (nicht von Hand ändern, ODbL)
  laender/<kürzel>/   je Land: Elterngeldstelle, Landesleistungen, Abdeckungsnachweis
  kreise/<AGS>/       Kreise mit erfasstem Jugendamt (München, Landkreis Freising)
  kommunen/09162000/  München: kommunale Varianten
szenarien/          Testprofile für manuelles Testen und Regression
tests/              pytest, jeweils mit @pytest.mark.anforderung("ANF-…")
docs/
  anforderungen.json  Anforderungen mit IDs (Quelle der Testmatrix)
  validierung.md      Stand der Prüfung gegen Primärquellen (inkl. Stichprobe je Land)
  datenquellen.md     Quellen und Lizenzen der importierten Daten, Import-Anleitung
  adr/                Architekturentscheidungen
```

### Daten pflegen

- Zuständigkeiten dürfen `{kreis}`, `{gemeinde}` und `{land}` enthalten; sie werden durch den Wohnort ersetzt (z. B. „Jugendamt – {kreis}“).
- Neues Land bzw. neue Lebenslage: Unter `abdeckung` (mit `lebenslage`) festhalten, ob es Landesleistungen gibt (`erfasst` oder `keine`); sonst warnt der Bericht.
- Neues Fachmodul: Ordner `data/fachmodule/<id>/` mit `modul.json` (`fachmodul`, `lebenslagen` mit Einstiegsfragen, Synonymen und Beispielen, ggf. `rollen`) und `fakten.json`. Eigene Fakten mit Präfix `<id>.`. Regeln dürfen nur Kern-Fakten, eigene Fakten und unter `importiert_fakten` genannte Fakten anderer Module nutzen.
- Leistung: `lebenslagen` (eine oder mehrere), `fuer` (`"haushalt"` oder Liste von Rollen), `art` (`pflicht`, `antrag`, `geldleistung`, `foerderprogramm`, `information`), optional `rechtsanspruch`, `beantragt_von` (`selbst`, `arbeitgeber`, `angehoerige`, `von_amts_wegen`) und `ortsbezug` (Fakt vom Typ `ort`, z. B. Lage der Immobilie).
- Fristen: `bezug` ist `geburt`, `termin`, `keiner` oder ein Datumsfakt (z. B. Kaufdatum).
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

## Stand bundesweite Abdeckung (#40)

- ✅ Alle Kreise, Gemeinden und PLZ automatisch importiert, wiederholbar mit Diff ([docs/datenquellen.md](docs/datenquellen.md))
- ✅ Elterngeld: zuständige Stelle in allen 16 Ländern (Hessen und Schleswig-Holstein je Kreis); Landesleistungen erfasst bzw. als „keine“ dokumentiert
- ✅ Jugendamt und Standesamt bundesweit als Fallback mit ehrlichem Abdeckungsstatus; Jugendamt nennt den Kreis
- ✅ `pilot` ersetzt durch Abdeckungsstatus je Leistung und Land (`./bai abdeckung`), je Land ein Szenario, 73/73 Anforderungen mit Tests
- ⏳ Stichprobe von 3 Gemeinden je Land gegen Behördenseiten ([docs/validierung.md](docs/validierung.md)), Standesämter/Jugendämter je Gemeinde automatisch importieren (Folge-Issue)

## Stand Fachmodule (#41, Schritt 0)

- ✅ Geburt als Lebenslage im Fachmodul Familie; Kern-Fakten getrennt von Modul-Fakten, Modulgrenzen werden geprüft
- ✅ Mehrere Lebenslagen je Anfrage, Rollen aus den Daten, Ortsbezug je Leistung, Förderprogramme, „nur in anderen Ländern“, Fristen zu beliebigen Datumsfakten
- ✅ Fragen nach Entscheidungskraft sortiert, Stichwortsuche nach Lebenslagen (`./bai lebenslagen --suche`)
- ✅ Performance-Budget in Zielgröße als Test (500 Leistungen, 5.000 Varianten: Laden 0,3 s, Bericht mit 3 Lebenslagen etwa 7 ms), 83/83 Anforderungen mit Tests
- ⏳ Auswahl mehrerer Lebenslagen in der Web-Oberfläche (sobald es eine zweite gibt; die API kann es schon)

Nächste Schritte: Lebenslage Umzug (#41, Schritt 1), danach LLM-Schicht (Phase 3) mit Freitext-Intake. Die Web-Oberfläche bleibt als Notbremse ohne LLM bestehen.

## Lizenz

Apache 2.0, siehe [LICENSE](LICENSE).
