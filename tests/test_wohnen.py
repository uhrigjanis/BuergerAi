"""Lebenslage Wohneigentum (Fachmodul Wohnen, #41 Schritt 4)."""

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
# Land -> (PLZ, Steuersatz laut Übersicht)
LAENDER = {"08": ("70173", "5,0"), "09": ("80331", "3,5"), "11": ("10115", "6,0"), "12": ("14467", "6,5"), "04": ("28195", "5,5"),
           "02": ("20095", "5,5"), "06": ("34225", "6,0"), "13": ("19053", "6,0"), "03": ("30159", "5,0"), "05": ("40213", "6,5"),
           "07": ("55116", "5,0"), "10": ("66111", "6,5"), "14": ("01067", "5,5"), "15": ("39104", "5,0"), "01": ("24103", "6,5"),
           "16": ("99084", "5,0")}
OHNE_LANDESFOERDERUNG = {"11", "13", "04"}  # Berlin, Mecklenburg-Vorpommern, Bremen (nur die Stadt Bremen)


def familie(**abweichungen: Any) -> dict[str, Any]:
    """Familie mit zwei Kindern kauft ein sanierungsbedürftiges Haus in Baunatal (Hessen)."""
    fakten: dict[str, Any] = {
        "wohnen.vorhaben": "kauf_bestand", "wohnen.ort_immobilie": "34225", "wohnen.selbst_genutzt": "ja",
        "wohnen.vertrag_unterschrieben": "nein", "wohnen.schon_eigentum": "nein", "wohnen.kinder_minderjaehrig": 2,
        "wohnen.einkommen_zve": 85000, "wohnen.energieklasse_fgh": "ja", "wohnen.heizung_tauschen": "nein",
        "wohnen.daemmen_fenster": "nein",
    }
    for k, v in abweichungen.items():
        k = k.replace("__", ".")
        if v is None:
            fakten.pop(k, None)
        else:
            fakten[k] = v
    return fakten


@pytest.fixture
def plane_w(kb):
    def _plane(fakten: Optional[dict[str, Any]] = None, plz: str = "34117") -> Bericht:
        return planen(kb, Anfrage(fakten=fakten_parsen(kb, fakten or {}), plz=plz, lebenslagen=["wohneigentum"], stichtag=STICHTAG))

    return _plane


@pytest.mark.anforderung("ANF-WOH-01")
def test_grunderwerbsteuer_je_land_am_ort_der_immobilie(plane_w):
    for land_id, (plz, satz) in LAENDER.items():
        # Wohnort immer Kassel: maßgeblich ist der Ort der Immobilie
        e = plane_w(familie(wohnen__ort_immobilie=plz)).eintrag("grunderwerbsteuer")
        assert e.ergebnis is Wert.JA and e.gebiet.id == land_id, plz
        assert any(f"Steuersatz {satz} %" in h for h in e.variante.hinweise), (plz, e.variante.hinweise)
    assert plane_w(familie(wohnen__vorhaben="bauen")).ergebnisse()["grunderwerbsteuer"] == "unklar"  # nur bei Grundstückskauf
    # Ort der Immobilie unbekannt: Bundesvariante ohne Steuersatz, der Ort wird erfragt
    offen = plane_w(familie(wohnen__ort_immobilie=None))
    assert offen.eintrag("grunderwerbsteuer").gebiet.id == "DE"
    assert "wohnen.ort_immobilie" in offen.fehlend[:2]


@pytest.mark.anforderung("ANF-WOH-02")
def test_hessengeld(plane_w):
    e = lambda **f: plane_w(familie(**f)).ergebnisse().get("hessengeld")
    assert e() == "ja"
    assert e(wohnen__schon_eigentum="ja") == "nein"
    assert e(wohnen__selbst_genutzt="nein") == "nein"
    assert e(wohnen__vorhaben="bauen") == "unklar"  # nur mit Grundstückskauf
    # Immobilie in Bayern, Wohnort Kassel: kein Hessengeld, nur in anderen Ländern
    bayern = plane_w(familie(wohnen__ort_immobilie="85354"))
    assert "hessengeld" not in bayern.ergebnisse()
    andere = {n.leistung.id: [g.kuerzel for g in n.laender] for n in bayern.nur_andere_laender}
    assert andere["hessengeld"] == ["HE"]
    # Wohnort Berlin, Immobilie in Hessen: Hessengeld gilt
    assert plane_w(familie(), plz="10115").ergebnisse()["hessengeld"] == "ja"
    assert plane_w(familie()).eintrag("hessengeld").zustaendigkeit.name == "WIBank – Kundenportal Hessengeld"


@pytest.mark.anforderung("ANF-WOH-03")
def test_kfw_vor_vertrag_und_einkommensgrenze(plane_w):
    e = lambda **f: plane_w(familie(**f)).ergebnisse()
    vertrag = e(wohnen__vertrag_unterschrieben="ja")
    for l in ("kfw_jung_kauft_alt", "kfw_wohneigentumsprogramm", "kfw_wohneigentum_familien", "kfw_klimafreundlicher_neubau"):
        assert vertrag[l] == "nein", l
    assert vertrag["grunderwerbsteuer"] == "ja"
    # Einkommensgrenze: 90.000 € bei einem Kind, plus 10.000 € je weiterem Kind
    assert e(wohnen__kinder_minderjaehrig=1, wohnen__einkommen_zve=90000)["kfw_jung_kauft_alt"] == "ja"
    assert e(wohnen__kinder_minderjaehrig=1, wohnen__einkommen_zve=95000)["kfw_jung_kauft_alt"] == "nein"
    assert e(wohnen__kinder_minderjaehrig=2, wohnen__einkommen_zve=95000)["kfw_jung_kauft_alt"] == "ja"
    assert e(wohnen__kinder_minderjaehrig=0)["kfw_jung_kauft_alt"] == "nein"
    assert e(wohnen__kinder_minderjaehrig=6, wohnen__einkommen_zve=130000)["kfw_jung_kauft_alt"] == "unklar"
    # Neubau-Familienkredit nur bei Neubau, mit Prüfung des Gebäudestandards
    neubau = e(wohnen__vorhaben="kauf_neubau")
    assert neubau["kfw_wohneigentum_familien"] == "unklar" and neubau["kfw_jung_kauft_alt"] == "nein"
    assert e(wohnen__selbst_genutzt="nein")["kfw_wohneigentumsprogramm"] == "nein"


@pytest.mark.anforderung("ANF-WOH-04")
def test_jung_kauft_alt_und_sanierung(plane_w):
    e = lambda **f: plane_w(familie(**f)).ergebnisse()
    assert e()["kfw_jung_kauft_alt"] == "ja"
    assert e(wohnen__energieklasse_fgh="nein")["kfw_jung_kauft_alt"] == "nein"
    assert e(wohnen__schon_eigentum="ja")["kfw_jung_kauft_alt"] == "nein"
    assert e(wohnen__heizung_tauschen="ja")["heizungsfoerderung"] == "ja"
    assert e(wohnen__daemmen_fenster="ja")["bafa_sanierung"] == "ja"
    neubau = e(wohnen__vorhaben="bauen", wohnen__heizung_tauschen="ja", wohnen__daemmen_fenster="ja")
    assert neubau["heizungsfoerderung"] == "nein" and neubau["bafa_sanierung"] == "nein"
    b = plane_w(familie(wohnen__daemmen_fenster="ja"))
    assert [f.frist.text for f in b.eintrag("bafa_sanierung").fristen] == ["Vor der Beauftragung beantragen"]
    assert b.eintrag("heizungsfoerderung").pruefstatus.value == "widerspruechlich"  # Fördersätze in Berichten uneinheitlich


@pytest.mark.anforderung("ANF-WOH-05")
def test_unbekannt_bleibt_unklar(plane_w):
    b = plane_w(familie(wohnen__einkommen_zve="unbekannt"))
    assert b.ergebnisse()["kfw_jung_kauft_alt"] == "unklar"
    b = plane_w(familie(wohnen__energieklasse_fgh="unbekannt"))
    assert b.ergebnisse()["kfw_jung_kauft_alt"] == "unklar"
    # Fehlende Einstiegsangaben werden zuerst gefragt
    assert plane_w({}).fehlend[:4] == ["wohnen.vorhaben", "wohnen.ort_immobilie", "wohnen.selbst_genutzt", "wohnen.vertrag_unterschrieben"]


@pytest.mark.anforderung("ANF-WOH-06")
def test_landesfoerderung_alle_laender(kb, plane_w):
    for land in gebiete.laender(kb):
        nachweis = kb.landesabdeckung[(land.id, "wohneigentum")]
        erwartet = "keine" if land.id in OHNE_LANDESFOERDERUNG else "erfasst"
        assert nachweis.landesleistungen == erwartet, land.name
        assert nachweis.quellen and nachweis.notiz
    stellen = set()
    for land_id, (plz, _) in LAENDER.items():
        b = plane_w(familie(wohnen__ort_immobilie=plz))
        assert not any("noch nicht erfasst, ob es eigene Landesleistungen" in w for w in b.warnungen), plz
        if land_id == "06":  # Hessen: Hessengeld statt Wohnraumförderung
            assert b.ergebnisse()["hessengeld"] == "ja"
        elif land_id in OHNE_LANDESFOERDERUNG and land_id != "04":
            assert "landesfoerderung_wohneigentum" not in b.ergebnisse(), plz
        else:
            e = b.eintrag("landesfoerderung_wohneigentum")
            assert e.ergebnis is not Wert.JA, plz  # Einkommen bzw. Programmstand wird geprüft
            stellen.add(e.zustaendigkeit.name)
    assert len(stellen) >= 12  # je Land eigene Förderbank bzw. Stelle
    # Stadt Bremen: kommunaler Eigenheimzuschuss; Bremerhaven nicht
    bremen = plane_w(familie(wohnen__ort_immobilie="28195")).eintrag("landesfoerderung_wohneigentum")
    assert bremen.gebiet.ebene.value == "gemeinde" and bremen.zustaendigkeit.name == "Bremer Aufbau-Bank (BAB)"
    assert "landesfoerderung_wohneigentum" not in plane_w(familie(wohnen__ort_immobilie="27568")).ergebnisse()


@pytest.mark.anforderung("ANF-WOH-07", "ANF-WEB-08")
def test_szenarien_wohnen(kb):
    wohnen = [s for s in szenarien_mod.alle(kb) if "wohneigentum" in s.anfrage.lebenslagen]
    assert len(wohnen) >= 3
    assert any("unklar" in s.erwartet.values() for s in wohnen)
    # mindestens ein Szenario mit Immobilie außerhalb Hessens (Land mit dem Hessengeld)
    assert any(not str(s.anfrage.fakten.get("wohnen.ort_immobilie", "")).startswith(("34", "35", "36", "60", "61", "63", "64", "65"))
               for s in wohnen)
    for s in wohnen:
        assert szenarien_mod.abweichungen(s, planen(kb, s.anfrage)) == [], s.id
