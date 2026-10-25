"""Lebenslage Umzug (Fachmodul Umzug, #41 Schritt 1)."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

import pytest

from buergerai import szenarien as szenarien_mod
from buergerai.ausgabe import Farbe, bericht_json, bericht_text
from buergerai.planer import Anfrage, Bericht, planen
from buergerai.regeln import Wert
from buergerai.szenarien import fakten_parsen
from buergerai.web import api

STICHTAG = date(2026, 10, 24)


def umzug(**abweichungen: Any) -> dict[str, Any]:
    """Vollständig beschriebener Umzug von Freising nach München, ohne Hund, Auto und Leistungen."""
    fakten: dict[str, Any] = {
        "umzug.einzugsdatum": "2026-10-15",
        "umzug.ort_alt": "85354",
        "umzug.hund": "nein",
        "umzug.kfz_halter": "nein",
        "bezieht_wohngeld": "nein",
        "bezieht_buergergeld": "nein",
        "umzug.wegen_arbeit": "nein",
        "umzug.leistungsbezug": "nein",
    }
    for k, v in abweichungen.items():
        k = k.replace("__", ".")
        if v is None:
            fakten.pop(k, None)
        else:
            fakten[k] = v
    return fakten


@pytest.fixture
def plane_umzug(kb):
    def _plane(fakten: Optional[dict[str, Any]] = None, plz: str = "80331", lebenslagen=("umzug",)) -> Bericht:
        return planen(kb, Anfrage(fakten=fakten_parsen(kb, fakten or {}), plz=plz, lebenslagen=list(lebenslagen),
                                  stichtag=STICHTAG))

    return _plane


# ------------------------------------------------------------------ Anmeldung
@pytest.mark.anforderung("ANF-UMZ-01")
def test_anmeldung_frist_und_stellen(plane_umzug):
    e = plane_umzug(umzug()).eintrag("wohnsitz_anmelden")
    assert e.ergebnis is Wert.JA and e.leistung.art == "pflicht"
    assert e.zustaendigkeit.name == "Bürgerbüro der Landeshauptstadt München"
    spaetestens = [f for f in e.fristen if f.frist.art == "spaetestens"]
    assert [f.datum for f in spaetestens] == [date(2026, 10, 29)]  # 14 Tage nach dem 15.10.
    assert any(f.frist.art == "fruehestens" for f in e.fristen)  # München: erst nach dem Einzug
    berlin = plane_umzug(umzug(), plz="10115").eintrag("wohnsitz_anmelden")
    assert berlin.zustaendigkeit.name == "Bürgeramt (Berlin)" and berlin.variante.verfahren.online_url
    koeln = plane_umzug(umzug(), plz="50667").eintrag("wohnsitz_anmelden")
    assert koeln.zustaendigkeit.name == "Meldebehörde – Köln"
    assert koeln.variante.id == "wohnsitz_anmelden_bund"
    # Ohne Einzugsdatum: Pflicht bleibt, Frist ohne Datum
    ohne = plane_umzug(umzug(umzug__einzugsdatum=None)).eintrag("wohnsitz_anmelden")
    assert ohne.ergebnis is Wert.JA and ohne.fristen[0].datum is None


# ------------------------------------------------------------------ Pflichten und Leistungen nach Angaben
@pytest.mark.anforderung("ANF-UMZ-02")
def test_pflichten_nach_angaben(plane_umzug):
    b = plane_umzug(umzug())
    assert b.ergebnisse()["kfz_umzug"] == "nein"
    assert b.ergebnisse()["rundfunkbeitrag_umzug"] == "ja"
    assert b.ergebnisse()["wohngeld_umzug"] == "nein"
    assert b.ergebnisse()["adresse_an_leistungstraeger"] == "nein"
    b = plane_umzug(umzug(umzug__kfz_halter="ja", bezieht_wohngeld="ja", umzug__leistungsbezug="ja"))
    assert b.ergebnisse()["kfz_umzug"] == "ja"
    assert b.eintrag("kfz_umzug").zustaendigkeit.name == "Kfz-Zulassungsbehörde – Kreisfreie Stadt München"
    assert b.ergebnisse()["wohngeld_umzug"] == "ja"
    assert b.eintrag("wohngeld_umzug").zustaendigkeit.name == "Wohngeldbehörde – Kreisfreie Stadt München"
    assert b.ergebnisse()["adresse_an_leistungstraeger"] == "ja"
    assert b.fehlend == []


# ------------------------------------------------------------------ Hundesteuer und Ortsvergleich
@pytest.mark.anforderung("ANF-UMZ-03", "ANF-MOD-10")
def test_hundesteuer_an_und_abmelden(plane_umzug):
    b = plane_umzug(umzug(umzug__hund="ja"))
    an, ab = b.eintrag("hundesteuer_anmelden"), b.eintrag("hundesteuer_abmelden")
    assert an.ergebnis is ab.ergebnis is Wert.JA
    assert an.zustaendigkeit.name == "Landeshauptstadt München – Hundesteuer"
    assert an.fristen[0].datum == date(2026, 10, 29)
    assert ab.zustaendigkeit.name == "Steueramt der Gemeinde – Freising"  # bisheriger Wohnort
    assert ab.gebiet.id == "DE"  # Satzung Freising nicht erfasst
    # Wegzug aus München: Abmeldung mit Münchner Stelle
    weg = plane_umzug(umzug(umzug__hund="ja", umzug__ort_alt="80331"), plz="85354").eintrag("hundesteuer_abmelden")
    assert weg.zustaendigkeit.name == "Landeshauptstadt München – Hundesteuer"
    # Innerhalb derselben Gemeinde: weder an- noch abmelden
    innen = plane_umzug(umzug(umzug__hund="ja", umzug__ort_alt="80469"))
    assert innen.ergebnisse()["hundesteuer_anmelden"] == innen.ergebnisse()["hundesteuer_abmelden"] == "nein"


@pytest.mark.anforderung("ANF-MOD-10")
def test_ortsvergleich_abgeleitet_und_erfragt(plane_umzug):
    # Bisheriger Ort fehlt: es wird der Ort erfragt, nicht der abgeleitete Fakt
    b = plane_umzug(umzug(umzug__hund="ja", umzug__ort_alt=None))
    assert b.eintrag("hundesteuer_anmelden").ergebnis is Wert.UNKLAR
    assert "umzug.ort_alt" in b.fehlend and "umzug.gleiche_gemeinde" not in b.fehlend
    # "weiß nicht" beim Ort: Vergleich unbekannt, keine Rückfrage
    b = plane_umzug(umzug(umzug__hund="ja", umzug__ort_alt="unbekannt"))
    assert b.eintrag("hundesteuer_anmelden").ergebnis is Wert.UNKLAR and b.fehlend == []
    # PLZ mit mehreren Gemeinden: Gemeinde nicht eindeutig, also unklar
    b = plane_umzug(umzug(umzug__hund="ja", umzug__ort_alt="85356"))
    assert b.eintrag("hundesteuer_anmelden").ergebnis is Wert.UNKLAR
    # Der abgeleitete Fakt kann nicht von außen gesetzt werden
    with pytest.raises(Exception, match="automatisch abgeleitet"):
        plane_umzug(umzug(umzug__gleiche_gemeinde="ja"))


# ------------------------------------------------------------------ Umzugskosten
@pytest.mark.anforderung("ANF-UMZ-04", "ANF-UMZ-05")
def test_umzugskosten_jobcenter(plane_umzug):
    b = plane_umzug(umzug(bezieht_buergergeld="ja"), plz="10115")
    e = b.eintrag("umzugskosten_jobcenter")
    assert e.ergebnis is Wert.UNKLAR  # Notwendigkeit und Angemessenheit prüft das Jobcenter
    assert e.zustaendigkeit.name == "Jobcenter – Landkreis Freising"  # bisheriger Wohnort
    assert e.fristen[0].datum == date(2026, 10, 14) and e.fristen[0].abgelaufen  # vor dem Umzug
    assert not e.leistung.rechtsanspruch
    assert plane_umzug(umzug()).ergebnisse()["umzugskosten_jobcenter"] == "nein"


@pytest.mark.anforderung("ANF-UMZ-05")
def test_umzugskosten_arbeitsagentur(kb, plane_umzug):
    b = plane_umzug(umzug(umzug__wegen_arbeit="ja", arbeitsuchend_gemeldet="ja"))
    e = b.eintrag("umzugskosten_arbeitsagentur")
    assert e.ergebnis is Wert.UNKLAR and not e.leistung.rechtsanspruch
    assert "Kein Rechtsanspruch" in bericht_text(b, kb, Farbe(False))
    assert plane_umzug(umzug(umzug__wegen_arbeit="ja", arbeitsuchend_gemeldet="nein")).ergebnisse()[
        "umzugskosten_arbeitsagentur"] == "nein"


# ------------------------------------------------------------------ Abdeckung und nicht erfasst
@pytest.mark.anforderung("ANF-UMZ-06", "ANF-MOD-11")
def test_abdeckung_und_nicht_erfasst(kb, plane_umzug):
    from buergerai import gebiete

    for land in gebiete.laender(kb):
        nachweis = kb.landesabdeckung[(land.id, "umzug")]
        assert nachweis.landesleistungen == ("erfasst" if land.id == "04" else "keine"), land.name
        assert nachweis.quellen and "25.10.2026" in (nachweis.notiz or "")
        # Je Land ein eigener Beleg, nicht nur der allgemeine Ratgeber (außer NI und SL)
        if land.id not in ("03", "10"):
            assert set(nachweis.quellen) != {"ratgeber_umzugspraemien"}, land.name
    b = plane_umzug(umzug())
    assert not any("Landesleistungen" in w for w in b.warnungen)
    namen = [n for _, n, _ in b.nicht_erfasst]
    assert "Abmeldung bei Umzug ins Ausland" in namen and all(g for _, _, g in b.nicht_erfasst)
    text = bericht_text(b, kb, Farbe(False))
    assert "== Noch nicht erfasst (7) ==" in text and "Zweitwohnungsteuer" in text
    assert bericht_json(b)["nicht_erfasst"][0]["lebenslage"] == "umzug"
    web = api.bericht(kb, {"plz": "80331", "lebenslagen": ["umzug"], "fakten": {}})
    assert {n["lebenslage"] for n in web["nicht_erfasst"]} == {"Umzug"}
    # Nur Geburt gewählt: keine Umzugsthemen
    assert api.bericht(kb, {"plz": "80331", "fakten": {}})["nicht_erfasst"] == []


@pytest.mark.anforderung("ANF-MOD-06")
def test_kommunale_leistung_nicht_als_andere_laender(kb, plane_umzug):
    """München-Varianten (Gemeinde) erscheinen in Köln nicht als 'nur in anderen Ländern'."""
    b = plane_umzug(umzug(), plz="50667")
    assert [n.leistung.id for n in b.nur_andere_laender] == ["begruessungsgeld_studium"]  # Landesleistung Bremen


# ------------------------------------------------------------------ Szenarien und Terminal = Web
@pytest.mark.anforderung("ANF-UMZ-01", "ANF-WEB-08")
def test_szenarien_umzug(kb):
    umzug_szenarien = [s for s in szenarien_mod.alle(kb) if "umzug" in s.anfrage.lebenslagen]
    assert len(umzug_szenarien) >= 3
    assert any("unklar" in s.erwartet.values() for s in umzug_szenarien)
    for s in umzug_szenarien:
        assert szenarien_mod.abweichungen(s, planen(kb, s.anfrage)) == [], s.id


@pytest.mark.anforderung("ANF-UMZ-07")
def test_begruessungsgeld_bremen(plane_umzug):
    studium = umzug(umzug__ort_alt="30159", umzug__fuer_studium_ausbildung="ja")
    b = plane_umzug(studium, plz="28195")
    e = b.eintrag("begruessungsgeld_studium")
    assert e.ergebnis is Wert.UNKLAR  # Hochschule, 12 Monate, Frist prüft das Service-Center
    assert e.gebiet.id == "04" and "Universität Bremen" in e.zustaendigkeit.name
    assert not e.leistung.rechtsanspruch
    # Umzug innerhalb des Landes Bremen (Bremerhaven -> Bremen) zählt nicht als Zuzug
    innen = plane_umzug(umzug(umzug__ort_alt="27576", umzug__fuer_studium_ausbildung="ja"), plz="28195")
    assert innen.ergebnisse()["begruessungsgeld_studium"] == "nein"
    assert plane_umzug(umzug(umzug__ort_alt="30159", umzug__fuer_studium_ausbildung="nein"), plz="28195").ergebnisse()[
        "begruessungsgeld_studium"] == "nein"
    # Außerhalb Bremens: nur in anderen Ländern
    muenchen = plane_umzug(umzug(umzug__fuer_studium_ausbildung="ja"))
    assert "begruessungsgeld_studium" not in muenchen.ergebnisse()
    assert [g.kuerzel for n in muenchen.nur_andere_laender if n.leistung.id == "begruessungsgeld_studium" for g in n.laender] == ["HB"]
