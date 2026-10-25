from datetime import date

import pytest

from buergerai.fakten import UNBEKANNT
from buergerai.regeln import RegelFehler, Wert, auswerten, begruendung, fakten_in_regel

JA = {"fakt": "a", "op": "==", "wert": True, "text": "a"}
B = {"fakt": "b", "op": "==", "wert": True, "text": "b"}


def w(regel, fakten, person=None):
    return auswerten(regel, fakten, person).wert


@pytest.mark.anforderung("ANF-ENG-01")
@pytest.mark.parametrize(
    "a,b,und,oder",
    [
        (True, True, Wert.JA, Wert.JA),
        (True, False, Wert.NEIN, Wert.JA),
        (False, False, Wert.NEIN, Wert.NEIN),
        (True, None, Wert.UNKLAR, Wert.JA),
        (False, None, Wert.NEIN, Wert.UNKLAR),
        (None, None, Wert.UNKLAR, Wert.UNKLAR),
    ],
)
def test_kleene_logik(a, b, und, oder):
    fakten = {k: v for k, v in (("a", a), ("b", b)) if v is not None}
    assert w({"alle": [JA, B]}, fakten) is und
    assert w({"eine": [JA, B]}, fakten) is oder


@pytest.mark.anforderung("ANF-ENG-01")
def test_nicht_und_leere_listen():
    nicht = {"nicht": JA, "text": "nicht a"}
    assert w(nicht, {"a": True}) is Wert.NEIN
    assert w(nicht, {"a": False}) is Wert.JA
    assert w(nicht, {}) is Wert.UNKLAR
    assert w({"alle": []}, {}) is Wert.JA
    assert w({"eine": []}, {}) is Wert.NEIN


@pytest.mark.anforderung("ANF-ENG-02")
def test_fehlender_fakt_ist_unklar_nicht_nein():
    s = auswerten({"fakt": "x", "op": ">=", "wert": 3, "text": "x"}, {})
    assert s.wert is Wert.UNKLAR
    assert s.fehlend == ["x"]


@pytest.mark.anforderung("ANF-ENG-03")
def test_keine_rueckfrage_wenn_entschieden():
    # Und: ein Nein entscheidet – fehlendes b wird nicht erfragt
    assert auswerten({"alle": [JA, B]}, {"a": False}).fehlend == []
    # Oder: ein Ja entscheidet
    assert auswerten({"eine": [JA, B]}, {"a": True}).fehlend == []
    # Sonst wird gefragt
    assert auswerten({"alle": [JA, B]}, {"a": True}).fehlend == ["b"]


@pytest.mark.anforderung("ANF-ENG-04")
def test_weiss_nicht():
    s = auswerten(JA, {"a": UNBEKANNT})
    assert s.wert is Wert.UNKLAR and s.fehlend == []


@pytest.mark.anforderung("ANF-ENG-05")
def test_pruefung_noetig_nie_ja():
    regel = {"eine": [JA, {"pruefung_noetig": "manuell"}]}
    assert w(regel, {"a": True}) is Wert.JA
    assert w(regel, {"a": False}) is Wert.UNKLAR
    assert w({"alle": [JA, {"pruefung_noetig": "manuell"}]}, {"a": True}) is Wert.UNKLAR


@pytest.mark.anforderung("ANF-ENG-06")
def test_begruendung_zeigt_ausschlaggebende_bedingungen():
    regel = {"alle": [dict(JA, quellen=["q1"]), dict(B, quellen=["q2"])]}
    s = auswerten(regel, {"a": True, "b": False})
    gruende = begruendung(s)
    assert [(g.text, g.wert) for g in gruende] == [("b", Wert.NEIN)]
    assert gruende[0].quellen == ("q2",)
    assert gruende[0].ist is False


@pytest.mark.anforderung("ANF-ENG-07")
def test_datumsvergleich():
    regel = {"fakt": "d", "op": ">=", "wert": "2025-04-01", "text": "ab April 2025"}
    assert w(regel, {"d": date(2025, 4, 1)}) is Wert.JA
    assert w(regel, {"d": date(2025, 3, 31)}) is Wert.NEIN
    assert w({"fakt": "d", "op": "in", "wert": ["2025-01-01"], "text": "t"}, {"d": date(2025, 1, 1)}) is Wert.JA


@pytest.mark.anforderung("ANF-ENG-08")
def test_personenfakten():
    regel = {"fakt": "person.x", "op": "==", "wert": 1, "text": "x"}
    fakten = {"mutter.x": 1, "partner.x": 2}
    assert w(regel, fakten, "mutter") is Wert.JA
    assert w(regel, fakten, "partner") is Wert.NEIN
    with pytest.raises(RegelFehler):
        auswerten(regel, fakten, None)


def test_operatoren_und_fehler():
    for op, wert, erwartet in [("!=", 2, True), ("<", 2, True), ("<=", 1, True), (">", 0, True), ("nicht_in", [2], True)]:
        assert w({"fakt": "x", "op": op, "wert": wert, "text": "t"}, {"x": 1}) is (Wert.JA if erwartet else Wert.NEIN)
    with pytest.raises(RegelFehler):
        auswerten({"fakt": "x", "op": "~", "wert": 1, "text": "t"}, {"x": 1})
    with pytest.raises(RegelFehler):
        auswerten({"alle": [], "eine": []}, {})
    with pytest.raises(RegelFehler):
        auswerten({"fakt": "x", "op": "<", "wert": 1, "text": "t"}, {"x": "text"})


def test_fakten_in_regel():
    assert fakten_in_regel({"alle": [JA, {"nicht": B, "text": "t"}, JA]}) == ["a", "b"]
