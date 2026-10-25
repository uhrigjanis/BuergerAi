"""Terminal-Oberfläche für manuelles Testen von BürgerAI (ohne LLM).

Beispiele::

    buergerai                                   # geführter Dialog (= interaktiv)
    buergerai pruefen --szenario muenchen_verheiratet_angestellt --details
    buergerai pruefen --plz 85354 --fakt kind_geboren=nein --fakt errechneter_termin=15.01.2027
    buergerai erklaeren elterngeld --szenario freising_unverheiratet
    buergerai lebenslagen --suche "Wir bekommen ein Baby"
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
    person_name,
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
    if getattr(args, "lebenslage", None):
        anfrage.lebenslagen = list(dict.fromkeys(args.lebenslage))
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
    _lebenslage_option(p)
    p.add_argument(
        "--fakt", "-f", action="append", metavar="NAME=WERT",
        help="Angabe setzen, z. B. -f eltern_verheiratet=ja -f mutter.beschaeftigt=ja (mehrfach möglich)",
    )


def _lebenslage_option(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--lebenslage", "-l", action="append", metavar="ID",
        help="Lebenslage, mehrfach möglich (Standard: geburt; siehe 'buergerai lebenslagen')",
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
            print(f.fett(f"Prüfung für: {person_name(kb, p.person)}"))
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
    hinweis = {"ja_nein": "ja/nein", "zahl": "Zahl", "datum": "TT.MM.JJJJ", "auswahl": "Nummer", "ort": "PLZ"}.get(
        definition.typ, ""
    )
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
    from .ausgabe import lebenslagen_text

    kb = _kb(args)
    f = Farbe(None if not args.keine_farbe else False)
    stichtag = _stichtag(args.stichtag)
    anfrage = Anfrage(fakten={}, stichtag=stichtag)
    if args.szenario:
        anfrage = szenarien_mod.finden(kb, args.szenario).anfrage
    if args.lebenslage:
        anfrage.lebenslagen = list(dict.fromkeys(args.lebenslage))
    unbekannt = [ll for ll in anfrage.lebenslagen if ll not in kb.lebenslagen]
    if unbekannt:
        raise EingabeFehler(f"Unbekannte Lebenslage {', '.join(unbekannt)} (siehe 'buergerai lebenslagen')")
    print(f.fett(f"BürgerAI – geführte Prüfung: {lebenslagen_text(kb, anfrage.lebenslagen)}"))
    print(f.grau("Alle Bundesländer, Kreise und Gemeinden. Kein LLM – alle Ergebnisse sind regelbasiert."))
    if args.szenario:
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
                    kreis = gebiete_mod.kreis_von(kb, g)
                    print(f"  {i}) {g.name}" + (f.grau(f" ({kreis.name})") if kreis else ""))
                while True:
                    wahl = input("Welche Gemeinde? (Nummer) ").strip()
                    if wahl.isdigit() and 1 <= int(wahl) <= len(exc.gemeinden):
                        break
                    print(f.rot(f"  Bitte eine Zahl von 1 bis {len(exc.gemeinden)} eingeben."))
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
        zusatz = f" – {g.verband[1]}" if g.verband else ""
        print(f"{EBENE_TEXT[g.ebene]:9} {g.id:9} {g.name}{zusatz}")
    return 0


def cmd_abdeckung(args: argparse.Namespace) -> int:
    """Übersicht je Land: Wie viel ist für eine Lebenslage vor Ort erfasst?"""
    from .ausgabe import ABDECKUNG_TEXT
    from .modell import Abdeckung, Ebene
    from .planer import abdeckung_eintrag, beste_variante, landesabdeckung

    kb = _kb(args)
    f = Farbe(None if not args.keine_farbe else False)
    stichtag = _stichtag(args.stichtag)
    if args.lebenslage not in kb.lebenslagen:
        raise EingabeFehler(f"Unbekannte Lebenslage {args.lebenslage} (siehe 'buergerai lebenslagen')")
    leistungen = sorted(
        (l for l in kb.leistungen_fuer([args.lebenslage]) if l.verwaltungsebene is not Ebene.BUND),
        key=lambda l: (l.verwaltungsebene.rang, l.id),
    )
    kreise_je_land: dict[str, list[Any]] = {}
    gemeinden_je_kreis: dict[str, list[Any]] = {}
    for g in kb.gebiete.values():
        if g.ebene is Ebene.KREIS:
            kreise_je_land.setdefault(g.parent_id, []).append(g)
        elif g.ebene is Ebene.GEMEINDE:
            gemeinden_je_kreis.setdefault(g.parent_id, []).append(g)
    print(f.fett(f"Abdeckung für die Lebenslage '{args.lebenslage}' (Stichtag {datum(stichtag)})"))
    print(f.grau("Je Leistung (nur Leistungen, die nicht auf Bundesebene verwaltet werden): "
                 "Anzahl der Gemeinden, für die die zuständige Stelle erfasst ist.\n"))
    for land in gebiete_mod.laender(kb):
        nachweis = kb.landesabdeckung.get((land.id, args.lebenslage))
        if landesabdeckung(kb, land, args.lebenslage) is Abdeckung.FEHLT:
            ll = f.rot("nicht recherchiert")
        elif nachweis and nachweis.landesleistungen == "keine":
            ll = "keine"
        else:
            ll = ", ".join(kb.leistungen[i].name for i in kb.landesleistungen(land.id, args.lebenslage))
        gemeinden = [g for k in kreise_je_land.get(land.id, []) for g in gemeinden_je_kreis.get(k.id, [])]
        print(f.fett(f"{land.kuerzel} {land.name}") + f.grau(f"  ({len(kreise_je_land.get(land.id, []))} Kreise, {len(gemeinden)} Gemeinden)"))
        print(f"    Landesleistungen: {ll}")
        for l in leistungen:
            gebiete_der_varianten = [gebiete_mod.hierarchie(kb, v.gebiet_id) for v in kb.varianten_von(l.id)]
            if not any(land in kette or len(kette) == 1 for kette in gebiete_der_varianten):
                continue  # Landesleistung eines anderen Landes
            erfasst = 0
            for g in gemeinden:
                treffer = beste_variante(kb, l, gebiete_mod.hierarchie(kb, g.id), stichtag)
                if treffer and abdeckung_eintrag(l, treffer[1]) is Abdeckung.ERFASST:
                    erfasst += 1
            voll = bool(gemeinden) and erfasst == len(gemeinden)
            farbe = f.gruen if voll else (f.gelb if erfasst else f.grau)
            if voll:
                text = ABDECKUNG_TEXT[Abdeckung.ERFASST]
            elif erfasst:
                text = "teilweise erfasst, sonst " + ABDECKUNG_TEXT[Abdeckung.ALLGEMEIN]
            else:
                text = ABDECKUNG_TEXT[Abdeckung.ALLGEMEIN]
            print(f"    {l.name[:45]:45} {farbe(f'{erfasst:>5}/{len(gemeinden):<5}')}  {f.grau(text)}")
    return 0


def cmd_leistungen(args: argparse.Namespace) -> int:
    kb = _kb(args)
    for l in sorted(kb.leistungen.values(), key=lambda x: x.id):
        fuer = ", ".join(l.fuer) if l.fuer else "Haushalt"
        print(f"{l.id}  –  {l.name}  [{', '.join(l.lebenslagen)}; verwaltet auf Ebene {l.verwaltungsebene.value}; für {fuer}]")
        for v in sorted(kb.varianten_von(l.id), key=lambda v: kb.gebiete[v.gebiet_id].ebene.rang):
            g = kb.gebiete[v.gebiet_id]
            print(f"    Variante {v.id:45} {EBENE_TEXT[g.ebene]:9} {g.name}")
    return 0


def cmd_fakten(args: argparse.Namespace) -> int:
    kb = _kb(args)
    f = Farbe(None if not args.keine_farbe else False)
    einstieg = {fid: ll.name for ll in kb.lebenslagen.values() for fid in ll.einstiegsfragen}
    rollen = ", ".join(f"{r.id}." for r in kb.rollen.values())
    module = ["kern"] + sorted(kb.fachmodule)
    for modul in module:
        definitionen = [d for d in kb.fakten.values() if d.modul == modul]
        if not definitionen:
            continue
        titel = "Kern (alle Fachmodule)" if modul == "kern" else f"Fachmodul {kb.fachmodule[modul].name}"
        print(f.fett(f"== {titel} =="))
        for d in definitionen:
            merkmale = [d.typ]
            if d.je_person:
                merkmale.append(f"je Rolle: {rollen}")
            if d.abgeleitet:
                merkmale.append("abgeleitet")
            if d.id in einstieg:
                merkmale.append(f"Einstiegsfrage {einstieg[d.id]}")
            print(f"{d.id:38} ({', '.join(merkmale)})")
            beispiel = next(iter(kb.rollen.values()), None)
            print(f"    {d.frage_fuer(beispiel.wer) if d.je_person and beispiel else d.frage}")
            if d.optionen:
                print("    Werte: " + ", ".join(w for w, _ in d.optionen))
        print()
    return 0


def cmd_lebenslagen(args: argparse.Namespace) -> int:
    from .suche import lebenslagen_suchen

    kb = _kb(args)
    f = Farbe(None if not args.keine_farbe else False)
    if args.suche:
        treffer = lebenslagen_suchen(kb, args.suche)
        if not treffer:
            print("Keine passende Lebenslage gefunden. Alle Lebenslagen: buergerai lebenslagen")
            return 1
        for ll, punkte in treffer:
            print(f"{ll.id:20} {ll.name}  {f.grau(f'({punkte} Punkte, Fachmodul {kb.fachmodule[ll.modul].name})')}")
        return 0
    for m in sorted(kb.fachmodule.values(), key=lambda m: m.id):
        print(f.fett(f"Fachmodul {m.name}") + f.grau(f"  ({m.id})"))
        print(f"    {m.beschreibung}")
        rollen = [r.name for r in kb.rollen.values() if r.modul == m.id]
        fakten = [d for d in kb.fakten.values() if d.modul == m.id]
        print(f.grau(f"    Rollen: {', '.join(rollen) or '-'} · Fakten: {len(fakten)}"))
        for ll in sorted((x for x in kb.lebenslagen.values() if x.modul == m.id), key=lambda x: x.id):
            leistungen = kb.leistungen_fuer([ll.id])
            print(f"  {f.fett(ll.id)} – {ll.name} ({ll.typ}): {ll.beschreibung}")
            print(f.grau(f"      {len(leistungen)} Leistungen · Einstiegsfragen: {', '.join(ll.einstiegsfragen) or '-'}"))
    print(f.grau("\nPrüfen mit: buergerai pruefen --lebenslage ID …   |   Suche: buergerai lebenslagen --suche \"Text\""))
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
    print(f"  Fachmodule: {len(kb.fachmodule)}, Lebenslagen: {len(kb.lebenslagen)}, Rollen: {len(kb.rollen)}")
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
        abweichungen = szenarien_mod.abweichungen(s, planen(kb, s.anfrage))
        if abweichungen:
            fehler += 1
            print(f.rot(f"✗ {s.id}"))
            for a in abweichungen:
                print(f"    {a}")
        else:
            print(f.gruen(f"✓ {s.id}") + f.grau(f"  ({len(s.erwartet) + len(s.erwartet_stellen)} Erwartungen)"))
    if not args.pruefen:
        print(f.grau("\nAusführen mit: buergerai pruefen --szenario NAME [--details]   |   Erwartungen prüfen: buergerai szenarien --pruefen"))
    return 1 if fehler else 0


def cmd_gebiete_import(args: argparse.Namespace) -> int:
    from . import gebietsimport as gi

    f = Farbe(None if not args.keine_farbe else False)
    try:
        plz_gemeinden = gi.plz_lesen(Path(args.plz))
        if args.gv100ad:
            stand, kreise, amtlich = gi.gv100ad_lesen(Path(args.gv100ad))
            kreisquelle, kreis_version = gi.QUELLE_GV100, args.kreise_stand or stand
        else:
            kreise, amtlich = gi.kreisliste_lesen(Path(args.kreise)), None
            kreisquelle, kreis_version = gi.QUELLE_KREISE, args.kreise_stand or "unbekannt"
        daten = gi.zusammenfuehren(plz_gemeinden, kreise, amtlich)
    except (gi.ImportFehler, OSError) as exc:
        print(f.rot(f"Import abgebrochen: {exc}"))
        return 1
    inhalt = gi.datei_erzeugen(daten, kreisquelle, args.plz_stand or "unbekannt", kreis_version)
    ziel = Path(args.ziel) if args.ziel else gi.ZIEL_STANDARD
    anzahl = inhalt["_import"]["anzahl"]
    print(f.fett(f"Import: {anzahl['kreise']} Kreise, {anzahl['gemeinden']} Gemeinden, {anzahl['plz']} PLZ"))
    for h in daten.hinweise:
        print(f.gelb(f"  Hinweis: {h}"))
    mehrdeutig = sum(1 for n in _plz_zaehler(inhalt).values() if n > 1)
    print(f"  PLZ mit mehreren Gemeinden: {mehrdeutig}")
    print(f.fett(f"\nÄnderungen gegenüber {ziel}:"))
    for zeile in gi.vergleichen(gi.vorhandene_gebiete(ziel), inhalt["gebiete"]).zeilen():
        print("  " + zeile)
    if args.nur_diff:
        print(f.grau("\n(--nur-diff: nichts geschrieben)"))
        return 0
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(gi.als_text(inhalt), encoding="utf-8")
    print(f.gruen(f"\nGeschrieben: {ziel}"))
    print(f.grau("Danach prüfen: buergerai daten && python -m pytest"))
    return 0


def _plz_zaehler(inhalt: dict[str, Any]) -> dict[str, int]:
    zaehler: dict[str, int] = {}
    for g in inhalt["gebiete"]:
        for p in g.get("plz", ()):
            zaehler[p] = zaehler.get(p, 0) + 1
    return zaehler


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
    _lebenslage_option(s)
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

    s = sub.add_parser("abdeckung", help="Je Land: Landesleistungen und erfasste Stellen vor Ort")
    s.add_argument("--lebenslage", "--ereignis", dest="lebenslage", default="geburt")
    s.add_argument("--stichtag")
    s.set_defaults(func=cmd_abdeckung)

    sub.add_parser("leistungen", help="Alle Leistungen und ihre Varianten").set_defaults(func=cmd_leistungen)
    sub.add_parser("fakten", help="Faktenkatalog nach Fachmodul (Namen für --fakt)").set_defaults(func=cmd_fakten)

    s = sub.add_parser("lebenslagen", help="Fachmodule und Lebenslagen, Stichwortsuche")
    s.add_argument("--suche", metavar="TEXT", help="Passende Lebenslagen zu einem Satz finden")
    s.set_defaults(func=cmd_lebenslagen)

    s = sub.add_parser("quellen", help="Quellen und ihr Prüfstatus")
    s.add_argument("--offen", action="store_true", help="Nur noch nicht verifizierte Quellen")
    s.set_defaults(func=cmd_quellen)

    sub.add_parser("daten", help="Wissensbasis auf Konsistenz prüfen").set_defaults(func=cmd_daten)

    s = sub.add_parser("szenarien", help="Gespeicherte Testprofile auflisten oder prüfen")
    s.add_argument("--pruefen", action="store_true", help="Alle Szenarien gegen ihre Erwartungen prüfen")
    s.set_defaults(func=cmd_szenarien)

    s = sub.add_parser("gebiete-import", help="Kreise, Gemeinden und PLZ bundesweit neu importieren (data/generiert)")
    s.add_argument("--plz", required=True, metavar="STREETS.CSV", help="OpenPLZ-Straßenverzeichnis (streets.csv)")
    quelle = s.add_mutually_exclusive_group(required=True)
    quelle.add_argument("--kreise", metavar="KREISE.CSV", help="Kreisliste (AGS;type;name) von Destatis")
    quelle.add_argument("--gv100ad", metavar="GV100AD.TXT", help="Amtliches Gemeindeverzeichnis GV100AD von Destatis")
    s.add_argument("--plz-stand", help="Version der PLZ-Daten, z. B. Git-Commit oder Datum")
    s.add_argument("--kreise-stand", help="Stand der Kreisliste (beim GV100AD: aus der Datei)")
    s.add_argument("--ziel", help="Zieldatei (Standard: data/generiert/gebiete.json)")
    s.add_argument("--nur-diff", action="store_true", help="Nur Änderungen anzeigen, nichts schreiben")
    s.set_defaults(func=cmd_gebiete_import)

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
