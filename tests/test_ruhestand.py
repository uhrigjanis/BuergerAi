"""Lebenslage Ruhestand (Fachmodul Ruhestand, #41 Schritt 6)."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

import pytest

from buergerai import gebiete
from buergerai import szenarien as szenarien_mod
from buergerai.fakten import abgeleitete_fakten, regelaltersgrenze, regelaltersrente_ab
from buergerai.planer import Anfrage, Bericht, planen
from buergerai.regeln import Wert
from buergerai.szenarien import fakten_parsen

STICHTAG = date(2026, 10, 26)
PLZ = {"08": "70173", "09": "80331", "11": "10115", "12": "14467", "04": "28195", "02": "20095", "06": "34225", "13": "19053",
       "03": "30159", "05": "40213", "07": "55116", "10": "66111", "14": "01067", "15": "39104", "01": "24103", "16": "99084"}
TICKET_AB = {"13": 65, "02": 67, "06": 65}


def rentner(**abweichungen: Any) -> dict[str, Any]:
    fakten: dict[str, Any] = {"ruhestand.geburtsdatum": "1960-03-15", "ruhestand.rentenbeginn": "2026-08-01", "ruhestand.versicherungsjahre": 42,
                              "ruhestand.gesetzlich_krankenversichert": "ja"}
    for k, v in abweichungen.items():
        k = k.replace("__", ".")
        if v is None:
            fakten.pop(k, None)
        else:
            fakten[k] = v
    return fakten


@pytest.fixture
def plane_r(kb):
    def _plane(fakten: Optional[dict[str, Any]] = None, plz: str = "80331") -> Bericht:
        return planen(kb, Anfrage(fakten=fakten_parsen(kb, fakten or {}), plz=plz, lebenslagen=["ruhestand"], stichtag=STICHTAG))

    return _plane


@pytest.mark.anforderung("ANF-RUH-01")
def test_regelaltersgrenze_und_altersrente(plane_r):
    assert regelaltersgrenze(1946) == (65, 0)
    assert regelaltersgrenze(1950) == (65, 4)
    assert regelaltersgrenze(1958) == (66, 0)
    assert regelaltersgrenze(1960) == (66, 4)
    assert regelaltersgrenze(1963) == (66, 10)
    assert regelaltersgrenze(1964) == (67, 0) == regelaltersgrenze(1990)
    assert regelaltersrente_ab(date(1960, 1, 1)) == date(2026, 6, 1)  # Beispiel der Rentenversicherung
    assert regelaltersrente_ab(date(1963, 12, 10)) == date(2030, 11, 1)
    assert regelaltersrente_ab(date(1964, 11, 15)) == date(2031, 12, 1)
    b = plane_r(rentner())
    e = b.eintrag("altersrente")
    assert e.ergebnis is Wert.JA
    assert e.fristen[0].datum == date(2026, 5, 1) and e.fristen[0].frist.art == "empfohlen"
    # Einen Monat zu früh: Regelaltersgrenze noch nicht erreicht
    assert plane_r(rentner(ruhestand__rentenbeginn="2026-07-01")).ergebnisse()["altersrente"] == "unklar"
    assert plane_r({}).fehlend[:2] == ["ruhestand.geburtsdatum", "ruhestand.rentenbeginn"]


@pytest.mark.anforderung("ANF-RUH-02")
def test_vorzeitig_und_wartezeit(plane_r):
    e = lambda **f: plane_r(rentner(**f)).ergebnisse()["altersrente"]
    mit_63 = dict(ruhestand__geburtsdatum="1963-06-01", ruhestand__rentenbeginn="2026-07-01")
    assert e(**mit_63, ruhestand__versicherungsjahre=40) == "unklar"
    assert e(**mit_63, ruhestand__versicherungsjahre=30) == "nein"
    assert e(ruhestand__geburtsdatum="1965-06-01", ruhestand__rentenbeginn="2026-07-01") == "nein"  # erst 61
    assert e(ruhestand__versicherungsjahre=3) == "nein"  # Wartezeit fehlt
    assert e(ruhestand__geburtsdatum="unbekannt") == "unklar"
    assert e(ruhestand__versicherungsjahre="unbekannt") == "unklar"


@pytest.mark.anforderung("ANF-RUH-03")
def test_kvdr(plane_r):
    e = lambda **f: plane_r(rentner(**f)).ergebnisse()["kvdr"]
    assert e() == "unklar"  # 9/10-Regel prüft die Krankenkasse
    assert e(ruhestand__gesetzlich_krankenversichert="nein") == "nein"


@pytest.mark.anforderung("ANF-RUH-04")
def test_seniorenticket_je_land(kb, plane_r):
    quellen = set()
    for land_id, plz in PLZ.items():
        nachweis = kb.landesabdeckung[(land_id, "ruhestand")]
        assert nachweis.quellen and nachweis.notiz, plz
        quellen.update(nachweis.quellen)
        b = plane_r(rentner(ruhestand__geburtsdatum="1958-05-10", ruhestand__rentenbeginn="2026-12-01"), plz=plz)  # 68 Jahre
        if land_id in TICKET_AB:
            assert nachweis.landesleistungen == "erfasst", plz
            assert b.eintrag("seniorenticket_land").gebiet.id == land_id and b.ergebnisse()["seniorenticket_land"] == "ja", plz
        else:
            assert nachweis.landesleistungen == "keine", plz
            assert "seniorenticket_land" not in b.ergebnisse(), plz
    assert len(quellen) == 16
    # Hamburg erst ab 67, Mecklenburg-Vorpommern ab 65
    jung = rentner(ruhestand__geburtsdatum="1960-03-15", ruhestand__rentenbeginn="2026-04-01")
    assert plane_r(jung, plz="20095").ergebnisse()["seniorenticket_land"] == "nein"
    assert plane_r(jung, plz="19053").ergebnisse()["seniorenticket_land"] == "ja"
    andere = {n.leistung.id: sorted(g.kuerzel for g in n.laender) for n in plane_r(rentner()).nur_andere_laender}
    assert andere["seniorenticket_land"] == ["HE", "HH", "MV"]
    assert len(gebiete.laender(kb)) == 16


@pytest.mark.anforderung("ANF-RUH-05")
def test_alter_aus_geburtsdatum(plane_r):
    neu = abgeleitete_fakten({"ruhestand.geburtsdatum": date(1960, 3, 15), "ruhestand.rentenbeginn": date(2026, 8, 1)}, STICHTAG)
    assert neu["alter"] == 66 and neu["ruhestand.alter_bei_rentenbeginn"] == 66 and neu["ruhestand.regelaltersgrenze_erreicht"] is True
    # Angegebenes Alter wird nicht überschrieben
    assert "alter" not in abgeleitete_fakten({"alter": 70, "ruhestand.geburtsdatum": date(1960, 3, 15)}, STICHTAG)
    b = plane_r(rentner())
    assert "alter" not in b.fehlend  # nicht noch einmal gefragt
    assert "ruhestand" in b.eintrag("grundsicherung_alter_em").lebenslagen
    assert "ruhestand" in b.eintrag("wohngeld").lebenslagen


@pytest.mark.anforderung("ANF-RUH-06", "ANF-WEB-08")
def test_szenarien_ruhestand(kb):
    szen = [s for s in szenarien_mod.alle(kb) if "ruhestand" in s.anfrage.lebenslagen]
    assert len(szen) >= 3
    assert any("unklar" in s.erwartet.values() for s in szen)
    for s in szen:
        assert szenarien_mod.abweichungen(s, planen(kb, s.anfrage)) == [], s.id
