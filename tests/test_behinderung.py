"""Lebenslage Behinderung (Fachmodul Behinderung, #41 Schritt 6)."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

import pytest

from buergerai import gebiete
from buergerai import szenarien as szenarien_mod
from buergerai.planer import Anfrage, Bericht, planen
from buergerai.regeln import Wert
from buergerai.szenarien import fakten_parsen

STICHTAG = date(2026, 10, 26)
PLZ = {"08": "70173", "09": "80331", "11": "10115", "12": "14467", "04": "28195", "02": "20095", "06": "34225", "13": "19053",
       "03": "30159", "05": "40213", "07": "55116", "10": "66111", "14": "01067", "15": "39104", "01": "24103", "16": "99084"}


def person(**abweichungen: Any) -> dict[str, Any]:
    """GdB 50 ohne Merkzeichen, angestellt, kein Auto."""
    fakten: dict[str, Any] = {
        "behinderung.gdb": 50, "behinderung.merkzeichen_g": "nein", "behinderung.merkzeichen_ag": "nein", "behinderung.merkzeichen_h": "nein",
        "pflege.blind": "nein", "behinderung.merkzeichen_gl": "nein", "behinderung.merkzeichen_rf": "nein",
        "behinderung.beschaeftigt": "ja", "behinderung.kfz_halter": "nein", "arbeitsuchend_gemeldet": "nein",
    }
    for k, v in abweichungen.items():
        k = k.replace("__", ".")
        if v is None:
            fakten.pop(k, None)
        else:
            fakten[k] = v
    return fakten


@pytest.fixture
def plane_beh(kb):
    def _plane(fakten: Optional[dict[str, Any]] = None, plz: str = "80331", lebenslagen=("behinderung",)) -> Bericht:
        return planen(kb, Anfrage(fakten=fakten_parsen(kb, fakten or {}), plz=plz, lebenslagen=list(lebenslagen), stichtag=STICHTAG))

    return _plane


@pytest.mark.anforderung("ANF-BEH-01")
def test_feststellung_je_land(plane_beh):
    stellen = set()
    for land_id, plz in PLZ.items():
        e = plane_beh(person(behinderung__gdb=0), plz=plz).eintrag("behinderung_feststellen")
        assert e.ergebnis is Wert.JA and e.gebiet.id == land_id, plz
        stellen.add(e.zustaendigkeit.name)
    assert len(stellen) == 16  # jedes Land hat eine eigene Stelle
    # Kommunal zuständige Länder nennen Kreis bzw. Stadt
    assert "Kreisfreie Stadt Köln" in plane_beh(person(behinderung__gdb=0), plz="50667").eintrag("behinderung_feststellen").zustaendigkeit.name
    assert plane_beh(person()).ergebnisse()["behinderung_feststellen"] == "nein"
    assert plane_beh({}).fehlend[0] == "behinderung.gdb"


@pytest.mark.anforderung("ANF-BEH-02")
def test_wertmarke(plane_beh):
    e = lambda **f: plane_beh(person(**f)).ergebnisse()["wertmarke_freifahrt"]
    assert e() == "nein"  # ohne Merkzeichen
    for mz in ("behinderung__merkzeichen_g", "behinderung__merkzeichen_ag", "behinderung__merkzeichen_h", "pflege__blind", "behinderung__merkzeichen_gl"):
        assert e(**{mz: "ja"}) == "ja", mz
    assert e(behinderung__gdb=40, behinderung__merkzeichen_g="ja") == "nein"
    assert plane_beh(person(behinderung__merkzeichen_g="ja")).eintrag("wertmarke_freifahrt").zustaendigkeit.name.startswith("Zentrum Bayern Familie und Soziales")


@pytest.mark.anforderung("ANF-BEH-03")
def test_kfz_parkausweis_rundfunk(plane_beh):
    e = lambda **f: plane_beh(person(behinderung__kfz_halter="ja", **f)).ergebnisse()
    assert e(behinderung__merkzeichen_h="ja")["kfz_steuer_behinderung"] == "ja"
    assert e(behinderung__merkzeichen_g="ja")["kfz_steuer_behinderung"] == "unklar"  # nur statt Freifahrt
    assert e()["kfz_steuer_behinderung"] == "nein"
    assert plane_beh(person(behinderung__merkzeichen_h="ja")).ergebnisse()["kfz_steuer_behinderung"] == "nein"  # kein Auto
    assert e(behinderung__merkzeichen_ag="ja")["parkausweis_blau"] == "ja"
    assert e(pflege__blind="ja")["parkausweis_blau"] == "ja"
    assert e(behinderung__merkzeichen_g="ja")["parkausweis_blau"] == "nein"
    assert e(behinderung__merkzeichen_rf="ja")["rundfunk_ermaessigung"] == "ja"
    assert e()["rundfunk_ermaessigung"] == "nein"


@pytest.mark.anforderung("ANF-BEH-04")
def test_arbeit_zusatzurlaub_gleichstellung(plane_beh):
    e = lambda **f: plane_beh(person(**f)).ergebnisse()
    assert e()["zusatzurlaub"] == "ja" and e()["gleichstellung"] == "nein"
    assert e(behinderung__beschaeftigt="nein")["zusatzurlaub"] == "nein"
    vierzig = e(behinderung__gdb=40)
    assert vierzig["zusatzurlaub"] == "nein" and vierzig["gleichstellung"] == "unklar"
    assert e(behinderung__gdb=40, behinderung__beschaeftigt="nein", arbeitsuchend_gemeldet="ja")["gleichstellung"] == "unklar"
    assert e(behinderung__gdb=20)["gleichstellung"] == "nein"


@pytest.mark.anforderung("ANF-BEH-05")
def test_blindengeld_ohne_pflegefrage(kb, plane_beh):
    # Nur Behinderung gewählt: Blindengeld am Wohnort, keine Frage, wer pflegebedürftig ist
    b = plane_beh(person(pflege__blind="ja"), plz="50667")
    e = b.eintrag("landesblindengeld")
    assert e.ergebnis is Wert.JA and e.gebiet.name == "Nordrhein-Westfalen"
    assert "pflege.rolle" not in b.fehlend and "pflege.ort" not in b.fehlend
    assert e.lebenslagen == ["behinderung"]
    # Pflege und Behinderung zusammen: erst die Pflegefrage, dann erscheint die Leistung einmal
    beide = plane_beh(person(pflege__blind="ja"), plz="50667", lebenslagen=("behinderung", "pflege"))
    assert beide.fehlend[0] == "pflege.rolle"
    beide = plane_beh(person(**{"pflege.blind": "ja", "pflege.rolle": "selbst"}), plz="50667", lebenslagen=("behinderung", "pflege"))
    assert [x.leistung.id for x in beide.eintraege].count("landesblindengeld") == 1
    assert beide.eintrag("landesblindengeld").lebenslagen == ["behinderung", "pflege"]
    # Abdeckung für alle Länder belegt
    for land in gebiete.laender(kb):
        nachweis = kb.landesabdeckung[(land.id, "behinderung")]
        assert nachweis.landesleistungen == "erfasst" and len(nachweis.quellen) == 2, land.name


@pytest.mark.anforderung("ANF-BEH-06")
def test_unbekannt_bleibt_unklar(plane_beh):
    b = plane_beh(person(behinderung__gdb="unbekannt"))
    assert b.ergebnisse()["behinderung_feststellen"] == "unklar"
    assert b.ergebnisse()["zusatzurlaub"] == "unklar"
    assert plane_beh(person(behinderung__merkzeichen_g="ja", behinderung__beschaeftigt="unbekannt")).ergebnisse()["zusatzurlaub"] == "unklar"
    # Thüringen: widersprüchliche Angaben zur zuständigen Stelle sind gekennzeichnet
    th = plane_beh(person(behinderung__gdb=0), plz="99084").eintrag("behinderung_feststellen")
    assert th.pruefstatus.value == "widerspruechlich"


@pytest.mark.anforderung("ANF-BEH-07", "ANF-WEB-08")
def test_szenarien_behinderung(kb):
    szen = [s for s in szenarien_mod.alle(kb) if "behinderung" in s.anfrage.lebenslagen]
    assert len(szen) >= 3
    assert any("unklar" in s.erwartet.values() for s in szen)
    for s in szen:
        assert szenarien_mod.abweichungen(s, planen(kb, s.anfrage)) == [], s.id
