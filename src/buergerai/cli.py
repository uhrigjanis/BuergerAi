"""Terminal-Oberfläche für manuelles Testen von BürgerAI (ohne LLM).

Beispiele::

    buergerai                                   # geführter Dialog (= interaktiv)
    buergerai pruefen --szenario muenchen_verheiratet_angestellt --details
    buergerai pruefen --plz 85354 --fakt kind_geboren=nein --fakt errechneter_termin=15.01.2027
    buergerai erklaeren elterngeld --szenario freising_unverheiratet
    buergerai szenarien --pruefen
    buergerai web                               # Web-Oberfläche auf http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Optional

from . import __version__
from . import anforderungen as anforderungen_mod
from . import gebiete as gebiete_mod
from . import szenarien as szenarien_mod
from .ausgabe import (
    EBENE_TEXT,
    Farbe,
    baum_text,
    bericht_json,
    bericht_text,
    datum,
    frage_zu,
)
from .fakten import UNBEKANNT, EingabeFehler, parse_wert
from .modell import Pruefstatus
from .planer import Anfrage, planen
from .wissensbasis import DatenFehler, Wissensbasis


# --------------------------------------------------------------------- Helfer
def _kb(args: argparse.Namespace) -> Wissensbasis:
    return Wissensbasis.laden(Path(args.daten) if args.daten else None)


def _stichtag(text: Optional[str]) -> date:
    if not text:
        return date.today()
    if "." in text:
        t, m, j = text.split(".")
        return date(int(j), int(m), int(t))
    return date.fromisoformat(text)


def _anfrage(kb: Wissensbasis, args: argparse.Namespace) -> Anfrage:
    if args.szenario:
        anfrage = szenarien_mod.finden(kb, args.szenario).anfrage
    else:
        anfrage = Anfrage(fakten={})
    for k in ("plz", "gemeinde", "land"):
        if getattr(args, k, None):
            setattr(anfrage, k, getattr(args, k))
    if args.stichtag:
        anfrage.stichtag = _stichtag(args.stichtag)
    for eintrag in args.fakt or []:
        if "=" not in eintrag:
            raise EingabeFehler(f"--fakt erwartet NAME=WERT (war: {eintrag!r})")
        fid, wert = eintrag.split("=", 1)
        anfrage.fakten.update(szenarien_mod.fakten_parsen(kb, {fid.strip(): wert.strip()}))
    if not (anfrage.plz or anfrage.gemeinde or anfrage.land):
        raise EingabeFehler("Bitte --plz, --land oder --szenario angeben")
    return anfrage


def _anfrage_optionen(p: argparse.ArgumentParser) -> None:
    p.add_argument("--szenario", "-s", help="Szenario-Name aus szenarien/ oder Pfad zu einer JSON-Datei")
    p.add_argument("--plz", help="Postleitzahl des Wohnorts")
    p.add_argument("--gemeinde", help="Amtlicher Gemeindeschlüssel (bei mehrdeutiger PLZ)")
    p.add_argument("--land", help="Bundesland-Kürzel (z. B. BY), falls die PLZ nicht erfasst ist")
    p.add_argument("--stichtag", help="Bezugsdatum für Fristen und Gültigkeit (Standard: heute)")
    p.add_argument(
        "--fakt", "-f", action="append", metavar="NAME=WERT",
        help="Angabe setzen, z. B. -f eltern_verheiratet=ja -f mutter.beschaeftigt=ja (mehrfach möglich)",
    )


# ------------------------------------------------------------------- Befehle
def cmd_pruefen(args: argparse.Namespace) -> int:
    kb = _kb(args)
    bericht = planen(kb, _anfrage(kb, args))
    if args.json:
        print(json.dumps(bericht_json(bericht), ensure_ascii=False, indent=2))
    else:
        print(bericht_text(bericht, kb, Farbe(None if not args.keine_farbe else False), details=args.details))
    return 0


def cmd_erklaeren(args: argparse.Namespace) -> int:
    kb = _kb(args)
    f = Farbe(None if not args.keine_farbe else False)
    bericht = planen(kb, _anfrage(kb, args))
    try:
        e = bericht.eintrag(args.leistung)
    except KeyError:
        ids = ", ".join(x.leistung.id for x in bericht.eintraege)
        print(f"Leistung {args.leistung!r} ist für diesen Ort nicht erfasst. Verfügbar: {ids}")
        return 1
    print(f.fett(f"{e.leistung.name}") + f"  →  Ergebnis: {e.ergebnis.value.upper()}")
    print(f"Variante: {e.variante.id} (Gebiet {e.gebiet.name}, {EBENE_TEXT[e.gebiet.ebene]}) · Abdeckung: {e.abdeckung.value} · Prüfstatus: {e.pruefstatus.value}")
    for p in e.personen:
        print()
        if p.person:
            print(f.fett(f"Prüfung für: {p.person}"))
        print("\n".join(baum_text(p.schritt, kb, f)))
    print()
    print(f.fett("Quellen:"))
    for q in e.quellen:
        print(f"  {q.id}: {q.titel} [{q.pruefstatus.value}]")
        if q.url:
            print(f"      {q.url}")
        if q.notiz:
            print(f"      {f.grau(q.notiz)}")
    return 0


def _frage(kb: Wissensbasis, fid: str, f: Farbe) -> Any:
    """Fragt einen Fakt ab. Rückgabe: Wert, UNBEKANNT oder None (= beenden)."""
    definition = kb.fakt_definition(fid)
    assert definition is not None
    print()
    print(f.fett(frage_zu(kb, fid)))
    if definition.hilfe:
        print(f.grau(f"  {definition.hilfe}"))
    if definition.typ == "auswahl":
        for i, (_, text) in enumerate(definition.optionen, 1):
            print(f"  {i}) {text}")
    hinweis = {"ja_nein": "ja/nein", "zahl": "Zahl", "datum": "TT.MM.JJJJ", "auswahl": "Nummer"}.get(definition.typ, "")
    while True:
        try:
            roh = input(f"  > ({hinweis}, ? = weiß nicht, q = fertig) ").strip()
        except EOFError:
            return None
        if roh.lower() in ("q", "quit", "fertig", "exit"):
            return None
        if roh == "":
            roh = "?"
        try:
            return parse_wert(definition, roh)
        except EingabeFehler as exc:
            print(f.rot(f"  {exc}"))


def cmd_interaktiv(args: argparse.Namespace) -> int:
    kb = _kb(args)
    f = Farbe(None if not args.keine_farbe else False)
    print(f.fett("BürgerAI – geführte Prüfung für das Lebensereignis Geburt"))
    print(f.grau("Pilot: Bundesleistungen, Bayern, München und Freising. Kein LLM – alle Ergebnisse sind regelbasiert."))
    stichtag = _stichtag(args.stichtag)
    anfrage = Anfrage(fakten={}, stichtag=stichtag)
    if args.szenario:
        anfrage = szenarien_mod.finden(kb, args.szenario).anfrage
        print(f"Szenario geladen. Wohnort: PLZ {anfrage.plz or '-'} / Land {anfrage.land or '-'}")
    else:
        anfrage.plz = args.plz
        while True:
            if not anfrage.plz:
                try:
                    anfrage.plz = input("\nPostleitzahl Ihres Wohnorts: ").strip()
                except EOFError:
                    return 1
            try:
                anfrage.gemeinde = None
                hierarchie = gebiete_mod.aufloesen(kb, anfrage.plz, None, anfrage.land)
                break
            except gebiete_mod.PlzMehrdeutig as exc:
                for i, g in enumerate(exc.gemeinden, 1):
                    print(f"  {i}) {g.name}")
                wahl = input("Welche Gemeinde? ").strip()
                anfrage.gemeinde = exc.gemeinden[int(wahl) - 1].id
                hierarchie = gebiete_mod.aufloesen(kb, gemeinde_id=anfrage.gemeinde)
                break
            except gebiete_mod.PlzUnbekannt as exc:
                print(f.gelb(str(exc)))
                print("  " + ", ".join(f"{g.kuerzel}={g.name}" for g in gebiete_mod.laender(kb)))
                anfrage.land = input("Bundesland-Kürzel: ").strip()
            except gebiete_mod.GebietFehler as exc:
                print(f.rot(str(exc)))
                anfrage.plz, anfrage.land = None, None
        print(f.grau("Wohnort: " + " → ".join(g.name for g in hierarchie)))

    uebersprungen: set[str] = set()
    while True:
        bericht = planen(kb, anfrage)
        offen = [fid for fid in bericht.fehlend if fid not in uebersprungen]
        if not offen:
            break
        print(f.grau(f"\n({len(offen)} offene Frage(n) – die Liste passt sich Ihren Antworten an)"))
        wert = _frage(kb, offen[0], f)
        if wert is None:
            break
        anfrage.fakten[offen[0]] = wert
        if wert is UNBEKANNT:
            uebersprungen.add(offen[0])

    print("\n" + "=" * 72 + "\n")
    print(bericht_text(planen(kb, anfrage), kb, f, details=args.details))
    if args.speichern:
        szenarien_mod.speichern(Path(args.speichern), anfrage, name=Path(args.speichern).stem)
        print(f.gruen(f"\nAngaben gespeichert in {args.speichern} (wieder laden mit --szenario {args.speichern})"))
    return 0


def cmd_gebiet(args: argparse.Namespace) -> int:
    kb = _kb(args)
    try:
        hierarchie = gebiete_mod.aufloesen(kb, args.plz, args.gemeinde, args.land)
    except gebiete_mod.GebietFehler as exc:
        print(str(exc))
        return 1
    for g in hierarchie:
        pilot = " (Pilot)" if g.pilot else ""
        print(f"{EBENE_TEXT[g.ebene]:9} {g.id:9} {g.name}{pilot}")
    return 0


def cmd_leistungen(args: argparse.Namespace) -> int:
    kb = _kb(args)
    for l in sorted(kb.leistungen.values(), key=lambda x: x.id):
        print(f"{l.id}  –  {l.name}  [{', '.join(l.ereignisse)}; verwaltet auf Ebene {l.verwaltungsebene.value}; für {l.fuer}]")
        for v in sorted(kb.varianten_von(l.id), key=lambda v: kb.gebiete[v.gebiet_id].ebene.rang):
            g = kb.gebiete[v.gebiet_id]
            print(f"    Variante {v.id:45} {EBENE_TEXT[g.ebene]:9} {g.name}")
    return 0


def cmd_fakten(args: argparse.Namespace) -> int:
    kb = _kb(args)
    for d in kb.fakten.values():
        merkmale = [d.typ]
        if d.je_person:
            merkmale.append("je Elternteil: mutter./partner.")
        if d.abgeleitet:
            merkmale.append("abgeleitet")
        if d.grunddaten:
            merkmale.append("Grunddaten")
        print(f"{d.id:38} ({', '.join(merkmale)})")
        print(f"    {d.frage_fuer('mutter') if d.je_person else d.frage}")
        if d.optionen:
            print("    Werte: " + ", ".join(w for w, _ in d.optionen))
    return 0


def cmd_quellen(args: argparse.Namespace) -> int:
    kb = _kb(args)
    f = Farbe(None if not args.keine_farbe else False)
    quellen = sorted(kb.quellen.values(), key=lambda q: (q.pruefstatus.value, q.id))
    if args.offen:
        quellen = [q for q in quellen if q.pruefstatus is not Pruefstatus.VERIFIZIERT]
    zaehler: dict[str, int] = {}
    for q in kb.quellen.values():
        zaehler[q.pruefstatus.value] = zaehler.get(q.pruefstatus.value, 0) + 1
    print(f.fett("Prüfstatus der Quellen: ") + ", ".join(f"{k}: {v}" for k, v in sorted(zaehler.items())))
    for q in quellen:
        print(f"\n[{q.pruefstatus.value}] {q.id} – {q.titel}")
        if q.url:
            print(f"    {q.url}")
        if q.geprueft_am:
            print(f"    geprüft am {datum(q.geprueft_am)} von {q.geprueft_von}")
        if q.notiz:
            print(f"    {f.grau(q.notiz)}")
    if args.offen:
        print(f.grau("\nNach eigener Prüfung im Volltext: in data/**/quellen bzw. der jeweiligen Datei "
                     "pruefstatus auf \"verifiziert\" setzen und geprueft_am/geprueft_von eintragen."))
    return 0


def cmd_daten(args: argparse.Namespace) -> int:
    try:
        kb = _kb(args)
    except DatenFehler as exc:
        print(str(exc))
        return 1
    print(f"Wissensbasis OK ({len(kb.dateien)} Dateien)")
    print(f"  Gebiete: {len(kb.gebiete)}, Leistungen: {len(kb.leistungen)}, Varianten: {len(kb.varianten)}, "
          f"Quellen: {len(kb.quellen)}, Zuständigkeiten: {len(kb.zustaendigkeiten)}, Fakten: {len(kb.fakten)}")
    unbenutzt = kb.unbenutzte_fakten()
    if unbenutzt:
        print("  Warnung – Fakten ohne Verwendung: " + ", ".join(unbenutzt))
    return 0


def cmd_szenarien(args: argparse.Namespace) -> int:
    kb = _kb(args)
    f = Farbe(None if not args.keine_farbe else False)
    fehler = 0
    for s in szenarien_mod.alle(kb):
        if not args.pruefen:
            print(f"{f.fett(s.id)}\n    {s.name}" + (f" – {s.beschreibung}" if s.beschreibung else ""))
            continue
        ist = planen(kb, s.anfrage).ergebnisse()
        abweichungen = [f"{l}: erwartet {w}, ist {ist.get(l, 'nicht gelistet')}" for l, w in s.erwartet.items() if ist.get(l) != w]
        if abweichungen:
            fehler += 1
            print(f.rot(f"✗ {s.id}"))
            for a in abweichungen:
                print(f"    {a}")
        else:
            print(f.gruen(f"✓ {s.id}") + f.grau(f"  ({len(s.erwartet)} Erwartungen)"))
    if not args.pruefen:
        print(f.grau("\nAusführen mit: buergerai pruefen --szenario NAME [--details]   |   Erwartungen prüfen: buergerai szenarien --pruefen"))
    return 1 if fehler else 0


def cmd_web(args: argparse.Namespace) -> int:
    from .web.server import starten

    return starten(_kb(args), host=args.host, port=args.port, oeffnen=args.oeffnen)


def cmd_anforderungen(args: argparse.Namespace) -> int:
    f = Farbe(None if not args.keine_farbe else False)
    matrix = anforderungen_mod.testmatrix()
    ohne = 0
    bereich = None
    for a in matrix:
        if a.bereich != bereich:
            bereich = a.bereich
            print("\n" + f.fett(bereich))
        status = f.gruen(f"{len(a.tests)} Test(s)") if a.tests else f.rot("KEIN TEST")
        ohne += 0 if a.tests else 1
        print(f"  {a.id:16} {a.titel}  [{status}]")
        if args.details:
            for t in a.tests:
                print(f.grau(f"      {t}"))
    print(f"\n{len(matrix)} Anforderungen, {len(matrix) - ohne} mit Tests, {ohne} ohne Tests.")
    return 1 if ohne else 0


# ---------------------------------------------------------------------- Main
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="buergerai", description="BürgerAI – regelbasierte Prüfung von Leistungen (ohne LLM)")
    p.add_argument("--version", action="version", version=f"buergerai {__version__}")
    p.add_argument("--daten", help="Alternatives Datenverzeichnis (Standard: data/)")
    p.add_argument("--keine-farbe", action="store_true", help="Ausgabe ohne Farben")
    gemeinsam = argparse.ArgumentParser(add_help=False)
    gemeinsam.add_argument("--daten", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    gemeinsam.add_argument("--keine-farbe", action="store_true", default=argparse.SUPPRESS, help="Ausgabe ohne Farben")
    sub = p.add_subparsers(dest="befehl")
    original_add = sub.add_parser

    def add_parser(name: str, **kw: Any) -> argparse.ArgumentParser:
        return original_add(name, parents=[gemeinsam], **kw)

    sub.add_parser = add_parser  # type: ignore[method-assign]

    s = sub.add_parser("interaktiv", help="Geführter Dialog: fragt nur, was für das Ergebnis nötig ist")
    s.add_argument("--plz")
    s.add_argument("--land")
    s.add_argument("--szenario", "-s", help="Mit gespeicherten Angaben starten und fehlende nachfragen")
    s.add_argument("--stichtag")
    s.add_argument("--details", action="store_true")
    s.add_argument("--speichern", metavar="DATEI.json", help="Angaben am Ende als Szenario speichern")
    s.set_defaults(func=cmd_interaktiv)

    s = sub.add_parser("pruefen", help="Bericht für Ort und Angaben ausgeben")
    _anfrage_optionen(s)
    s.add_argument("--details", "-d", action="store_true", help="Unterlagen, Schritte, Kosten und Quellen zeigen")
    s.add_argument("--json", action="store_true", help="Maschinenlesbare Ausgabe")
    s.set_defaults(func=cmd_pruefen)

    s = sub.add_parser("erklaeren", help="Vollständigen Prüfbaum einer Leistung zeigen")
    s.add_argument("leistung", help="Leistungs-ID, z. B. elterngeld (siehe 'buergerai leistungen')")
    _anfrage_optionen(s)
    s.set_defaults(func=cmd_erklaeren)

    s = sub.add_parser("gebiet", help="Gebietshierarchie zu PLZ/Gemeinde/Land")
    s.add_argument("plz", nargs="?")
    s.add_argument("--gemeinde")
    s.add_argument("--land")
    s.set_defaults(func=cmd_gebiet)

    sub.add_parser("leistungen", help="Alle Leistungen und ihre Varianten").set_defaults(func=cmd_leistungen)
    sub.add_parser("fakten", help="Faktenkatalog (Namen für --fakt)").set_defaults(func=cmd_fakten)

    s = sub.add_parser("quellen", help="Quellen und ihr Prüfstatus")
    s.add_argument("--offen", action="store_true", help="Nur noch nicht verifizierte Quellen")
    s.set_defaults(func=cmd_quellen)

    sub.add_parser("daten", help="Wissensbasis auf Konsistenz prüfen").set_defaults(func=cmd_daten)

    s = sub.add_parser("szenarien", help="Gespeicherte Testprofile auflisten oder prüfen")
    s.add_argument("--pruefen", action="store_true", help="Alle Szenarien gegen ihre Erwartungen prüfen")
    s.set_defaults(func=cmd_szenarien)

    s = sub.add_parser("web", help="Web-Oberfläche starten (Formular, Checkliste, Fristen)")
    s.add_argument("--port", type=int, default=8000, help="Port (Standard: 8000)")
    s.add_argument("--host", default="127.0.0.1", help="Adresse (Standard: 127.0.0.1, nur lokal erreichbar)")
    s.add_argument("--oeffnen", action="store_true", help="Browser automatisch öffnen")
    s.set_defaults(func=cmd_web)

    s = sub.add_parser("anforderungen", help="Testmatrix: Anforderungen und abdeckende Tests")
    s.add_argument("--details", "-d", action="store_true")
    s.set_defaults(func=cmd_anforderungen)
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = parser().parse_args(argv)
    if not args.befehl:
        args = parser().parse_args(["interaktiv"] + (argv if argv is not None else sys.argv[1:]))
    try:
        return args.func(args)
    except (EingabeFehler, gebiete_mod.GebietFehler, FileNotFoundError, DatenFehler) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print()
        return 130
    except BrokenPipeError:  # z. B. "buergerai quellen | head"
        sys.stderr.close()
        return 0


if __name__ == "__main__":
    sys.exit(main())
