"""Lebenslage Pflege (Fachmodul Pflege, #41 Schritt 3)."""

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
PLZ_JE_LAND = {"08": "70173", "09": "80331", "11": "10115", "12": "14467", "04": "28195", "02": "20095", "06": "34225",
               "13": "19053", "03": "30159", "05": "40213", "07": "55116", "10": "66111", "14": "01067", "15": "39104",
               "01": "24103", "16": "99084"}


def angehoerig(**abweichungen: Any) -> dict[str, Any]:
    """Angestellte Person pflegt einen Angehörigen (Pflegegrad 3) zu Hause in München."""
    fakten: dict[str, Any] = {
        "pflege.rolle": "angehoerig", "pflege.pflegegrad": 3, "pflege.wohnform": "zuhause", "pflege.ort": "80331",
        "pflege.pflege_durch_angehoerige": "ja", "pflege.blind": "nein", "pflege.beschaeftigt": "ja",
        "pflege.beschaeftigte_arbeitgeber": 50, "pflege.akut": "nein", "pflege.pflegestunden": 14,
        "pflege.eigene_arbeitsstunden": 30,
    }
    for k, v in abweichungen.items():
        k = k.replace("__", ".")
        if v is None:
            fakten.pop(k, None)
        else:
            fakten[k] = v
    return fakten


def selbst(**abweichungen: Any) -> dict[str, Any]:
    fakten = angehoerig(**abweichungen)
    fakten["pflege.rolle"] = "selbst"
    for f in ("pflege.ort", "pflege.beschaeftigt", "pflege.beschaeftigte_arbeitgeber", "pflege.akut",
              "pflege.pflegestunden", "pflege.eigene_arbeitsstunden"):
        if f.replace(".", "__") not in abweichungen:
            fakten.pop(f, None)
    return fakten


@pytest.fixture
def plane_pfl(kb):
    def _plane(fakten: Optional[dict[str, Any]] = None, plz: str = "10115") -> Bericht:
        return planen(kb, Anfrage(fakten=fakten_parsen(kb, fakten or {}), plz=plz, lebenslagen=["pflege"], stichtag=STICHTAG))

    return _plane


# ------------------------------------------------------------------ Pflegeversicherung
@pytest.mark.anforderung("ANF-PFL-01")
def test_leistungen_nach_pflegegrad_und_wohnform(plane_pfl):
    e = lambda **f: plane_pfl(angehoerig(**f)).ergebnisse()
    assert e()["pflegegeld"] == "ja" and e()["pflegegrad_beantragen"] == "nein"
    assert e(pflege__pflegegrad=1)["pflegegeld"] == "nein" and e(pflege__pflegegrad=1)["entlastungsbetrag"] == "ja"
    assert e(pflege__pflegegrad=0)["pflegegrad_beantragen"] == "ja" and e(pflege__pflegegrad=0)["entlastungsbetrag"] == "nein"
    assert e(pflege__pflege_durch_angehoerige="nein")["pflegegeld"] == "nein"
    assert e(pflege__pflege_durch_angehoerige="nein")["pflegesachleistung"] == "ja"
    heim = e(pflege__wohnform="heim")
    assert heim["pflege_im_heim"] == "ja"
    assert all(heim[l] == "nein" for l in ("pflegegeld", "pflegesachleistung", "entlastungsbetrag", "wohnumfeld", "pflegehilfsmittel"))
    assert e()["hilfe_zur_pflege"] == "unklar"  # Einkommensprüfung beim Sozialamt
    b = plane_pfl(angehoerig())
    assert b.eintrag("pflegegeld").betrag.text.startswith("347 € (Pflegegrad 2)")
    assert b.eintrag("entlastungsbetrag").betrag.text == "bis 131 € im Monat"
    assert b.eintrag("pflegegeld").zustaendigkeit.name == "Pflegekasse der pflegebedürftigen Person"


# ------------------------------------------------------------------ Landespflegegeld und Ort
@pytest.mark.anforderung("ANF-PFL-02")
def test_landespflegegeld_bayern(plane_pfl):
    # Angehörige Person in Berlin, Pflegebedürftige in München
    b = plane_pfl(angehoerig())
    e = b.eintrag("landespflegegeld")
    assert e.ergebnis is Wert.JA and e.gebiet.name == "Bayern"
    assert e.zustaendigkeit.name == "Bayerisches Landesamt für Pflege (Amberg)"
    assert e.pruefstatus.value == "widerspruechlich"  # Antragsfrist in den Quellen widersprüchlich
    assert plane_pfl(angehoerig(pflege__pflegegrad=1)).ergebnisse()["landespflegegeld"] == "nein"
    # Pflegebedürftige in Köln: nur in anderen Ländern (Bayern)
    koeln = plane_pfl(angehoerig(pflege__ort="50667"))
    assert "landespflegegeld" not in koeln.ergebnisse()
    andere = {n.leistung.id: [g.kuerzel for g in n.laender] for n in koeln.nur_andere_laender}
    assert andere["landespflegegeld"] == ["BY"]


@pytest.mark.anforderung("ANF-PFL-03")
def test_ort_der_pflegebeduerftigen_person(plane_pfl):
    # Selbst pflegebedürftig: kein eigener Ort, es gilt der Wohnort
    muenchen = plane_pfl(selbst(), plz="80331")
    assert "pflege.ort" not in muenchen.fehlend
    assert muenchen.ergebnisse()["landespflegegeld"] == "ja"
    assert "landespflegegeld" not in plane_pfl(selbst(), plz="10115").ergebnisse()
    # Angehörige: der Ort wird direkt nach den Einstiegsfragen erfragt
    offen = plane_pfl(angehoerig(pflege__ort=None))
    assert offen.fehlend[0] == "pflege.ort"
    # Ohne Ort: Landesleistungen offen, nicht "nur in anderen Ländern"
    for b in (offen, plane_pfl(angehoerig(pflege__ort="unbekannt"))):
        assert b.nur_andere_laender == []
        assert any("Wo wohnt die pflegebedürftige Person?" in w and "Landespflegegeld" in w for w in b.warnungen), b.warnungen
    # Rolle "weiß nicht": Ort nicht erfragen, Wohnort nicht annehmen, Landesleistungen offen
    unklar = plane_pfl(angehoerig(pflege__rolle="unbekannt", pflege__ort=None), plz="80331")
    assert "pflege.ort" not in unklar.fehlend
    assert "landespflegegeld" not in unklar.ergebnisse() and unklar.nur_andere_laender == []
    assert any("Landespflegegeld" in w and "nicht prüfen" in w for w in unklar.warnungen), unklar.warnungen
    # Rolle noch offen: zuerst danach fragen
    ohne_rolle = plane_pfl({})
    assert ohne_rolle.fehlend[:3] == ["pflege.rolle", "pflege.pflegegrad", "pflege.wohnform"]


@pytest.mark.anforderung("ANF-PFL-04")
def test_leistungen_fuer_pflegepersonen_nur_bei_angehoerigen(plane_pfl):
    fuer_pflegepersonen = ("arbeitsverhinderung_pflege", "pflegeunterstuetzungsgeld", "pflegezeit", "familienpflegezeit",
                           "pflegezeit_darlehen", "rente_pflegeperson")
    b = plane_pfl(selbst(), plz="80331")
    assert all(b.ergebnisse()[l] == "nein" for l in fuer_pflegepersonen)
    assert not {"pflege.beschaeftigt", "pflege.akut", "pflege.pflegestunden"} & set(b.fehlend)
    # Rentenversicherung: mindestens 10 Stunden Pflege, höchstens 30 Stunden eigene Arbeit, Pflegegrad 2
    r = lambda **f: plane_pfl(angehoerig(**f)).ergebnisse()["rente_pflegeperson"]
    assert r() == "unklar"  # Altersrente wird geprüft
    assert r(pflege__pflegestunden=8) == "nein"
    assert r(pflege__eigene_arbeitsstunden=35) == "nein"
    assert r(pflege__pflegegrad=1) == "nein"


@pytest.mark.anforderung("ANF-PFL-05")
def test_freistellungen_nach_betriebsgroesse(plane_pfl):
    e = lambda **f: plane_pfl(angehoerig(**f)).ergebnisse()
    assert e()["pflegezeit"] == "ja" and e()["familienpflegezeit"] == "ja"
    assert e(pflege__beschaeftigte_arbeitgeber=20)["pflegezeit"] == "ja"
    assert e(pflege__beschaeftigte_arbeitgeber=20)["familienpflegezeit"] == "nein"
    assert e(pflege__beschaeftigte_arbeitgeber=15)["pflegezeit"] == "nein"
    # Zehn Arbeitstage bei akutem Pflegefall gelten in jedem Betrieb
    klein = e(pflege__beschaeftigte_arbeitgeber=3, pflege__akut="ja")
    assert klein["arbeitsverhinderung_pflege"] == "ja" and klein["pflegeunterstuetzungsgeld"] == "unklar"
    assert e()["arbeitsverhinderung_pflege"] == "nein"  # nicht akut
    assert e(pflege__beschaeftigt="nein")["pflegezeit"] == "nein"
    b = plane_pfl(angehoerig())
    assert [f.frist.text for f in b.eintrag("pflegezeit").fristen] == ["Spätestens zehn Arbeitstage vor Beginn schriftlich ankündigen"]
    assert [f.frist.text for f in b.eintrag("familienpflegezeit").fristen] == ["Spätestens acht Wochen vor Beginn schriftlich ankündigen"]


# ------------------------------------------------------------------ Länder
@pytest.mark.anforderung("ANF-PFL-06")
def test_blindengeld_in_allen_laendern(kb, plane_pfl):
    stellen = set()
    for land_id, plz in PLZ_JE_LAND.items():
        b = plane_pfl(selbst(pflege__blind="ja"), plz=plz)
        e = b.eintrag("landesblindengeld")
        assert e.ergebnis is Wert.JA and e.gebiet.id == land_id, plz
        assert e.quellen and all(q.url for q in e.quellen), plz
        stellen.add(e.zustaendigkeit.name)
        assert plane_pfl(selbst(pflege__blind="nein"), plz=plz).ergebnisse()["landesblindengeld"] == "nein"
    assert len(stellen) >= 10  # je Land eigene Stelle (Kreise, Landesämter, Landschaftsverband ...)


@pytest.mark.anforderung("ANF-PFL-06")
def test_pflegewohngeld_nur_in_drei_laendern(plane_pfl):
    for plz in ("40213", "24103", "19053"):  # NRW, Schleswig-Holstein, Mecklenburg-Vorpommern
        assert plane_pfl(selbst(pflege__wohnform="heim", pflege__pflegegrad=3), plz=plz).ergebnisse()["pflegewohngeld"] == "unklar", plz
        assert plane_pfl(selbst(), plz=plz).ergebnisse()["pflegewohngeld"] == "nein", plz  # zu Hause
    assert plane_pfl(selbst(pflege__wohnform="heim", pflege__pflegegrad=1), plz="40213").ergebnisse()["pflegewohngeld"] == "nein"
    berlin = plane_pfl(selbst(pflege__wohnform="heim"), plz="10115")
    assert "pflegewohngeld" not in berlin.ergebnisse()
    andere = {n.leistung.id: [g.kuerzel for g in n.laender] for n in berlin.nur_andere_laender}
    assert sorted(andere["pflegewohngeld"]) == ["MV", "NW", "SH"]


@pytest.mark.anforderung("ANF-PFL-07")
def test_unbekannt_bleibt_unklar(plane_pfl):
    b = plane_pfl(angehoerig(pflege__pflegegrad="unbekannt"))
    for l in ("pflegegrad_beantragen", "pflegegeld", "entlastungsbetrag", "landespflegegeld"):
        assert b.ergebnisse()[l] == "unklar", l
    # Widersprüchliche Quellen sind gekennzeichnet (Blindengeld Berlin)
    assert plane_pfl(selbst(pflege__blind="ja"), plz="10115").eintrag("landesblindengeld").pruefstatus.value == "widerspruechlich"


@pytest.mark.anforderung("ANF-PFL-07", "ANF-WEB-08")
def test_szenarien_pflege(kb):
    pflege = [s for s in szenarien_mod.alle(kb) if "pflege" in s.anfrage.lebenslagen]
    assert len(pflege) >= 3
    assert any("unklar" in s.erwartet.values() for s in pflege)
    # Mindestens ein Szenario außerhalb Bayerns (Land mit dem Landespflegegeld)
    assert any(not s.anfrage.plz.startswith(("8", "9")) and s.anfrage.fakten.get("pflege.rolle") == "selbst" for s in pflege)
    for s in pflege:
        assert szenarien_mod.abweichungen(s, planen(kb, s.anfrage)) == [], s.id


@pytest.mark.anforderung("ANF-PFL-08")
def test_alle_laender_recherchiert(kb, plane_pfl):
    for land in gebiete.laender(kb):
        nachweis = kb.landesabdeckung[(land.id, "pflege")]
        assert nachweis.landesleistungen == "erfasst", land.name
        assert nachweis.quellen and nachweis.notiz
    for plz in PLZ_JE_LAND.values():
        assert not any("noch nicht erfasst, ob es eigene Landesleistungen" in w for w in plane_pfl(selbst(), plz=plz).warnungen), plz
