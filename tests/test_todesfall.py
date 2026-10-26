"""Lebenslage Todesfall (Fachmodul Todesfall, #41 Schritt 6)."""

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
# Länder mit Frist in Kalendertagen (als Datum berechnet); sonst nur Text
FRIST_TAGE = {"12": 10, "06": 10, "13": 10, "03": 8, "05": 10, "07": 14, "10": 10, "15": 10, "01": 9, "16": 10}


def todesfall(**abweichungen: Any) -> dict[str, Any]:
    fakten: dict[str, Any] = {"todesfall.datum": "2026-10-24", "todesfall.beziehung": "ehepartner", "todesfall.sterbeort": "50667",
                              "todesfall.sterbeort_art": "zuhause", "todesfall.ausschlagen_erwaegen": "nein", "todesfall.bezog_rente": "ja",
                              "todesfall.kosten_tragbar": "ja"}
    for k, v in abweichungen.items():
        k = k.replace("__", ".")
        if v is None:
            fakten.pop(k, None)
        else:
            fakten[k] = v
    return fakten


@pytest.fixture
def plane_t(kb):
    def _plane(fakten: Optional[dict[str, Any]] = None, plz: str = "50667") -> Bericht:
        return planen(kb, Anfrage(fakten=fakten_parsen(kb, fakten or {}), plz=plz, lebenslagen=["todesfall"], stichtag=STICHTAG))

    return _plane


@pytest.mark.anforderung("ANF-TOD-01")
def test_sterbefall_anzeigen(plane_t):
    b = plane_t(todesfall())
    e = b.eintrag("sterbefall_anzeigen")
    assert e.ergebnis is Wert.JA and e.leistung.art == "pflicht"
    assert e.fristen[0].datum == date(2026, 10, 27)  # drei Tage nach dem Tod (vorsichtig gerechnet)
    assert e.zustaendigkeit.name == "Standesamt des Sterbeorts"
    # Im Krankenhaus oder Heim zeigt die Einrichtung den Tod an
    assert plane_t(todesfall(todesfall__sterbeort_art="einrichtung")).ergebnisse()["sterbefall_anzeigen"] == "nein"
    assert plane_t({}).fehlend[0] == "todesfall.datum"


@pytest.mark.anforderung("ANF-TOD-02")
def test_bestattungsfrist_je_land(kb, plane_t):
    for land_id, plz in PLZ.items():
        nachweis = kb.landesabdeckung[(land_id, "todesfall")]
        assert nachweis.landesleistungen == "erfasst" and nachweis.quellen and nachweis.notiz, plz
        # Wohnort Köln, gestorben im jeweiligen Land: es gilt das Recht des Sterbeorts
        e = plane_t(todesfall(todesfall__sterbeort=plz)).eintrag("bestattung_veranlassen")
        assert e.gebiet.id == land_id and e.ergebnis is Wert.JA, plz
        datum = e.fristen[0].datum
        if land_id in FRIST_TAGE:
            assert datum is not None and (datum - date(2026, 10, 24)).days == FRIST_TAGE[land_id], plz
        else:
            assert datum is None, plz  # Werktage bzw. keine feste Frist: kein berechnetes Datum
    by = plane_t(todesfall(todesfall__sterbeort="80331")).eintrag("bestattung_veranlassen")
    assert "Samstage, Sonn- und Feiertage zählen nicht" in by.fristen[0].frist.text


@pytest.mark.anforderung("ANF-TOD-03")
def test_bestattungspflicht_und_kosten(plane_t):
    e = lambda **f: plane_t(todesfall(**f)).ergebnisse()
    assert e()["bestattung_veranlassen"] == "ja"
    assert e(todesfall__beziehung="kind")["bestattung_veranlassen"] == "unklar"  # Reihenfolge der Pflichtigen
    assert e(todesfall__beziehung="andere")["bestattung_veranlassen"] == "nein"
    assert e()["bestattungskosten_sozialamt"] == "nein"
    assert e(todesfall__kosten_tragbar="nein")["bestattungskosten_sozialamt"] == "unklar"
    assert e(todesfall__beziehung="andere", todesfall__kosten_tragbar="nein")["bestattungskosten_sozialamt"] == "nein"


@pytest.mark.anforderung("ANF-TOD-04")
def test_renten(plane_t):
    b = plane_t(todesfall())
    assert b.ergebnisse()["rentenvorschuss_witwe"] == "ja"
    assert b.eintrag("rentenvorschuss_witwe").fristen[0].datum == date(2026, 11, 23)  # 30 Tage
    e = lambda **f: plane_t(todesfall(**f)).ergebnisse()
    assert e(todesfall__bezog_rente="nein")["rentenvorschuss_witwe"] == "nein"
    assert e()["hinterbliebenenrente"] == "unklar"
    assert e(todesfall__beziehung="kind")["hinterbliebenenrente"] == "unklar"  # Waisenrente
    assert e(todesfall__beziehung="andere")["hinterbliebenenrente"] == "nein"
    # Rentenbezug nur bei Ehepartnern gefragt
    assert "todesfall.bezog_rente" not in plane_t(todesfall(todesfall__beziehung="kind", todesfall__bezog_rente=None)).fehlend


@pytest.mark.anforderung("ANF-TOD-05")
def test_erbe_ausschlagen(plane_t):
    b = plane_t(todesfall(todesfall__ausschlagen_erwaegen="ja", todesfall__erbe_kenntnis="2026-10-24"))
    e = b.eintrag("erbe_ausschlagen")
    assert e.ergebnis is Wert.UNKLAR
    assert e.fristen[0].datum == date(2026, 12, 5)  # sechs Wochen
    assert "todesfall.erbe_kenntnis" not in plane_t(todesfall()).fehlend
    assert "todesfall.erbe_kenntnis" in plane_t(todesfall(todesfall__ausschlagen_erwaegen="ja")).fehlend


@pytest.mark.anforderung("ANF-TOD-06")
def test_unbekannt_und_ohne_ort(plane_t):
    b = plane_t(todesfall(todesfall__beziehung="unbekannt"))
    assert b.ergebnisse()["bestattung_veranlassen"] == "unklar"
    assert b.ergebnisse()["hinterbliebenenrente"] == "unklar"
    # Sterbeort unbekannt: keine Liste aller Länder, sondern ein Hinweis
    ohne = plane_t(todesfall(todesfall__sterbeort="unbekannt"))
    assert "bestattung_veranlassen" not in ohne.ergebnisse()
    assert not ohne.nur_andere_laender
    assert any("Wo ist die Person gestorben" in w for w in ohne.warnungen), ohne.warnungen


@pytest.mark.anforderung("ANF-TOD-07", "ANF-WEB-08")
def test_szenarien_todesfall(kb):
    szen = [s for s in szenarien_mod.alle(kb) if "todesfall" in s.anfrage.lebenslagen]
    assert len(szen) >= 3
    assert any("unklar" in s.erwartet.values() for s in szen)
    for s in szen:
        assert szenarien_mod.abweichungen(s, planen(kb, s.anfrage)) == [], s.id
    # Wohnort Köln, gestorben in München: Bestattungsrecht von Bayern
    muenchen = next(s for s in szen if s.id == "todesfall_koeln_vater_in_muenchen")
    assert planen(kb, muenchen.anfrage).eintrag("bestattung_veranlassen").gebiet.id == "09"
