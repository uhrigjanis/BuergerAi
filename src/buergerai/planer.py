"""Orchestrator: aus Anfrage (Ort, Ereignis, Fakten) wird ein priorisierter Bericht."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any, Optional

from . import gebiete as gebiete_mod
from .fakten import UNBEKANNT, abgeleitete_fakten, grund_rueckfragen
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


# Vorbedingung für alle Prüfungen des anderen Elternteils
PARTNER_IM_HAUSHALT: dict[str, Any] = {
    "fakt": "partner_im_haushalt",
    "op": "==",
    "wert": True,
    "text": "Der andere Elternteil lebt im Haushalt",
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


def _hat_landesdaten(kb: Wissensbasis, ereignis: str) -> bool:
    """Gibt es für das Ereignis irgendwo Varianten unterhalb der Bundesebene?

    Nur dann kann in einem Land ohne Recherche tatsächlich etwas fehlen.
    """
    return any(
        ereignis in kb.leistungen[v.leistung_id].ereignisse
        and kb.gebiete[v.gebiet_id].ebene is not Ebene.BUND
        for v in kb.varianten.values()
    )


def landesabdeckung(kb: Wissensbasis, land: Gebiet, ereignis: str) -> Abdeckung:
    """ERFASST, wenn für das Land recherchiert ist, ob es eigene Leistungen gibt, sonst FEHLT."""
    return Abdeckung.ERFASST if (land.id, ereignis) in kb.landesabdeckung else Abdeckung.FEHLT


def ort_platzhalter(hierarchie: list[Gebiet]) -> dict[str, str]:
    """Werte für Platzhalter in Zuständigkeiten, z. B. "Elterngeldstelle – {kreis}"."""
    nach_ebene = {g.ebene: g for g in hierarchie}
    return {
        "gemeinde": nach_ebene[Ebene.GEMEINDE].name if Ebene.GEMEINDE in nach_ebene else "Ihre Gemeinde",
        "kreis": nach_ebene[Ebene.KREIS].name if Ebene.KREIS in nach_ebene else "Ihr Landkreis bzw. Ihre kreisfreie Stadt",
        "land": nach_ebene[Ebene.LAND].name if Ebene.LAND in nach_ebene else "Ihr Bundesland",
    }


def zustaendigkeit_fuer_ort(z: Zustaendigkeit, hierarchie: list[Gebiet]) -> Zustaendigkeit:
    werte = ort_platzhalter(hierarchie)
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
    if (
        land is not None
        and landesabdeckung(kb, land, anfrage.ereignis) is Abdeckung.FEHLT
        and _hat_landesdaten(kb, anfrage.ereignis)
    ):
        warnungen.append(
            f"Für {land.name} ist noch nicht erfasst, ob es eigene Landesleistungen gibt. "
            "Angezeigt werden Bundesleistungen und allgemeine Zuständigkeiten."
        )
    if gemeinde is None:
        warnungen.append(
            "Der Wohnort ist nicht als Gemeinde erfasst: Angaben zu Stellen vor Ort "
            "(z. B. Standesamt, Jugendamt) sind allgemein gehalten."
        )
    allgemein = [e.leistung.name for e in eintraege if e.abdeckung is Abdeckung.ALLGEMEIN and e.ergebnis is not Wert.NEIN]
    if gemeinde is not None and allgemein:
        warnungen.append(
            f"Für {gemeinde.name} ist die zuständige Stelle vor Ort noch nicht erfasst bei: "
            + ", ".join(allgemein)
            + ". Angezeigt wird, welche Art von Stelle zuständig ist – Adresse und Termine bitte dort erfragen."
        )
    return warnungen


def planen(kb: Wissensbasis, anfrage: Anfrage) -> Bericht:
    hierarchie = gebiete_mod.aufloesen(kb, anfrage.plz, anfrage.gemeinde, anfrage.land)
    fakten = dict(anfrage.fakten)
    fakten["wohnsitz_in_deutschland"] = True  # Ort wurde in Deutschland aufgelöst
    land = next((g for g in hierarchie if g.ebene is Ebene.LAND), None)
    if land is not None:
        fakten["wohnsitz_land"] = land.kuerzel
    fakten.update(abgeleitete_fakten(fakten))

    fehlend: list[str] = grund_rueckfragen(list(kb.fakten.values()), fakten)
    # Der andere Elternteil wird geprüft, wenn er im Haushalt lebt oder das unklar ist.
    # Bei "weiß nicht" kann sein Ergebnis höchstens Unklar sein (siehe PARTNER_IM_HAUSHALT).
    partner_unklar = fakten.get("partner_im_haushalt") is UNBEKANNT
    personen_haushalt: list[str] = ["mutter"]
    if fakten.get("partner_im_haushalt") is True or partner_unklar:
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
        ergebnisse = [
            PersonErgebnis(
                p,
                auswerten({"alle": [PARTNER_IM_HAUSHALT, variante.regel]} if p == "partner" else variante.regel, fakten, p),
            )
            for p in personen
        ]
        gesamt = _gesamt([r.schritt.wert for r in ergebnisse])
        # Rückfragen je Person: Bei "jeder_elternteil" zählt jede Person einzeln.
        # Ist offen, ob der andere Elternteil im Haushalt lebt, wird er nicht weiter befragt.
        eintrag_fehlend: list[str] = []
        for r in ergebnisse:
            if r.person == "partner" and partner_unklar:
                continue
            _anfuegen(eintrag_fehlend, r.schritt.fehlend)
        # Abgeleitete Fakten werden nicht direkt erfragt, sondern über Grunddaten
        eintrag_fehlend = [
            f for f in eintrag_fehlend if not getattr(kb.fakt_definition(f), "abgeleitet", False)
        ]
        _anfuegen(fehlend, eintrag_fehlend)

        abdeckung = abdeckung_eintrag(leistung, gebiet)
        quellen = [kb.quellen[q] for q in kb.quellen_von_variante(variante)]
        pruefstatus = max((q.pruefstatus for q in quellen), key=PRUEF_RANG.__getitem__)
        eintraege.append(
            Eintrag(
                leistung=leistung,
                variante=variante,
                gebiet=gebiet,
                abdeckung=abdeckung,
                zustaendigkeit=zustaendigkeit_fuer_ort(kb.zustaendigkeiten[variante.zustaendigkeit_id], hierarchie),
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
    sortiert = _sortieren(eintraege)
    return Bericht(anfrage, hierarchie, sortiert, fehlend, _warnungen(kb, anfrage, hierarchie, sortiert))
