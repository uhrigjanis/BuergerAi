"""Lebenslage Geringes Einkommen (Fachmodul Einkommen, #41 Schritt 2) und Regelknoten 'lebenslage'."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

import pytest

from buergerai import szenarien as szenarien_mod
from buergerai.planer import Anfrage, Bericht, planen
from buergerai.regeln import Wert, auswerten, begruendung
from buergerai.szenarien import fakten_parsen
from buergerai.wissensbasis import DatenFehler, Wissensbasis
from test_wissensbasis import bearbeite, kopie

STICHTAG = date(2026, 10, 24)


def haushalt(**abweichungen: Any) -> dict[str, Any]:
    """Alleinstehend, 40 Jahre, erwerbsfähig, zur Miete, ohne Leistungen und Kinder."""
    fakten: dict[str, Any] = {
        "bezieht_buergergeld": "nein",
        "bezieht_sozialhilfe": "nein",
        "bezieht_asylbewerberleistungen": "nein",
        "bezieht_wohngeld": "nein",
        "bezieht_kinderzuschlag": "nein",
        "kinder_im_haushalt": 0,
        "alter": 40,
        "einkommen.erwerbsfaehig": "ja",
        "einkommen.wohnkosten": "miete",
        "einkommen.ausbildungsfoerderung_ohne_eltern": "nein",
        "einkommen.gesetzlich_versichert": "ja",
    }
    for k, v in abweichungen.items():
        k = k.replace("__", ".")
        if v is None:
            fakten.pop(k, None)
        else:
            fakten[k] = v
    return fakten


@pytest.fixture
def plane_ek(kb):
    def _plane(fakten: Optional[dict[str, Any]] = None, plz: str = "80331", lebenslagen=("geringes_einkommen",)) -> Bericht:
        return planen(kb, Anfrage(fakten=fakten_parsen(kb, fakten or {}), plz=plz, lebenslagen=list(lebenslagen),
                                  stichtag=STICHTAG))

    return _plane


# ------------------------------------------------------------------ Grundsicherung
@pytest.mark.anforderung("ANF-EINK-01")
def test_grundsicherungsgeld(plane_ek):
    assert plane_ek(haushalt()).ergebnisse()["grundsicherungsgeld"] == "unklar"  # Bedarfsrechnung beim Jobcenter
    assert plane_ek(haushalt(bezieht_buergergeld="ja")).ergebnisse()["grundsicherungsgeld"] == "ja"
    assert plane_ek(haushalt(einkommen__erwerbsfaehig="nein")).ergebnisse()["grundsicherungsgeld"] == "nein"
    assert plane_ek(haushalt(alter=14)).ergebnisse()["grundsicherungsgeld"] == "nein"
    assert plane_ek(haushalt(alter=67)).ergebnisse()["grundsicherungsgeld"] == "nein"
    assert plane_ek(haushalt(alter=66)).ergebnisse()["grundsicherungsgeld"] == "unklar"  # Regelaltersgrenze je Jahrgang
    e = plane_ek(haushalt()).eintrag("grundsicherungsgeld")
    assert e.leistung.name == "Grundsicherungsgeld (früher Bürgergeld)"
    assert e.betrag.text.startswith("Regelbedarf 563 €")
    assert e.zustaendigkeit.name == "Jobcenter – Kreisfreie Stadt München"


@pytest.mark.anforderung("ANF-EINK-02")
def test_grundsicherung_alter_und_erwerbsminderung(plane_ek):
    assert plane_ek(haushalt(alter=70)).ergebnisse()["grundsicherung_alter_em"] == "unklar"
    assert plane_ek(haushalt(alter=40)).ergebnisse()["grundsicherung_alter_em"] == "nein"  # erwerbsfähig
    em = haushalt(alter=40, einkommen__erwerbsfaehig="nein", einkommen__voll_erwerbsgemindert="ja")
    assert plane_ek(em).ergebnisse()["grundsicherung_alter_em"] == "unklar"
    assert plane_ek(haushalt(bezieht_sozialhilfe="ja")).ergebnisse()["grundsicherung_alter_em"] == "ja"
    # Erwerbsfähig: keine Frage nach Erwerbsminderung
    assert "einkommen.voll_erwerbsgemindert" not in plane_ek(haushalt()).fehlend


# ------------------------------------------------------------------ Wohngeld
@pytest.mark.anforderung("ANF-EINK-03")
def test_wohngeld_ausschluesse(plane_ek):
    assert plane_ek(haushalt()).ergebnisse()["wohngeld"] == "unklar"
    assert plane_ek(haushalt(bezieht_wohngeld="ja")).ergebnisse()["wohngeld"] == "ja"
    for ausschluss in ("bezieht_buergergeld", "bezieht_sozialhilfe", "bezieht_asylbewerberleistungen"):
        assert plane_ek(haushalt(**{ausschluss: "ja"})).ergebnisse()["wohngeld"] == "nein", ausschluss
    assert plane_ek(haushalt(einkommen__wohnkosten="keine")).ergebnisse()["wohngeld"] == "nein"
    assert plane_ek(haushalt(einkommen__wohnkosten="eigentum")).ergebnisse()["wohngeld"] == "unklar"


# ------------------------------------------------------------------ Bildung und Teilhabe, Rundfunk
@pytest.mark.anforderung("ANF-EINK-04")
def test_bildung_und_teilhabe(plane_ek):
    assert plane_ek(haushalt(kinder_im_haushalt=2)).ergebnisse()["bildung_und_teilhabe"] == "nein"  # keine Leistung
    for leistung in ("bezieht_buergergeld", "bezieht_sozialhilfe", "bezieht_wohngeld", "bezieht_kinderzuschlag",
                     "bezieht_asylbewerberleistungen"):
        b = plane_ek(haushalt(kinder_im_haushalt=1, **{leistung: "ja"}))
        assert b.ergebnisse()["bildung_und_teilhabe"] == "ja", leistung
    assert plane_ek(haushalt(bezieht_wohngeld="ja")).ergebnisse()["bildung_und_teilhabe"] == "nein"  # ohne Kinder
    e = plane_ek(haushalt(kinder_im_haushalt=1, bezieht_wohngeld="ja"), plz="34225").eintrag("bildung_und_teilhabe")
    assert e.zustaendigkeit.name == "Jobcenter bzw. Stelle für Bildung und Teilhabe – Landkreis Kassel"


@pytest.mark.anforderung("ANF-EINK-05")
def test_rundfunkbefreiung(plane_ek):
    assert plane_ek(haushalt(bezieht_buergergeld="ja")).ergebnisse()["rundfunkbeitrag_befreiung"] == "ja"
    assert plane_ek(haushalt(einkommen__ausbildungsfoerderung_ohne_eltern="ja")).ergebnisse()["rundfunkbeitrag_befreiung"] == "ja"
    b = plane_ek(haushalt(bezieht_wohngeld="ja"))
    assert b.ergebnisse()["rundfunkbeitrag_befreiung"] == "nein"
    assert any("Wohngeld" in h for h in b.eintrag("rundfunkbeitrag_befreiung").variante.hinweise)


# ------------------------------------------------------------------ Landes- und Kommunalleistungen
@pytest.mark.anforderung("ANF-EINK-06")
def test_sozialticket_der_laender(kb, plane_ek):
    berlin = plane_ek(haushalt(bezieht_wohngeld="ja"), plz="10115")
    assert berlin.ergebnisse()["sozialticket"] == "ja"
    assert "Berlin-Ticket S" in berlin.eintrag("sozialticket").zustaendigkeit.name
    # Hamburg: Wohngeld allein reicht nicht, Grundsicherungsgeld schon
    assert plane_ek(haushalt(bezieht_wohngeld="ja"), plz="20095").ergebnisse()["sozialticket"] == "nein"
    assert plane_ek(haushalt(bezieht_buergergeld="ja"), plz="20095").ergebnisse()["sozialticket"] == "ja"
    # Hessen: widersprüchliche Quellen, höchstens Unklar
    hessen = plane_ek(haushalt(bezieht_buergergeld="ja"), plz="34225").eintrag("sozialticket")
    assert hessen.ergebnis is Wert.UNKLAR and hessen.pruefstatus.value == "widerspruechlich"
    # Brandenburg: Grundsicherungsgeld ja, sonst unklar
    assert plane_ek(haushalt(bezieht_buergergeld="ja"), plz="14467").ergebnisse()["sozialticket"] == "ja"
    assert plane_ek(haushalt(bezieht_wohngeld="ja"), plz="14467").ergebnisse()["sozialticket"] == "unklar"
    # Bayern: kein Sozialticket des Landes, aber München-Pass
    muenchen = plane_ek(haushalt(bezieht_buergergeld="ja"))
    assert "sozialticket" not in muenchen.ergebnisse()
    andere = {n.leistung.id: [g.kuerzel for g in n.laender] for n in muenchen.nur_andere_laender}
    assert andere["sozialticket"] == ["BE", "BB", "HH", "HE"]
    assert muenchen.ergebnisse()["sozialpass"] == "ja"
    # Andere Gemeinden in Bayern: kein München-Pass und kein Eintrag "nur in anderen Ländern" dafür
    freising = plane_ek(haushalt(bezieht_buergergeld="ja"), plz="85354")
    assert "sozialpass" not in freising.ergebnisse() and "sozialpass" not in andere
    for kz in ("11", "02", "06", "12"):
        assert kb.landesabdeckung[(kz, "geringes_einkommen")].landesleistungen == "erfasst"
    assert any("Bayern ist noch nicht erfasst" in w for w in muenchen.warnungen)
    assert not any("Landesleistungen" in w for w in berlin.warnungen)


# ------------------------------------------------------------------ Kinderzuschlag in zwei Lebenslagen
@pytest.mark.anforderung("ANF-EINK-07", "ANF-MOD-02")
def test_kinderzuschlag_geteilt(plane_ek):
    nur_einkommen = plane_ek(haushalt(kinder_im_haushalt=0, partner_im_haushalt="ja", brutto_haushalt_monat=2000))
    e = nur_einkommen.eintrag("kinderzuschlag")
    assert e.ergebnis is Wert.NEIN and e.lebenslagen == ["geringes_einkommen"]
    assert "kind_lebt_im_haushalt" not in nur_einkommen.fehlend  # Geburt nicht gewählt: keine Frage zum Neugeborenen
    mit_kind = plane_ek(haushalt(kinder_im_haushalt=1, partner_im_haushalt="ja", brutto_haushalt_monat=2000))
    assert mit_kind.ergebnisse()["kinderzuschlag"] == "unklar"  # Bedarfsrechnung (KiZ-Lotse)
    beide = plane_ek({"kind_lebt_im_haushalt": "ja", "kinder_im_haushalt": 0, "partner_im_haushalt": "ja",
                      "brutto_haushalt_monat": 2000}, lebenslagen=("geburt", "geringes_einkommen"))
    assert [x.leistung.id for x in beide.eintraege].count("kinderzuschlag") == 1
    assert beide.eintrag("kinderzuschlag").lebenslagen == ["geburt", "geringes_einkommen"]
    assert beide.ergebnisse()["kinderzuschlag"] == "unklar"  # Neugeborenes zählt


# ------------------------------------------------------------------ Regelknoten 'lebenslage'
@pytest.mark.anforderung("ANF-MOD-12")
def test_regelknoten_lebenslage():
    knoten = {"lebenslage": "geburt", "text": "Bei der Geburt: X", "regel": {"fakt": "x", "op": "==", "wert": True, "text": "X"}}
    assert auswerten(knoten, {"x": True}).wert is Wert.JA  # ohne Angabe gelten alle Lebenslagen
    assert auswerten(knoten, {"x": True}, lebenslagen={"geburt"}).wert is Wert.JA
    aus = auswerten(knoten, {}, lebenslagen={"umzug"})
    assert aus.wert is Wert.NEIN and aus.fehlend == []
    assert "gilt nur, wenn diese Lebenslage gewählt ist" in begruendung(aus)[0].text
    offen = auswerten(knoten, {}, lebenslagen={"geburt"})
    assert offen.wert is Wert.UNKLAR and offen.fehlend == ["x"]


@pytest.mark.anforderung("ANF-MOD-12")
@pytest.mark.parametrize("aendern,meldung", [
    (lambda k: k.update(lebenslage="umzug"), "zu der die Leistung nicht gehört"),
    (lambda k: k.update(lebenslage="gibt_es_nicht"), "unbekannte Lebenslage gibt_es_nicht"),
    (lambda k: k.pop("text"), "'lebenslage'-Knoten braucht einen 'text'"),
])
def test_regelknoten_lebenslage_wird_geprueft(tmp_path, aendern, meldung):
    daten = kopie(tmp_path)

    def bearbeiten(d):
        v = next(v for v in d["varianten"] if v["id"] == "kinderzuschlag_bund")
        aendern(v["regel"]["alle"][0]["eine"][0])

    bearbeite(daten / "fachmodule" / "familie" / "geburt.json", bearbeiten)
    with pytest.raises(DatenFehler) as info:
        Wissensbasis.laden(daten)
    assert any(meldung in f for f in info.value.fehler), info.value.fehler


# ------------------------------------------------------------------ Szenarien
@pytest.mark.anforderung("ANF-EINK-01", "ANF-WEB-08")
def test_szenarien_einkommen(kb):
    liste = [s for s in szenarien_mod.alle(kb) if "geringes_einkommen" in s.anfrage.lebenslagen]
    assert len(liste) >= 3
    assert any("unklar" in s.erwartet.values() for s in liste)
    for s in liste:
        assert szenarien_mod.abweichungen(s, planen(kb, s.anfrage)) == [], s.id
