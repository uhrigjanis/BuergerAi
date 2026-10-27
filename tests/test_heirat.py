"""Lebenslage Heirat (Fachmodul Partnerschaft, #41 Schritt 6)."""

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


def paar(**abweichungen: Any) -> dict[str, Any]:
    fakten: dict[str, Any] = {"partnerschaft.stand": "geplant", "partnerschaft.datum": "2027-06-15", "partnerschaft.name_aendert": "ja",
                              "partnerschaft.arbeitnehmer": "einer", "partnerschaft.gering_verdienend": "ja", "partnerschaft.anderer_gkv": "ja"}
    for k, v in abweichungen.items():
        k = k.replace("__", ".")
        if v is None:
            fakten.pop(k, None)
        else:
            fakten[k] = v
    return fakten


@pytest.fixture
def plane_h(kb):
    def _plane(fakten: Optional[dict[str, Any]] = None, plz: str = "10115") -> Bericht:
        return planen(kb, Anfrage(fakten=fakten_parsen(kb, fakten or {}), plz=plz, lebenslagen=["heirat"], stichtag=STICHTAG))

    return _plane


@pytest.mark.anforderung("ANF-HEI-01")
def test_eheschliessung_anmelden(plane_h):
    b = plane_h(paar())
    e = b.eintrag("eheschliessung_anmelden")
    assert e.ergebnis is Wert.JA
    assert e.fristen[0].datum == date(2026, 12, 15) and e.fristen[0].frist.art == "fruehestens"
    assert e.zustaendigkeit.name == "Standesamt – Berlin"
    assert plane_h(paar(partnerschaft__stand="verheiratet")).ergebnisse()["eheschliessung_anmelden"] == "nein"
    assert plane_h({}).fehlend[:2] == ["partnerschaft.stand", "partnerschaft.datum"]


@pytest.mark.anforderung("ANF-HEI-02")
def test_ausweis_bei_namensaenderung(plane_h):
    e = plane_h(paar()).eintrag("ausweis_neuer_name")
    assert e.ergebnis is Wert.JA and e.leistung.art == "pflicht"
    assert e.fristen[0].datum == date(2027, 4, 20)  # acht Wochen vor der Trauung
    assert plane_h(paar(partnerschaft__name_aendert="nein")).ergebnisse()["ausweis_neuer_name"] == "nein"


@pytest.mark.anforderung("ANF-HEI-03")
def test_steuerklassen(plane_h):
    e = lambda wer: plane_h(paar(partnerschaft__arbeitnehmer=wer)).ergebnisse()["steuerklasse_ehe"]
    assert e("einer") == "ja"
    assert e("beide") == "unklar"
    assert e("keiner") == "nein"


@pytest.mark.anforderung("ANF-HEI-04")
def test_familienversicherung(plane_h):
    e = lambda **f: plane_h(paar(**f)).ergebnisse()["familienversicherung_ehe"]
    assert e() == "ja"
    assert e(partnerschaft__anderer_gkv="nein") == "nein"
    assert e(partnerschaft__anderer_gkv="unbekannt") == "unklar"
    assert e(partnerschaft__gering_verdienend="nein", partnerschaft__anderer_gkv=None) == "nein"
    assert "partnerschaft.anderer_gkv" not in plane_h(paar(partnerschaft__gering_verdienend="nein", partnerschaft__anderer_gkv=None)).fehlend
    assert "partnerschaft.anderer_gkv" in plane_h(paar(partnerschaft__anderer_gkv=None)).fehlend


@pytest.mark.anforderung("ANF-HEI-05")
def test_keine_landesleistung_je_land(kb, plane_h):
    quellen = set()
    for land in gebiete.laender(kb):
        nachweis = kb.landesabdeckung[(land.id, "heirat")]
        assert nachweis.landesleistungen == "keine" and len(nachweis.quellen) == 1 and "Bundesrecht" in nachweis.notiz, land.name
        assert kb.landesleistungen(land.id, "heirat") == []
        quellen.update(nachweis.quellen)
    assert len(quellen) == 16  # jedes Land mit eigener Quelle
    b = plane_h(paar(), plz="80331")
    assert not b.nur_andere_laender
    assert all(e.gebiet.id == "DE" for e in b.eintraege)


@pytest.mark.anforderung("ANF-HEI-06", "ANF-WEB-08")
def test_szenarien_heirat(kb):
    szen = [s for s in szenarien_mod.alle(kb) if "heirat" in s.anfrage.lebenslagen]
    assert len(szen) >= 3
    assert any("unklar" in s.erwartet.values() for s in szen)
    for s in szen:
        assert szenarien_mod.abweichungen(s, planen(kb, s.anfrage)) == [], s.id


def ausland(**abweichungen: Any) -> dict[str, Any]:
    werte: dict[str, Any] = {"partnerschaft__stand": "verheiratet", "partnerschaft__datum": "2026-08-20", "partnerschaft__heiratsort": "ausland",
                             "partnerschaft__ein_partner_deutsch": "ja"}
    werte.update(abweichungen)
    return paar(**werte)


@pytest.mark.anforderung("ANF-HEI-07")
def test_auslandsehe_beurkunden(plane_h):
    b = plane_h(ausland())
    e = b.eintrag("auslandsehe_beurkunden")
    assert e.ergebnis is Wert.JA and e.leistung.rechtsanspruch
    assert "Standesamt I in Berlin" in e.zustaendigkeit.name
    assert b.ergebnisse()["eheschliessung_anmelden"] == "nein"
    r = lambda **f: plane_h(ausland(**f)).ergebnisse()["auslandsehe_beurkunden"]
    assert r(partnerschaft__ein_partner_deutsch="nein") == "nein"
    assert r(partnerschaft__ein_partner_deutsch="unbekannt") == "unklar"
    assert r(partnerschaft__heiratsort="inland", partnerschaft__ein_partner_deutsch=None) == "nein"
    # Heiratsort nur nach der Hochzeit, Staatsangehörigkeit nur bei Heirat im Ausland gefragt
    geplant = plane_h(paar())
    assert "partnerschaft.heiratsort" not in geplant.fehlend and "partnerschaft.ein_partner_deutsch" not in geplant.fehlend
    assert geplant.ergebnisse()["auslandsehe_beurkunden"] == "nein"
    inland = plane_h(paar(partnerschaft__stand="verheiratet", partnerschaft__heiratsort="inland"))
    assert "partnerschaft.ein_partner_deutsch" not in inland.fehlend
    assert plane_h(paar(partnerschaft__stand="verheiratet", partnerschaft__heiratsort=None)).fehlend[0] == "partnerschaft.heiratsort"


@pytest.mark.anforderung("ANF-HEI-08")
def test_ehename_nach_auslandsheirat(plane_h):
    e = lambda **f: plane_h(ausland(**f)).ergebnisse()["ehename_erklaeren"]
    assert e() == "ja"
    assert e(partnerschaft__name_aendert="nein") == "nein"
    assert e(partnerschaft__ein_partner_deutsch="nein") == "nein"
    assert e(partnerschaft__heiratsort="inland", partnerschaft__ein_partner_deutsch=None) == "nein"  # Name wird bei der Trauung bestimmt
    ohne_deutsch = plane_h(ausland(partnerschaft__ein_partner_deutsch="nein")).ergebnisse()
    assert ohne_deutsch["auslandsehe_beurkunden"] == "nein" and ohne_deutsch["ehename_erklaeren"] == "nein"
