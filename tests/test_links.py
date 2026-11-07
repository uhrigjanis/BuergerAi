"""Links zu Antragsformularen, Portalen, Vorab-Checks und Infoseiten (#36)."""

from __future__ import annotations

import pytest

from buergerai import szenarien as szenarien_mod
from buergerai.ausgabe import KEIN_ANTRAG, LINK_TEXT, Farbe, bericht_text, link_hinweise
from buergerai.modell import LINK_ARTEN
from buergerai.planer import Anfrage, planen
from buergerai.regeln import Wert
from buergerai.web import api
from buergerai.wissensbasis import DatenFehler, Wissensbasis
from conftest import STICHTAG, familie
from test_wissensbasis import bearbeite, kopie

FREISING = "85354"
MUENCHEN = "80331"


def link(art: str, url: str, quelle: str = "pstg_18") -> dict:
    return {"art": art, "url": url, "quellen": [quelle]}


def variante(d: dict, vid: str) -> dict:
    return next(v for v in d["varianten"] if v["id"] == vid)


@pytest.fixture(scope="module")
def link_kb(tmp_path_factory) -> Wissensbasis:
    """Wissensbasis mit Test-Links: alle Arten beim Kindergeld, Geburtsanzeige auf allen Ebenen."""
    daten = kopie(tmp_path_factory.mktemp("links"))

    def bund(d):
        variante(d, "kindergeld_bund")["links"] += [
            link("rechner", "https://example.org/rechner"),
            link("formular", "https://example.org/formular"),
            link("portal", "https://example.org/portal"),
        ]
        variante(d, "geburtsanzeige_bund")["links"] = [
            link("info", "https://example.org/bund-info"),
            link("portal", "https://example.org/bund-portal"),
        ]

    def land(d):
        variante(d, "geburtsanzeige_by")["links"] = [
            link("formular", "https://example.org/by-formular"),
            link("portal", "https://example.org/by-portal"),
        ]

    bearbeite(daten / "fachmodule" / "familie" / "geburt.json", bund)
    bearbeite(daten / "laender" / "by" / "geburt.json", land)
    return Wissensbasis.laden(daten)


def plane(kb: Wissensbasis, plz: str):
    from buergerai.szenarien import fakten_parsen

    return planen(kb, Anfrage(fakten=fakten_parsen(kb, familie()), plz=plz, stichtag=STICHTAG))


# ------------------------------------------------------------------ ANF-LNK-01
@pytest.mark.anforderung("ANF-LNK-01")
def test_feste_reihenfolge_und_beschriftung(link_kb):
    e = plane(link_kb, MUENCHEN).eintrag("kindergeld")
    assert [l.art for l in e.links] == list(LINK_ARTEN) == ["formular", "portal", "rechner", "info"]
    assert LINK_TEXT["formular"] == "Antrag stellen"
    assert LINK_TEXT["rechner"] == "Vorab prüfen" and "antrag" not in LINK_TEXT["rechner"].lower()


@pytest.mark.anforderung("ANF-LNK-01")
def test_kiz_lotse_ist_rechner_kein_antrag(kb, plane):
    e = plane(familie()).eintrag("kinderzuschlag")
    assert [(l.art, l.url) for l in e.links] == [("rechner", "https://www.arbeitsagentur.de/familie-und-kinder/kiz-lotse")]
    json_links = next(l for l in api.bericht(kb, {"plz": MUENCHEN, "stichtag": STICHTAG.isoformat(),
                                                    "fakten": {}})["leistungen"] if l["id"] == "kinderzuschlag")["links"]
    assert json_links[0]["text"] == "Vorab prüfen"
    assert KEIN_ANTRAG in link_hinweise(e)


# ------------------------------------------------------------------ ANF-LNK-02
@pytest.mark.anforderung("ANF-LNK-02")
def test_fallback_auf_das_land_mit_hinweis(link_kb):
    """Freising hat keine Gemeindevariante: Antrag und Portal des Landes, Infoseite des Bundes."""
    e = plane(link_kb, FREISING).eintrag("geburtsanzeige")
    assert [(l.art, l.url, l.gebiet.id, l.ist_fallback) for l in e.links] == [
        ("formular", "https://example.org/by-formular", "09", True),
        ("portal", "https://example.org/by-portal", "09", True),
        ("info", "https://example.org/bund-info", "DE", True),
    ]
    assert e.verwaltungsgebiet.name == "Freising"
    assert link_hinweise(e) == ["Kein Antrags-Link für Freising erfasst, hier der Antrag des Landes Bayern."]


@pytest.mark.anforderung("ANF-LNK-02")
def test_spezifischster_link_je_art(link_kb):
    """München: eigene Infoseite (Gemeinde), Antrag und Portal vom Land.

    Das Bundesportal erbt die Münchner Variante per erbt_von, es bleibt aber ein
    Bundeslink und verliert gegen das Landesportal.
    """
    muenchen = link_kb.varianten["geburtsanzeige_muenchen"]
    assert {(l.art, l.gebiet_id) for l in muenchen.links} == {("info", "09162000"), ("portal", "DE")}
    e = plane(link_kb, MUENCHEN).eintrag("geburtsanzeige")
    assert [(l.art, l.gebiet.id, l.ist_fallback) for l in e.links] == [
        ("formular", "09", True), ("portal", "09", True), ("info", "09162000", False),
    ]
    assert "Kein Antrags-Link für München" in link_hinweise(e)[0]


@pytest.mark.anforderung("ANF-LNK-02")
def test_kein_fallback_bei_bundesleistung(kb, plane):
    e = plane(familie()).eintrag("kindergeld")
    assert [(l.art, l.gebiet.id, l.ist_fallback) for l in e.links] == [("info", "DE", False)]


@pytest.mark.anforderung("ANF-LNK-02", "ANF-DAT-07")
def test_eigene_art_ersetzt_geerbte(kb):
    """Berlin erbt die Bundesvariante: eigene Infoseite, Portal des Bundes bleibt Bundeslink."""
    berlin = kb.varianten["wohnsitz_anmelden_berlin"]
    assert [(l.art, l.gebiet_id) for l in berlin.links] == [("info", "11000000"), ("portal", "DE")]


# ------------------------------------------------------------------ ANF-LNK-03
@pytest.mark.anforderung("ANF-LNK-03")
@pytest.mark.parametrize("links,meldung", [
    ([{"art": "formular", "url": "https://example.org"}], "braucht mindestens eine Quelle"),
    ([link("antrag", "https://example.org")], "unbekannte Art 'antrag'"),
    ([link("formular", "http://example.org")], "nur https://"),
    ([link("formular", "https://example.org/a b")], "nur https://"),
    ([link("formular", "https://example.org", "gibt_es_nicht")], "unbekannte Quelle gibt_es_nicht"),
    ([link("info", "https://example.org/a"), link("info", "https://example.org/b")], "mehrere Links der Art info"),
])
def test_konsistenzpruefung_der_links(tmp_path, links, meldung):
    daten = kopie(tmp_path)
    bearbeite(daten / "fachmodule" / "familie" / "geburt.json",
              lambda d: variante(d, "geburtsanzeige_bund").update(links=links))
    with pytest.raises(DatenFehler) as info:
        Wissensbasis.laden(daten)
    assert any(meldung in f for f in info.value.fehler), info.value.fehler


@pytest.mark.anforderung("ANF-LNK-03")
def test_online_url_gibt_es_nicht_mehr(tmp_path):
    daten = kopie(tmp_path)
    bearbeite(daten / "fachmodule" / "familie" / "geburt.json",
              lambda d: variante(d, "kindergeld_bund")["verfahren"].update(online_url="https://example.org"))
    with pytest.raises(DatenFehler, match="online_url' entfällt"):
        Wissensbasis.laden(daten)


@pytest.mark.anforderung("ANF-LNK-03")
def test_pruefstatus_je_link(kb, plane):
    e = plane(familie(), plz=FREISING).eintrag("vaterschaftsanerkennung")
    quelle = kb.quellen["freising_belehrung_vaterschaft"]
    assert [(l.art, l.pruefstatus) for l in e.links] == [("info", quelle.pruefstatus)]
    assert all(l.url.startswith("https://") for v in kb.varianten.values() for l in v.links)


# ------------------------------------------------------------------ ANF-LNK-04
@pytest.mark.anforderung("ANF-LNK-04")
def test_ohne_link_ehrlicher_hinweis(plane):
    e = plane(familie(), plz=FREISING).eintrag("geburtsanzeige")
    assert e.links == [] and link_hinweise(e) == [KEIN_ANTRAG]


@pytest.mark.anforderung("ANF-LNK-04")
def test_pilot_jede_leistung_mit_link_oder_hinweis(kb):
    for s in szenarien_mod.alle(kb):
        if s.anfrage.lebenslagen != ["geburt"] or s.anfrage.plz not in (MUENCHEN, FREISING):
            continue
        for e in planen(kb, s.anfrage).eintraege:
            assert e.links or link_hinweise(e), (s.id, e.leistung.id)


@pytest.mark.anforderung("ANF-LNK-04", "ANF-WEB-08")
def test_web_und_terminal_zeigen_dieselben_links(kb):
    for s in szenarien_mod.alle(kb):
        bericht = planen(kb, s.anfrage)
        web = {l["id"]: l for l in api.bericht(kb, api.szenario(kb, s.id))["leistungen"]}
        text = bericht_text(bericht, kb, Farbe(False), details=True)
        for e in bericht.eintraege:
            w = web[e.leistung.id]
            assert [(l["art"], l["url"]) for l in w["links"]] == [(l.art, l.url) for l in e.links], s.id
            assert w["link_hinweise"] == link_hinweise(e)
            if e.ergebnis is not Wert.NEIN:
                for l in e.links:
                    assert f"{LINK_TEXT[l.art]}: {l.url}" in text, (s.id, e.leistung.id)
