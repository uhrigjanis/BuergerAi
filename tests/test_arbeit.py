"""Lebenslagen Job verloren und Selbstständig machen (Fachmodul Arbeit, #41 Schritt 6)."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

import pytest

from buergerai import szenarien as szenarien_mod
from buergerai.planer import Anfrage, Bericht, planen
from buergerai.regeln import Wert
from buergerai.szenarien import fakten_parsen

STICHTAG = date(2026, 10, 21)
PLZ = {"08": "70173", "09": "80331", "11": "10115", "12": "14467", "04": "28195", "02": "20095", "06": "34225", "13": "19053",
       "03": "30159", "05": "40213", "07": "55116", "10": "66111", "14": "01067", "15": "39104", "01": "24103", "16": "99084"}
MIT_BERATUNG = {"08", "11", "03", "05", "10"}
OHNE_MEISTERGRUENDUNG = {"09", "04", "06", "14"}


def kuendigung(**abweichungen: Any) -> dict[str, Any]:
    fakten: dict[str, Any] = {"arbeit.grund": "kuendigung_arbeitgeber", "arbeit.ende_datum": "2026-12-31", "arbeit.kuendigung_zugang": "2026-10-20",
                              "arbeit.versichert_12_monate": "ja", "bezieht_buergergeld": "nein", "einkommen.erwerbsfaehig": "ja", "alter": 40}
    return _anpassen(fakten, abweichungen)


def gruendung(**abweichungen: Any) -> dict[str, Any]:
    fakten: dict[str, Any] = {"arbeit.taetigkeit": "handwerk", "arbeit.gruendungsdatum": "2026-12-01", "arbeit.hauptberuflich": "ja",
                              "arbeit.zulassungspflichtig": "ja", "arbeit.meister": "ja", "arbeit.bezieht_alg": "nein", "bezieht_buergergeld": "nein",
                              "arbeit.kredit_benoetigt": "nein"}
    return _anpassen(fakten, abweichungen)


def _anpassen(fakten: dict[str, Any], abweichungen: dict[str, Any]) -> dict[str, Any]:
    for k, v in abweichungen.items():
        k = k.replace("__", ".")
        if v is None:
            fakten.pop(k, None)
        else:
            fakten[k] = v
    return fakten


@pytest.fixture
def plane_a(kb):
    def _plane(fakten: Optional[dict[str, Any]] = None, plz: str = "50667", lebenslage: str = "jobverlust") -> Bericht:
        return planen(kb, Anfrage(fakten=fakten_parsen(kb, fakten or {}), plz=plz, lebenslagen=[lebenslage], stichtag=STICHTAG))

    return _plane


def frist_datum(b: Bericht, leistung: str) -> Optional[date]:
    return b.eintrag(leistung).fristen[0].datum


# ------------------------------------------------------------------ Job verloren
@pytest.mark.anforderung("ANF-ARB-01")
def test_arbeitsuchend_melden_frist(plane_a):
    # Kündigung am 20.10. für den 31.12.: weniger als drei Monate -> drei Tage nach Zugang
    assert frist_datum(plane_a(kuendigung()), "arbeitsuchend_melden") == date(2026, 10, 23)
    # Befristung: drei Monate vor dem Ende
    b = plane_a(kuendigung(arbeit__grund="befristung", arbeit__kuendigung_zugang=None))
    assert frist_datum(b, "arbeitsuchend_melden") == date(2026, 9, 30)
    # Lange Kündigungsfrist: drei Monate vor dem Ende ist später als drei Tage nach Zugang
    b = plane_a(kuendigung(arbeit__ende_datum="2027-06-30"))
    assert frist_datum(b, "arbeitsuchend_melden") == date(2027, 3, 30)
    assert plane_a(kuendigung()).ergebnisse()["arbeitsuchend_melden"] == "ja"


@pytest.mark.anforderung("ANF-ARB-02")
def test_arbeitslosengeld_und_klage(plane_a):
    e = lambda **f: plane_a(kuendigung(**f)).ergebnisse()
    assert e()["arbeitslosengeld"] == "ja"
    assert e(arbeit__versichert_12_monate="nein")["arbeitslosengeld"] == "nein"
    assert e(arbeit__grund="eigenkuendigung", arbeit__kuendigung_zugang=None)["arbeitslosengeld"] == "unklar"  # Sperrzeit
    assert e()["kuendigungsschutzklage"] == "unklar"
    assert e(arbeit__grund="befristung", arbeit__kuendigung_zugang=None)["kuendigungsschutzklage"] == "nein"
    b = plane_a(kuendigung())
    assert frist_datum(b, "kuendigungsschutzklage") == date(2026, 11, 10)  # drei Wochen nach Zugang
    assert frist_datum(b, "arbeitslosengeld") == date(2027, 1, 1)  # erster Tag ohne Arbeit
    # Grundsicherungsgeld gehört auch zu Job verloren
    assert "jobverlust" in b.eintrag("grundsicherungsgeld").lebenslagen


@pytest.mark.anforderung("ANF-ARB-03")
def test_insolvenzgeld(plane_a):
    b = plane_a(kuendigung(arbeit__grund="insolvenz", arbeit__kuendigung_zugang=None, arbeit__insolvenz_datum="2026-10-01"))
    assert b.ergebnisse()["insolvenzgeld"] == "ja"
    assert frist_datum(b, "insolvenzgeld") == date(2026, 12, 1)
    # Datum der Insolvenz nur bei Insolvenz gefragt, Zugang der Kündigung nur bei Kündigung
    assert "arbeit.insolvenz_datum" not in plane_a(kuendigung()).fehlend
    assert "arbeit.kuendigung_zugang" not in plane_a(kuendigung(arbeit__grund="befristung", arbeit__kuendigung_zugang=None)).fehlend
    assert "arbeit.kuendigung_zugang" in plane_a(kuendigung(arbeit__kuendigung_zugang=None)).fehlend


@pytest.mark.anforderung("ANF-ARB-04", "ANF-ARB-05")
def test_erwerbslosenberatung_je_land(kb, plane_a):
    for land_id, plz in PLZ.items():
        nachweis = kb.landesabdeckung[(land_id, "jobverlust")]
        assert nachweis.quellen and nachweis.notiz
        b = plane_a(kuendigung(), plz=plz)
        if land_id in MIT_BERATUNG:
            assert nachweis.landesleistungen == "erfasst", plz
            assert b.eintrag("erwerbslosenberatung").gebiet.id == land_id
        else:
            assert nachweis.landesleistungen == "keine", plz
            assert "erwerbslosenberatung" not in b.ergebnisse()
    muenchen = plane_a(kuendigung(), plz="80331")
    andere = {n.leistung.id: sorted(g.kuerzel for g in n.laender) for n in muenchen.nur_andere_laender}
    assert andere["erwerbslosenberatung"] == ["BE", "BW", "NI", "NW", "SL"]


# ------------------------------------------------------------------ Selbstständig machen
@pytest.mark.anforderung("ANF-ARB-06")
def test_pflichten_bei_gruendung(plane_a):
    e = lambda **f: plane_a(gruendung(**f), plz="24103", lebenslage="selbststaendig").ergebnisse()
    assert e()["gewerbe_anmelden"] == "ja" and e()["handwerksrolle"] == "ja" and e()["steuerliche_erfassung"] == "ja"
    frei = e(arbeit__taetigkeit="freiberuflich", arbeit__zulassungspflichtig=None, arbeit__meister=None)
    assert frei["gewerbe_anmelden"] == "nein" and frei["handwerksrolle"] == "nein" and frei["steuerliche_erfassung"] == "ja"
    assert e(arbeit__zulassungspflichtig="nein")["handwerksrolle"] == "nein"
    b = plane_a(gruendung(), plz="24103", lebenslage="selbststaendig")
    assert frist_datum(b, "steuerliche_erfassung") == date(2027, 1, 1)  # ein Monat nach Beginn
    assert frist_datum(b, "gewerbe_anmelden") == date(2026, 12, 1)
    assert b.eintrag("gewerbe_anmelden").zustaendigkeit.name == "Gewerbeamt – Kiel"


@pytest.mark.anforderung("ANF-ARB-07")
def test_gruendungsfoerderung(plane_a):
    e = lambda **f: plane_a(gruendung(arbeit__taetigkeit="gewerbe", **f), lebenslage="selbststaendig").ergebnisse()
    assert e()["gruendungszuschuss"] == "nein" and e()["einstiegsgeld"] == "nein"
    assert e(arbeit__bezieht_alg="ja", arbeit__alg_resttage=200)["gruendungszuschuss"] == "unklar"  # Ermessen
    assert e(arbeit__bezieht_alg="ja", arbeit__alg_resttage=100)["gruendungszuschuss"] == "nein"
    assert e(arbeit__bezieht_alg="ja", arbeit__alg_resttage=200, arbeit__hauptberuflich="nein")["gruendungszuschuss"] == "nein"
    assert e(bezieht_buergergeld="ja")["einstiegsgeld"] == "unklar"
    assert e(arbeit__kredit_benoetigt="ja")["kfw_startgeld"] == "unklar"
    # Resttage nur gefragt, wenn Arbeitslosengeld bezogen wird
    assert "arbeit.alg_resttage" not in plane_a(gruendung(), lebenslage="selbststaendig").fehlend


@pytest.mark.anforderung("ANF-ARB-08")
def test_meistergruendungspraemie_je_land(kb, plane_a):
    stellen = set()
    for land_id, plz in PLZ.items():
        nachweis = kb.landesabdeckung[(land_id, "selbststaendig")]
        b = plane_a(gruendung(), plz=plz, lebenslage="selbststaendig")
        if land_id in OHNE_MEISTERGRUENDUNG:
            assert nachweis.landesleistungen == "keine" and "meistergruendungspraemie" not in b.ergebnisse(), plz
            continue
        assert nachweis.landesleistungen == "erfasst", plz
        e = b.eintrag("meistergruendungspraemie")
        assert e.gebiet.id == land_id and e.ergebnis is Wert.UNKLAR, plz
        stellen.add(e.zustaendigkeit.name)
    assert len(stellen) == 12
    assert plane_a(gruendung(arbeit__meister="nein"), plz="24103", lebenslage="selbststaendig").ergebnisse()["meistergruendungspraemie"] == "nein"


@pytest.mark.anforderung("ANF-ARB-09", "ANF-WEB-08")
def test_szenarien_arbeit(kb):
    for ll in ("jobverlust", "selbststaendig"):
        szen = [s for s in szenarien_mod.alle(kb) if ll in s.anfrage.lebenslagen]
        assert len(szen) >= 3, ll
        assert any("unklar" in s.erwartet.values() for s in szen), ll
        for s in szen:
            assert szenarien_mod.abweichungen(s, planen(kb, s.anfrage)) == [], s.id


@pytest.mark.anforderung("ANF-ARB-10")
def test_frist_nicht_vor_wird_geprueft(tmp_path):
    from buergerai.wissensbasis import DatenFehler, Wissensbasis
    from test_wissensbasis import bearbeite, kopie

    daten = kopie(tmp_path)

    def bearbeiten(d):
        v = next(v for v in d["varianten"] if v["id"] == "arbeitsuchend_melden_bund")
        v["verfahren"]["fristen"][0]["nicht_vor"] = {"bezug": "arbeit.grund", "tage": 3}

    bearbeite(daten / "fachmodule" / "arbeit" / "arbeit.json", bearbeiten)
    with pytest.raises(DatenFehler) as info:
        Wissensbasis.laden(daten)
    assert "'nicht_vor' braucht einen erlaubten Datumsfakt" in str(info.value)
