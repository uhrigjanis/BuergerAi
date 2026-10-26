"""Orchestrator: aus Anfrage (Ort, Lebenslagen, Fakten) wird ein priorisierter Bericht.

Alle Fachmodule laufen durch denselben Planer (ADR 0008). Ausgewertet werden nur
die Leistungen der gewählten Lebenslagen; jede Leistung erscheint einmal, auch
wenn sie zu mehreren gewählten Lebenslagen gehört.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any, Optional

from . import gebiete as gebiete_mod
from .fakten import ABLEITUNGEN, UNBEKANNT, EingabeFehler, abgeleitete_fakten, einstiegs_rueckfragen
from .fristen import BerechneteFrist, berechne
from .modell import (
    Abdeckung,
    Betrag,
    Ebene,
    Gebiet,
    Leistung,
    Leistungsvariante,
    Pruefstatus,
    Quelle,
    Zustaendigkeit,
)
from .regeln import Schritt, Wert, auswerten
from .wissensbasis import Wissensbasis

STANDARD_LEBENSLAGEN = ("geburt",)
WERT_RANG = {Wert.JA: 0, Wert.UNKLAR: 1, Wert.NEIN: 2}
PRUEF_RANG = {
    Pruefstatus.VERIFIZIERT: 0,
    Pruefstatus.TEILWEISE: 1,
    Pruefstatus.UNGEPRUEFT: 2,
    Pruefstatus.WIDERSPRUECHLICH: 3,
}
# Eine Frist gilt für die Reihenfolge der Fragen als nah, wenn sie in so vielen Tagen abläuft
NAHE_FRIST_TAGE = 30


@dataclass
class Anfrage:
    fakten: dict[str, Any]
    plz: Optional[str] = None
    gemeinde: Optional[str] = None
    land: Optional[str] = None
    lebenslagen: list[str] = field(default_factory=lambda: list(STANDARD_LEBENSLAGEN))
    stichtag: date = field(default_factory=date.today)


@dataclass
class PersonErgebnis:
    person: Optional[str]  # None = Haushalt, sonst ID der Rolle (z. B. "mutter")
    schritt: Schritt


@dataclass
class Eintrag:
    leistung: Leistung
    variante: Leistungsvariante
    gebiet: Gebiet
    abdeckung: Abdeckung
    zustaendigkeit: Zustaendigkeit
    ergebnis: Wert
    personen: list[PersonErgebnis]
    fristen: list[BerechneteFrist]
    betrag: Optional[Betrag]
    quellen: list[Quelle]
    pruefstatus: Pruefstatus
    fehlend: list[str]
    lebenslagen: list[str] = field(default_factory=list)  # gewählte Lebenslagen, zu denen die Leistung gehört

    @property
    def naechste_frist(self) -> Optional[date]:
        daten = [f.datum for f in self.fristen if f.datum and f.frist.art != "fruehestens"]
        return min(daten) if daten else None


@dataclass
class NurAndereLaender:
    """Landesleistung ohne Gegenstück am maßgeblichen Ort (z. B. Hessengeld für Bayern)."""

    leistung: Leistung
    laender: list[Gebiet]


@dataclass
class Bericht:
    anfrage: Anfrage
    hierarchie: list[Gebiet]
    eintraege: list[Eintrag]
    fehlend: list[str]
    warnungen: list[str]
    nur_andere_laender: list[NurAndereLaender] = field(default_factory=list)
    # Bewusst nicht erfasste Themen der gewählten Lebenslagen: (Lebenslage, Name, Begründung)
    nicht_erfasst: list[tuple[str, str, str]] = field(default_factory=list)

    def eintrag(self, leistung_id: str) -> Eintrag:
        for e in self.eintraege:
            if e.leistung.id == leistung_id:
                return e
        raise KeyError(leistung_id)

    def ergebnisse(self) -> dict[str, str]:
        """Kompakte Sicht ``leistung_id -> ja|nein|unklar`` (für Tests und Szenarien)."""
        return {e.leistung.id: e.ergebnis.value for e in self.eintraege}


def beste_variante(
    kb: Wissensbasis, leistung: Leistung, hierarchie: list[Gebiet], stichtag: date
) -> Optional[tuple[Leistungsvariante, Gebiet]]:
    """Spezifischste gültige Variante (Gemeinde vor Kreis vor Land vor Bund)."""
    varianten = [v for v in kb.varianten_von(leistung.id) if v.zeitraum.enthaelt(stichtag)]
    for gebiet in hierarchie:
        for v in varianten:
            if v.gebiet_id == gebiet.id:
                return v, gebiet
    return None


def _gesamt(werte: list[Wert]) -> Wert:
    if Wert.JA in werte:
        return Wert.JA
    if Wert.UNKLAR in werte:
        return Wert.UNKLAR
    return Wert.NEIN


def _betrag(leistung: Leistung, stichtag: date) -> Optional[Betrag]:
    for b in leistung.betraege:
        if b.zeitraum.enthaelt(stichtag):
            return b
    return None


def _anfuegen(liste: list[str], neue: list[str]) -> None:
    for f in neue:
        if f not in liste:
            liste.append(f)


def _sortieren(eintraege: list[Eintrag]) -> list[Eintrag]:
    """Topologisch nach Voraussetzungen; bei freier Wahl: Ergebnis, Frist, Pflicht, Name."""
    nach_id = {e.leistung.id: e for e in eintraege}

    def schluessel(e: Eintrag) -> tuple:
        frist = e.naechste_frist or date.max
        return (WERT_RANG[e.ergebnis], frist, e.leistung.art != "pflicht", e.leistung.name)

    offen = {
        e.leistung.id: {v for v in e.leistung.voraussetzungen if v in nach_id} for e in eintraege
    }
    bereit = [(schluessel(nach_id[i]), i) for i, vor in offen.items() if not vor]
    heapq.heapify(bereit)
    ergebnis: list[Eintrag] = []
    while bereit:
        _, lid = heapq.heappop(bereit)
        ergebnis.append(nach_id[lid])
        for andere, vor in offen.items():
            if lid in vor:
                vor.discard(lid)
                if not vor:
                    heapq.heappush(bereit, (schluessel(nach_id[andere]), andere))
    if len(ergebnis) != len(eintraege):
        raise ValueError("Zyklus in den Voraussetzungen der Leistungen")
    return ergebnis


def landesabdeckung(kb: Wissensbasis, land: Gebiet, lebenslage: str) -> Abdeckung:
    """ERFASST, wenn für das Land recherchiert ist, ob es eigene Leistungen gibt, sonst FEHLT."""
    return Abdeckung.ERFASST if (land.id, lebenslage) in kb.landesabdeckung else Abdeckung.FEHLT


def ort_platzhalter(hierarchie: list[Gebiet]) -> dict[str, str]:
    """Werte für Platzhalter in Zuständigkeiten, z. B. "Elterngeldstelle – {kreis}"."""
    nach_ebene = {g.ebene: g for g in hierarchie}
    return {
        "gemeinde": nach_ebene[Ebene.GEMEINDE].name if Ebene.GEMEINDE in nach_ebene else "Ihre Gemeinde",
        "kreis": nach_ebene[Ebene.KREIS].name if Ebene.KREIS in nach_ebene else "Ihr Landkreis bzw. Ihre kreisfreie Stadt",
        "land": nach_ebene[Ebene.LAND].name if Ebene.LAND in nach_ebene else "Ihr Bundesland",
    }


def zustaendigkeit_fuer_ort(
    z: Zustaendigkeit, hierarchie: list[Gebiet], werte: Optional[dict[str, str]] = None
) -> Zustaendigkeit:
    if "{" not in z.name and "{" not in (z.beschreibung or ""):
        return z
    werte = werte or ort_platzhalter(hierarchie)
    return replace(
        z,
        name=z.name.format_map(werte),
        beschreibung=z.beschreibung.format_map(werte) if z.beschreibung else None,
    )


def abdeckung_eintrag(leistung: Leistung, gebiet: Gebiet) -> Abdeckung:
    """ERFASST, wenn die Variante auf der Verwaltungsebene der Leistung (oder darunter) liegt."""
    return Abdeckung.ERFASST if gebiet.ebene.rang >= leistung.verwaltungsebene.rang else Abdeckung.ALLGEMEIN


def _warnungen(kb: Wissensbasis, anfrage: Anfrage, hierarchie: list[Gebiet], eintraege: list[Eintrag]) -> list[str]:
    warnungen: list[str] = []
    land = next((g for g in hierarchie if g.ebene is Ebene.LAND), None)
    gemeinde = next((g for g in hierarchie if g.ebene is Ebene.GEMEINDE), None)
    if land is not None:
        offen = [
            ll for ll in anfrage.lebenslagen
            if landesabdeckung(kb, land, ll) is Abdeckung.FEHLT and kb.hat_landesdaten(ll)
        ]
        if offen:
            welche = f" (Lebenslage {', '.join(kb.lebenslagen[ll].name for ll in offen)})" if len(anfrage.lebenslagen) > 1 else ""
            warnungen.append(
                f"Für {land.name} ist noch nicht erfasst, ob es eigene Landesleistungen gibt{welche}. "
                "Angezeigt werden Bundesleistungen und allgemeine Zuständigkeiten."
            )
    if gemeinde is None:
        warnungen.append(
            "Der Wohnort ist nicht als Gemeinde erfasst: Angaben zu Stellen vor Ort "
            "(z. B. Standesamt, Jugendamt) sind allgemein gehalten."
        )
    allgemein = [
        e.leistung.name for e in eintraege
        if e.abdeckung is Abdeckung.ALLGEMEIN and e.ergebnis is not Wert.NEIN and e.leistung.ortsbezug is None
    ]
    if gemeinde is not None and allgemein:
        warnungen.append(
            f"Für {gemeinde.name} ist die zuständige Stelle vor Ort noch nicht erfasst bei: "
            + ", ".join(allgemein)
            + ". Angezeigt wird, welche Art von Stelle zuständig ist – Adresse und Termine bitte dort erfragen."
        )
    return warnungen


def _lebenslagen_pruefen(kb: Wissensbasis, lebenslagen: list[str]) -> None:
    if not lebenslagen:
        raise EingabeFehler("Bitte mindestens eine Lebenslage angeben")
    unbekannt = [ll for ll in lebenslagen if ll not in kb.lebenslagen]
    if unbekannt:
        raise EingabeFehler(
            f"Unbekannte Lebenslage {', '.join(unbekannt)} (verfügbar: {', '.join(sorted(kb.lebenslagen))})"
        )


def _ort_der_leistung(
    kb: Wissensbasis, leistung: Leistung, fakten: dict[str, Any], wohnort: list[Gebiet], cache: dict[str, list[Gebiet]],
    einstieg: frozenset[str] = frozenset(),
) -> tuple[list[Gebiet], Optional[str]]:
    """Maßgebliche Gebietshierarchie und ggf. der fehlende Ortsfakt.

    Ist der Ort (z. B. der Immobilie) nicht bekannt, gilt nur der Bund: Landes-
    und Kommunalvarianten können dann nicht ausgewählt werden.

    Hat der Ortsfakt ein ``nur_wenn`` (z. B. Pflege: Ort der pflegebedürftigen
    Person nur, wenn ein Angehöriger gepflegt wird), dann gilt:

    - Bedingung offen: zuerst die Bedingung erfragen, nur der Bund gilt. Gehört
      die Bedingung nicht zu den Einstiegsfragen der gewählten Lebenslagen (z. B.
      Blindengeld bei Behinderung ohne Pflege), gilt der Wohnort.
    - Bedingung nicht erfüllt: Es gilt der Wohnort der Anfrage.
    - Bedingung "weiß nicht": nur der Bund, ohne Rückfrage. Der Ort wird nicht
      erfragt (die Frage passt dann womöglich nicht), und der Wohnort wird nicht
      angenommen (er könnte das falsche Land sein). Die Landesleistungen bleiben
      offen und erscheinen im Hinweis "lassen sich nicht prüfen".
    """
    if leistung.ortsbezug is None:
        return wohnort, None
    wert = fakten.get(leistung.ortsbezug)
    if wert is None:
        definition = kb.fakten.get(leistung.ortsbezug)
        bedingung = definition.nur_wenn if definition is not None else None
        if bedingung is not None:
            vorher = fakten.get(bedingung[0])
            if vorher is None:
                if bedingung[0] not in einstieg:
                    return wohnort, None
                return [gebiete_mod.bund(kb)], bedingung[0]
            if vorher is UNBEKANNT:
                return [gebiete_mod.bund(kb)], None
            if vorher != bedingung[1]:
                return wohnort, None
        return [gebiete_mod.bund(kb)], leistung.ortsbezug
    if not isinstance(wert, str):  # "weiß nicht"
        return [gebiete_mod.bund(kb)], None
    return _ort_hierarchie(kb, wert, cache), None


def _ort_hierarchie(kb: Wissensbasis, wert: str, cache: dict[str, list[Gebiet]]) -> list[Gebiet]:
    if wert not in cache:
        cache[wert] = gebiete_mod.hierarchie_fuer_ort(kb, wert)
    return cache[wert]


def _ortsvergleiche(
    kb: Wissensbasis, fakten: dict[str, Any], wohnort: list[Gebiet], cache: dict[str, list[Gebiet]]
) -> dict[str, Any]:
    """Abgeleitete Fakten wie "Umzug innerhalb derselben Gemeinde?" (Ortsfakt im Vergleich zum Wohnort).

    Ist der Ort "weiß nicht" oder lässt er sich auf der Ebene nicht eindeutig
    bestimmen (z. B. PLZ mit mehreren Gemeinden), ist das Ergebnis "weiß nicht".
    Fehlt der Ort, bleibt der Fakt offen; erfragt wird dann der Ort.
    """
    neu: dict[str, Any] = {}
    for d in kb.fakten.values():
        if d.ableitung is None or d.id in fakten:
            continue
        art, ort = d.ableitung
        wert = fakten.get(ort)
        if wert is None:
            continue
        if not isinstance(wert, str):
            neu[d.id] = UNBEKANNT
            continue
        ebene = Ebene(ABLEITUNGEN[art])
        dort = next((g for g in _ort_hierarchie(kb, wert, cache) if g.ebene is ebene), None)
        hier = next((g for g in wohnort if g.ebene is ebene), None)
        neu[d.id] = UNBEKANNT if dort is None or hier is None else dort.id == hier.id
    return neu


def _erfragbar(kb: Wissensbasis, fid: str, fakten: dict[str, Any]) -> Optional[str]:
    """Welche Frage klärt den fehlenden Fakt? Abgeleitete Fakten über ihre Quelle, sonst keine."""
    d = kb.fakt_definition(fid)
    if d is None or not d.abgeleitet:
        return fid
    if d.ableitung is not None and d.ableitung[1] not in fakten:
        return d.ableitung[1]
    return None


def _personen(
    kb: Wissensbasis,
    leistung: Leistung,
    regel: dict[str, Any],
    fakten: dict[str, Any],
    lebenslagen: Optional[set[str]] = None,
) -> tuple[list[tuple[Optional[str], dict[str, Any], bool]], list[str]]:
    """Wer wird geprüft? Liefert (Rolle, Regel, stumm) je Person und fehlende Vorbedingungen.

    ``stumm``: Ob es die Person gibt, ist "weiß nicht". Sie wird geprüft, das
    Ergebnis ist höchstens Unklar, und es gibt keine Rückfragen zu ihr.
    """
    if not leistung.fuer:
        return [(None, regel, False)], []
    personen: list[tuple[Optional[str], dict[str, Any], bool]] = []
    fehlend: list[str] = []
    for rid in leistung.fuer:
        rolle = kb.rollen[rid]
        if rolle.vorbedingung is None:
            personen.append((rid, regel, False))
            continue
        vor = auswerten(rolle.vorbedingung, fakten, lebenslagen=lebenslagen)
        mit_vorbedingung = {"alle": [rolle.vorbedingung, regel]}
        if vor.wert is Wert.JA:
            personen.append((rid, mit_vorbedingung, False))
        elif vor.wert is Wert.UNKLAR and vor.fehlend:
            _anfuegen(fehlend, vor.fehlend)
        elif vor.wert is Wert.UNKLAR:
            personen.append((rid, mit_vorbedingung, True))
    return personen, fehlend


def _gewicht(e: Eintrag, stichtag: date) -> int:
    """Wie wichtig ist es, die offenen Fragen dieses Eintrags zu klären?"""
    gewicht = 2 if e.ergebnis is Wert.UNKLAR else 1
    if e.leistung.art == "pflicht":
        gewicht += 1
    frist = e.naechste_frist
    if frist is not None and 0 <= (frist - stichtag).days <= NAHE_FRIST_TAGE:
        gewicht += 1
    return gewicht


def fragen_priorisieren(vorab: list[str], eintraege: list[Eintrag], stichtag: date) -> list[str]:
    """Reihenfolge der offenen Fragen.

    Zuerst ``vorab`` (Einstiegsfragen, Vorbedingungen von Rollen, Orte), dann die
    übrigen nach Entscheidungskraft: Summe der Gewichte aller Einträge, die eine
    Antwort entscheiden kann. Bei Gleichstand bleibt die Reihenfolge des Auftretens.
    """
    punkte: dict[str, int] = {}
    for e in eintraege:
        gewicht = _gewicht(e, stichtag)
        for f in e.fehlend:
            punkte[f] = punkte.get(f, 0) + gewicht
    reihenfolge = {f: i for i, f in enumerate(punkte)}
    rest = sorted((f for f in punkte if f not in vorab), key=lambda f: (-punkte[f], reihenfolge[f]))
    return list(vorab) + rest


def planen(kb: Wissensbasis, anfrage: Anfrage) -> Bericht:
    _lebenslagen_pruefen(kb, anfrage.lebenslagen)
    hierarchie = gebiete_mod.aufloesen(kb, anfrage.plz, anfrage.gemeinde, anfrage.land)
    fakten = dict(anfrage.fakten)
    fakten["wohnsitz_in_deutschland"] = True  # Ort wurde in Deutschland aufgelöst
    land = next((g for g in hierarchie if g.ebene is Ebene.LAND), None)
    if land is not None:
        fakten["wohnsitz_land"] = land.kuerzel
    fakten.update(abgeleitete_fakten(fakten))

    gewaehlt = set(anfrage.lebenslagen)
    orte: dict[str, list[Gebiet]] = {}
    fakten.update(_ortsvergleiche(kb, fakten, hierarchie, orte))
    einstiegsfragen = kb.einstiegsfragen(anfrage.lebenslagen)
    einstieg = frozenset(d.id for d in einstiegsfragen)
    vorab: list[str] = einstiegs_rueckfragen(einstiegsfragen, fakten)
    platzhalter: dict[int, dict[str, str]] = {}  # je Hierarchie (Wohnort, Orte von Leistungen) einmal
    eintraege: list[Eintrag] = []
    nur_andere: list[NurAndereLaender] = []
    ohne_ort: dict[str, list[str]] = {}  # Ortsfakt -> Landesleistungen, die ohne den Ort nicht prüfbar sind
    for leistung in kb.leistungen_fuer(anfrage.lebenslagen):
        ort, ort_fehlt = _ort_der_leistung(kb, leistung, fakten, hierarchie, orte, einstieg)
        if ort_fehlt and not getattr(kb.fakt_definition(ort_fehlt), "abgeleitet", False):
            _anfuegen(vorab, [ort_fehlt])
        treffer = beste_variante(kb, leistung, ort, anfrage.stichtag)
        if treffer is None:
            laender = _laender_mit_variante(kb, leistung, anfrage.stichtag)
            if laender and leistung.ortsbezug is not None and ort is not hierarchie and len(ort) == 1:
                # Ort der Leistung unbekannt: nicht "nur in anderen Ländern", sondern offen
                ohne_ort.setdefault(leistung.ortsbezug, []).append(leistung.name)
            elif laender:
                nur_andere.append(NurAndereLaender(leistung, laender))
            continue
        variante, gebiet = treffer
        personen, vorbedingungen_fehlen = _personen(kb, leistung, variante.regel, fakten, gewaehlt)
        _anfuegen(vorab, vorbedingungen_fehlen)
        if not personen:
            continue  # z. B. Leistung nur für den anderen Elternteil, der nicht im Haushalt lebt
        ergebnisse = [PersonErgebnis(rid, auswerten(regel, fakten, rid, gewaehlt)) for rid, regel, _ in personen]
        gesamt = _gesamt([r.schritt.wert for r in ergebnisse])
        # Rückfragen je Person; zu "stummen" Personen (gibt es sie? weiß nicht) wird nicht weiter gefragt
        eintrag_fehlend: list[str] = []
        for (_, _, stumm), r in zip(personen, ergebnisse):
            if not stumm:
                _anfuegen(eintrag_fehlend, r.schritt.fehlend)
        # Abgeleitete Fakten werden nicht direkt erfragt, sondern über ihre Quelle (z. B. den Ort)
        erfragbar = [_erfragbar(kb, f, fakten) for f in eintrag_fehlend]
        eintrag_fehlend = list(dict.fromkeys(f for f in erfragbar if f is not None))

        if id(ort) not in platzhalter:
            platzhalter[id(ort)] = ort_platzhalter(ort)
        quellen = [kb.quellen[q] for q in kb.quellen_von_variante(variante)]
        pruefstatus = max((q.pruefstatus for q in quellen), key=PRUEF_RANG.__getitem__)
        eintraege.append(
            Eintrag(
                leistung=leistung,
                variante=variante,
                gebiet=gebiet,
                abdeckung=abdeckung_eintrag(leistung, gebiet),
                zustaendigkeit=zustaendigkeit_fuer_ort(
                    kb.zustaendigkeiten[variante.zustaendigkeit_id],
                    ort,
                    platzhalter[id(ort)],
                ),
                ergebnis=gesamt,
                personen=ergebnisse,
                fristen=[
                    berechne(f, fakten, anfrage.stichtag)
                    for f in variante.verfahren.fristen
                    # Fristen vor dem Termin sind nach der Geburt gegenstandslos
                    if not (f.bezug == "termin" and fakten.get("kind_geboren") is True)
                ],
                betrag=_betrag(leistung, anfrage.stichtag),
                quellen=quellen,
                pruefstatus=pruefstatus,
                fehlend=eintrag_fehlend,
                lebenslagen=[ll for ll in anfrage.lebenslagen if ll in leistung.lebenslagen],
            )
        )
    sortiert = _sortieren(eintraege)
    warnungen = _warnungen(kb, anfrage, hierarchie, sortiert)
    for ortsfakt, namen in ohne_ort.items():
        definition = kb.fakten.get(ortsfakt)
        frage = definition.frage.split("?")[0].strip() if definition is not None and definition.frage else ""
        angabe = f"„{frage}?“" if frage else "dem Ort"
        warnungen.append(f"Ohne Angabe zu {angabe} lassen sich diese Landesleistungen nicht prüfen: {', '.join(namen)}.")
    return Bericht(
        anfrage,
        hierarchie,
        sortiert,
        fragen_priorisieren(vorab, eintraege, anfrage.stichtag),
        warnungen,
        nur_andere,
        [(ll, name, grund) for ll in anfrage.lebenslagen for name, grund in kb.lebenslagen[ll].nicht_erfasst],
    )


def _laender_mit_variante(kb: Wissensbasis, leistung: Leistung, stichtag: date) -> list[Gebiet]:
    """Länder mit einer gültigen Variante der Leistung auf Landesebene.

    Kommunale Leistungen (nur Varianten einzelner Gemeinden oder Kreise) zählen
    nicht: Sonst stünde z. B. die Leistung einer einzelnen Stadt für alle anderen
    Gemeinden ihres Landes als "nur in anderen Ländern" im Bericht.
    """
    laender = {
        v.gebiet_id: kb.gebiete[v.gebiet_id]
        for v in kb.varianten_von(leistung.id)
        if v.zeitraum.enthaelt(stichtag) and kb.gebiete[v.gebiet_id].ebene is Ebene.LAND
    }
    return sorted(laender.values(), key=lambda g: g.name)
