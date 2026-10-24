"""Orchestrator: aus Anfrage (Ort, Ereignis, Fakten) wird ein priorisierter Bericht."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from . import gebiete as gebiete_mod
from .fakten import abgeleitete_fakten, grund_rueckfragen
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

WERT_RANG = {Wert.JA: 0, Wert.UNKLAR: 1, Wert.NEIN: 2}
PRUEF_RANG = {
    Pruefstatus.VERIFIZIERT: 0,
    Pruefstatus.TEILWEISE: 1,
    Pruefstatus.UNGEPRUEFT: 2,
    Pruefstatus.WIDERSPRUECHLICH: 3,
}


@dataclass
class Anfrage:
    fakten: dict[str, Any]
    plz: Optional[str] = None
    gemeinde: Optional[str] = None
    land: Optional[str] = None
    ereignis: str = "geburt"
    stichtag: date = field(default_factory=date.today)


@dataclass
class PersonErgebnis:
    person: Optional[str]  # None = Haushalt, sonst "mutter"/"partner"
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

    @property
    def naechste_frist(self) -> Optional[date]:
        daten = [f.datum for f in self.fristen if f.datum and f.frist.art != "fruehestens"]
        return min(daten) if daten else None


@dataclass
class Bericht:
    anfrage: Anfrage
    hierarchie: list[Gebiet]
    eintraege: list[Eintrag]
    fehlend: list[str]
    warnungen: list[str]

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


def planen(kb: Wissensbasis, anfrage: Anfrage) -> Bericht:
    hierarchie = gebiete_mod.aufloesen(kb, anfrage.plz, anfrage.gemeinde, anfrage.land)
    fakten = dict(anfrage.fakten)
    fakten["wohnsitz_in_deutschland"] = True  # Ort wurde in Deutschland aufgelöst
    land = next((g for g in hierarchie if g.ebene is Ebene.LAND), None)
    if land is not None:
        fakten["wohnsitz_land"] = land.kuerzel
    fakten.update(abgeleitete_fakten(fakten))

    warnungen: list[str] = []
    gemeinde = next((g for g in hierarchie if g.ebene is Ebene.GEMEINDE), None)
    if land is not None and not land.pilot:
        warnungen.append(
            f"{land.name} ist kein Pilotland: Landesleistungen und landesspezifische "
            "Zuständigkeiten sind nicht erfasst. Angezeigt werden nur Bundesdaten."
        )
    if gemeinde is None:
        warnungen.append(
            "Der Wohnort ist nicht als Gemeinde erfasst: kommunale Angaben "
            "(z. B. Standesamt vor Ort) fehlen."
        )
    elif not gemeinde.pilot:
        warnungen.append(f"{gemeinde.name} ist keine Pilotkommune: kommunale Angaben fehlen.")

    personen_haushalt: list[str] = ["mutter"]
    fehlend: list[str] = grund_rueckfragen(list(kb.fakten.values()), fakten)
    if fakten.get("partner_im_haushalt") is True:
        personen_haushalt.append("partner")

    eintraege: list[Eintrag] = []
    for leistung in sorted(kb.leistungen.values(), key=lambda l: l.id):
        if anfrage.ereignis not in leistung.ereignisse:
            continue
        treffer = beste_variante(kb, leistung, hierarchie, anfrage.stichtag)
        if treffer is None:
            continue
        variante, gebiet = treffer
        if leistung.fuer == "jeder_elternteil":
            if "partner_im_haushalt" not in fakten:
                _anfuegen(fehlend, ["partner_im_haushalt"])
            personen: list[Optional[str]] = list(personen_haushalt)
        else:
            personen = [None]
        ergebnisse = [PersonErgebnis(p, auswerten(variante.regel, fakten, p)) for p in personen]
        gesamt = _gesamt([r.schritt.wert for r in ergebnisse])
        # Rückfragen je Person: Bei "jeder_elternteil" zählt jede Person einzeln
        eintrag_fehlend: list[str] = []
        for r in ergebnisse:
            _anfuegen(eintrag_fehlend, r.schritt.fehlend)
        # Abgeleitete Fakten werden nicht direkt erfragt, sondern über Grunddaten
        eintrag_fehlend = [
            f for f in eintrag_fehlend if not getattr(kb.fakt_definition(f), "abgeleitet", False)
        ]
        _anfuegen(fehlend, eintrag_fehlend)

        abdeckung = (
            Abdeckung.VOLLSTAENDIG
            if gebiet.ebene.rang >= leistung.verwaltungsebene.rang
            else Abdeckung.ALLGEMEIN
        )
        quellen = [kb.quellen[q] for q in kb.quellen_von_variante(variante)]
        pruefstatus = max((q.pruefstatus for q in quellen), key=PRUEF_RANG.__getitem__)
        eintraege.append(
            Eintrag(
                leistung=leistung,
                variante=variante,
                gebiet=gebiet,
                abdeckung=abdeckung,
                zustaendigkeit=kb.zustaendigkeiten[variante.zustaendigkeit_id],
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
            )
        )
    return Bericht(anfrage, hierarchie, _sortieren(eintraege), fehlend, warnungen)
