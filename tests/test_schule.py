"""Lebenslage Schulstart (Fachmodul Bildung, #41 Schritt 6)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

import pytest

from buergerai import szenarien as szenarien_mod
from buergerai.planer import Anfrage, Bericht, planen
from buergerai.regeln import Wert, _vergleiche, tag_im_jahr
from buergerai.szenarien import fakten_parsen

STICHTAG = date(2026, 10, 26)
PLZ = {"08": "70173", "09": "80331", "11": "10115", "12": "14467", "04": "28195", "02": "20095", "06": "34225", "13": "19053",
       "03": "30159", "05": "40213", "07": "55116", "10": "66111", "14": "01067", "15": "39104", "01": "24103", "16": "99084"}
# Letzter Geburtstag (Monat, Tag), mit dem ein Kind im Einschulungsjahr schulpflichtig ist
SCHULPFLICHT_BIS = {"08": (6, 30), "09": (9, 30), "11": (9, 30), "12": (9, 30), "04": (6, 30), "02": (7, 1), "06": (7, 1), "13": (6, 30),
                    "03": (9, 30), "05": (9, 30), "07": (8, 31), "10": (6, 30), "14": (6, 30), "15": (6, 30), "01": (6, 30), "16": (8, 1)}


def kind(geburt: str = "2021-03-10", jahr: Any = 2027, **abweichungen: Any) -> dict[str, Any]:
    fakten: dict[str, Any] = {"bildung.kind_geburtsdatum": geburt, "bildung.einschulungsjahr": jahr, "bildung.ganztag_gewuenscht": "nein",
                              "kinder_im_haushalt": 1, "bezieht_buergergeld": "nein", "bezieht_sozialhilfe": "nein", "bezieht_wohngeld": "nein",
                              "bezieht_kinderzuschlag": "nein", "bezieht_asylbewerberleistungen": "nein"}
    for k, v in abweichungen.items():
        fakten[k.replace("__", ".")] = v
    return fakten


@pytest.fixture
def plane_s(kb):
    def _plane(fakten: Optional[dict[str, Any]] = None, plz: str = "80331") -> Bericht:
        return planen(kb, Anfrage(fakten=fakten_parsen(kb, fakten or {}), plz=plz, lebenslagen=["schule"], stichtag=STICHTAG))

    return _plane


@pytest.mark.anforderung("ANF-SCH-01")
def test_stichtag_je_land(kb, plane_s):
    for land_id, plz in PLZ.items():
        nachweis = kb.landesabdeckung[(land_id, "schule")]
        assert nachweis.landesleistungen == "erfasst" and nachweis.quellen and nachweis.notiz, plz
        monat, tag = SCHULPFLICHT_BIS[land_id]
        letzter = date(2021, monat, tag)
        e = lambda geburt: plane_s(kind(geburt.isoformat()), plz=plz).eintrag("schulanmeldung")
        am_stichtag = e(letzter)
        assert am_stichtag.gebiet.id == land_id and am_stichtag.ergebnis is Wert.JA, plz
        assert am_stichtag.leistung.art == "pflicht"
        assert e(letzter + timedelta(days=1)).ergebnis is Wert.UNKLAR, plz  # Kann-Kind
    assert len(set(SCHULPFLICHT_BIS.values())) >= 5
    e = lambda **f: plane_s(kind(**f)).ergebnisse()["schulanmeldung"]
    assert e(geburt="2022-01-15") == "nein"  # erst fünf
    assert e(geburt="2020-11-01") == "ja"  # zurückgestellt, schon sieben
    # Gleiches Kind: in München schulpflichtig, in Kiel noch nicht
    assert e(geburt="2021-08-15") == "ja"
    assert plane_s(kind("2021-08-15"), plz="24103").ergebnisse()["schulanmeldung"] == "unklar"


@pytest.mark.anforderung("ANF-SCH-02")
def test_vergleich_mit_tag_im_jahr(tmp_path):
    assert _vergleiche(date(2021, 6, 30), "<=", "--06-30")
    assert not _vergleiche(date(2019, 7, 1), "<=", "--06-30")
    assert _vergleiche(date(2024, 2, 29), "<", "--03-01")
    from buergerai.wissensbasis import DatenFehler, Wissensbasis
    from test_wissensbasis import bearbeite, kopie

    daten = kopie(tmp_path)

    def bearbeiten(d):
        d["varianten"][0]["regel"]["eine"][0]["alle"][1]["wert"] = "--13-01"

    bearbeite(daten / "laender" / "by" / "schule.json", bearbeiten)
    with pytest.raises(DatenFehler) as info:
        Wissensbasis.laden(daten)
    assert "kein Tag im Jahr (--MM-TT)" in str(info.value)
    # Zu kurze oder falsch aufgebaute Werte geben denselben sauberen Fehler (kein IndexError)
    for falsch in ("--1", "--", "-06-30x", "06-30--"):
        with pytest.raises(ValueError, match="--MM-TT"):
            tag_im_jahr(falsch)

    def kurz(d):
        d["varianten"][0]["regel"]["eine"][0]["alle"][1]["wert"] = "--1"

    bearbeite(daten / "laender" / "by" / "schule.json", kurz)
    with pytest.raises(DatenFehler) as info:
        Wissensbasis.laden(daten)
    assert "kein Tag im Jahr (--MM-TT)" in str(info.value)


@pytest.mark.anforderung("ANF-SCH-03")
def test_alter_abgeleitet_und_unbekannt(plane_s, capsys):
    b = plane_s({})
    assert b.fehlend[:2] == ["bildung.kind_geburtsdatum", "bildung.einschulungsjahr"]
    assert "bildung.alter_im_einschulungsjahr" not in b.fehlend
    assert plane_s(kind(jahr="unbekannt")).ergebnisse()["schulanmeldung"] == "unklar"
    assert plane_s(kind(geburt="unbekannt")).ergebnisse()["schulanmeldung"] == "unklar"
    from buergerai import cli

    cli.main(["--keine-farbe", "pruefen", "--plz", "80331", "-l", "schule", "--stichtag", "2026-10-26",
              "-f", "bildung.kind_geburtsdatum=15.08.2021", "-f", "bildung.einschulungsjahr=2027", "-f", "bildung.ganztag_gewuenscht=ja"])
    out = capsys.readouterr().out
    assert "[Angabe: 2027]" in out and "2.027" not in out


@pytest.mark.anforderung("ANF-SCH-03")
def test_jahreszahl_braucht_typ_zahl(tmp_path):
    from buergerai.wissensbasis import DatenFehler, Wissensbasis
    from test_wissensbasis import bearbeite, kopie

    daten = kopie(tmp_path)

    def bearbeiten(d):
        f = next(f for f in d["fakten"] if f["id"] == "bildung.einschulungsjahr")
        f["typ"] = "datum"

    bearbeite(daten / "fachmodule" / "bildung" / "fakten.json", bearbeiten)
    with pytest.raises(DatenFehler) as info:
        Wissensbasis.laden(daten)
    assert "IDs auf 'jahr' stehen für Jahreszahlen" in str(info.value)


@pytest.mark.anforderung("ANF-SCH-04")
def test_ganztag(plane_s):
    e = lambda **f: plane_s(kind(**f)).ergebnisse()["ganztag_grundschule"]
    assert e(bildung__ganztag_gewuenscht="ja") == "ja"
    assert e(bildung__ganztag_gewuenscht="nein") == "nein"
    assert e(geburt="2020-03-10", jahr=2025, bildung__ganztag_gewuenscht="ja") == "nein"  # vor 2026/27 eingeschult


@pytest.mark.anforderung("ANF-SCH-05")
def test_bildung_und_teilhabe(plane_s):
    b = plane_s(kind(bezieht_wohngeld="ja"))
    assert b.ergebnisse()["bildung_und_teilhabe"] == "ja"
    assert b.eintrag("bildung_und_teilhabe").lebenslagen == ["schule"]
    assert plane_s(kind()).ergebnisse()["bildung_und_teilhabe"] == "nein"


@pytest.mark.anforderung("ANF-SCH-06", "ANF-WEB-08")
def test_szenarien_schule(kb):
    szen = [s for s in szenarien_mod.alle(kb) if "schule" in s.anfrage.lebenslagen]
    assert len(szen) >= 3
    assert any("unklar" in s.erwartet.values() for s in szen)
    for s in szen:
        assert szenarien_mod.abweichungen(s, planen(kb, s.anfrage)) == [], s.id
