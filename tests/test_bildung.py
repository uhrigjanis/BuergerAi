"""Lebenslage Ausbildung, Studium oder Meister (Fachmodul Bildung, #41 Schritt 5)."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

import pytest

from buergerai import szenarien as szenarien_mod
from buergerai.planer import Anfrage, Bericht, planen
from buergerai.regeln import Wert
from buergerai.szenarien import fakten_parsen

STICHTAG = date(2026, 10, 26)
PLZ = {"08": "70173", "09": "80331", "11": "10115", "12": "14467", "04": "28195", "02": "20095", "06": "34225", "13": "19053",
       "03": "30159", "05": "40213", "07": "55116", "10": "66111", "14": "01067", "15": "39104", "01": "24103", "16": "99084"}
OHNE_BONUS = {"12", "01"}  # Brandenburg, Schleswig-Holstein: nur Meistergründungsprämie
NUR_HANDWERK = {"08", "11", "03", "05"}  # Baden-Württemberg, Berlin, Niedersachsen, NRW


def angaben(**abweichungen: Any) -> dict[str, Any]:
    fakten: dict[str, Any] = {"bildung.vorhaben": "studium", "alter": 20, "bildung.wohnt_bei_eltern": "nein"}
    for k, v in abweichungen.items():
        k = k.replace("__", ".")
        if v is None:
            fakten.pop(k, None)
        else:
            fakten[k] = v
    return fakten


def meister(**abweichungen: Any) -> dict[str, Any]:
    return angaben(**{"bildung__vorhaben": "aufstieg", "alter": 29, "bildung__pruefung_bestanden": "ja",
                      "bildung__pruefung_datum": "2026-09-15", "bildung__handwerk": "ja", **abweichungen})


@pytest.fixture
def plane_b(kb):
    def _plane(fakten: Optional[dict[str, Any]] = None, plz: str = "50667") -> Bericht:
        return planen(kb, Anfrage(fakten=fakten_parsen(kb, fakten or {}), plz=plz, lebenslagen=["ausbildung_studium"], stichtag=STICHTAG))

    return _plane


@pytest.mark.anforderung("ANF-BIL-01")
def test_bafoeg_studium(plane_b):
    e = lambda **f: plane_b(angaben(**f)).ergebnisse()["bafoeg_studium"]
    assert e() == "unklar"  # Einkommen der Eltern
    assert e(alter=46) == "unklar"  # nur mit Ausnahme
    assert e(bildung__vorhaben="betriebliche_ausbildung") == "nein"
    b = plane_b(angaben())
    assert b.eintrag("bafoeg_studium").betrag.text.startswith("Grundbedarf 475 € plus Wohnpauschale 380 €")
    assert "Studierendenwerk" in b.eintrag("bafoeg_studium").zustaendigkeit.name


@pytest.mark.anforderung("ANF-BIL-02")
def test_berufsausbildungsbeihilfe(plane_b):
    e = lambda **f: plane_b(angaben(**{"bildung__vorhaben": "betriebliche_ausbildung", **f})).ergebnisse()["berufsausbildungsbeihilfe"]
    assert e() == "unklar"  # Einkommensrechnung der Arbeitsagentur
    assert e(bildung__wohnt_bei_eltern="ja") == "nein"
    assert e(bildung__vorhaben="schulische_ausbildung") == "nein"  # dafür ggf. BAföG
    # Minderjährig mit eigener Wohnung: nur bei weitem Weg (oder Sonderfällen)
    assert e(alter=17, bildung__betrieb_weit_von_eltern="ja") == "unklar"
    assert e(alter=17, bildung__betrieb_weit_von_eltern="nein") == "unklar"  # Sonderfälle (Kind, Ehe) werden geprüft
    b = plane_b(angaben(bildung__vorhaben="betriebliche_ausbildung"))
    assert [f.frist.text for f in b.eintrag("berufsausbildungsbeihilfe").fristen] == ["Frühestens ab dem Monat des Antrags – also rechtzeitig beantragen"]


@pytest.mark.anforderung("ANF-BIL-03")
def test_kindergeld_bis_25(plane_b):
    e = lambda **f: plane_b(angaben(**f)).ergebnisse()["kindergeld_ausbildung"]
    assert e() == "ja" and e(alter=24) == "ja" and e(alter=25) == "nein"
    assert e(bildung__vorhaben="aufstieg") == "nein"
    eintrag = plane_b(angaben()).eintrag("kindergeld_ausbildung")
    assert eintrag.betrag.text == "259 € im Monat" and eintrag.leistung.beantragt_von == "angehoerige"


@pytest.mark.anforderung("ANF-BIL-04")
def test_meisterbonus_je_land(kb, plane_b):
    stellen = set()
    for land_id, plz in PLZ.items():
        b = plane_b(meister(), plz=plz)
        nachweis = kb.landesabdeckung[(land_id, "ausbildung_studium")]
        if land_id in OHNE_BONUS:
            assert nachweis.landesleistungen == "keine" and "meisterbonus" not in b.ergebnisse(), plz
            continue
        assert nachweis.landesleistungen == "erfasst", plz
        e = b.eintrag("meisterbonus")
        assert e.gebiet.id == land_id and e.ergebnis is not Wert.NEIN, plz
        stellen.add(e.zustaendigkeit.name)
        # Länder, die nur das Handwerk fördern: Fachwirt (IHK) bekommt dort nichts
        if land_id in NUR_HANDWERK:
            assert plane_b(meister(bildung__handwerk="nein"), plz=plz).ergebnisse()["meisterbonus"] == "nein", plz
    assert len(stellen) >= 12
    # Ohne bestandene Prüfung keine Prämie; in Schleswig-Holstein nur anderswo
    assert plane_b(meister(bildung__pruefung_bestanden="nein")).ergebnisse()["meisterbonus"] == "nein"
    kiel = plane_b(meister(), plz="24103")
    andere = {n.leistung.id: [g.kuerzel for g in n.laender] for n in kiel.nur_andere_laender}
    assert "SH" not in andere["meisterbonus"] and "BB" not in andere["meisterbonus"] and len(andere["meisterbonus"]) == 14


@pytest.mark.anforderung("ANF-BIL-05")
def test_frist_ab_pruefungsdatum(plane_b):
    e = plane_b(meister()).eintrag("meisterbonus")  # Köln
    assert e.ergebnis is Wert.JA
    frist = e.fristen[0]
    assert frist.datum == date(2026, 12, 14)  # 90 Tage nach dem 15.9.2026
    # Datum nur gefragt, wenn die Prüfung bestanden ist
    offen = plane_b(meister(bildung__pruefung_datum=None))
    assert "bildung.pruefung_datum" in offen.fehlend
    assert "bildung.pruefung_datum" not in plane_b(meister(bildung__pruefung_bestanden="nein", bildung__pruefung_datum=None)).fehlend


@pytest.mark.anforderung("ANF-BIL-06")
def test_unbekannt_bleibt_unklar(plane_b):
    b = plane_b(angaben(alter="unbekannt"))
    assert b.ergebnisse()["bafoeg_studium"] == "unklar" and b.ergebnisse()["kindergeld_ausbildung"] == "unklar"
    assert plane_b({}).fehlend[:2] == ["bildung.vorhaben", "alter"]
    assert "bildung.pruefung_bestanden" not in plane_b(angaben()).fehlend  # nur bei Aufstiegsfortbildung
    assert plane_b(meister(bildung__handwerk="unbekannt")).ergebnisse()["meisterbonus"] == "unklar"


@pytest.mark.anforderung("ANF-BIL-07", "ANF-WEB-08")
def test_szenarien_bildung(kb):
    bildung = [s for s in szenarien_mod.alle(kb) if "ausbildung_studium" in s.anfrage.lebenslagen]
    assert len(bildung) >= 3
    assert any("unklar" in s.erwartet.values() for s in bildung)
    assert any(s.anfrage.plz == "24103" for s in bildung)  # Land ohne Meisterbonus
    for s in bildung:
        assert szenarien_mod.abweichungen(s, planen(kb, s.anfrage)) == [], s.id
