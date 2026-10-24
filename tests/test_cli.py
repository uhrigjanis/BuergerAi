import json

import pytest

from buergerai.cli import main


def lauf(capsys, *argv, eingaben=None, monkeypatch=None):
    if eingaben is not None:
        it = iter(eingaben)
        monkeypatch.setattr("builtins.input", lambda _prompt="": next(it))
    code = main(["--keine-farbe", *argv])
    out = capsys.readouterr()
    return code, out.out, out.err


@pytest.mark.anforderung("ANF-CLI-01")
def test_pruefen_text(capsys):
    code, out, _ = lauf(capsys, "pruefen", "-s", "muenchen_verheiratet_angestellt", "--details")
    assert code == 0
    assert "Standesamt München" in out and "Unterlagen:" in out and "Quellen:" in out


@pytest.mark.anforderung("ANF-CLI-01")
def test_pruefen_json(capsys):
    code, out, _ = lauf(capsys, "pruefen", "--plz", "85354", "--stichtag", "2026-10-24",
                        "-f", "kind_geboren=nein", "-f", "errechneter_termin=01.02.2027", "--json")
    daten = json.loads(out)
    assert code == 0
    assert daten["hierarchie"][0]["name"] == "Freising"
    assert {l["id"] for l in daten["leistungen"]} >= {"elterngeld", "kindergeld", "geburtsanzeige"}
    assert "partner_im_haushalt" in daten["fehlende_angaben"]


@pytest.mark.anforderung("ANF-CLI-02", "ANF-ENG-04")
def test_interaktiv(capsys, monkeypatch, tmp_path):
    ziel = tmp_path / "ich.json"
    eingaben = [
        "80331",  # PLZ
        "nein",   # kind_geboren
        "15.12.2026",  # Termin
        "nein",   # partner_im_haushalt
        "?",      # mutter.beschaeftigt -> weiß nicht
        "q",      # fertig
    ]
    code, out, _ = lauf(capsys, "interaktiv", "--stichtag", "2026-10-24", "--speichern", str(ziel),
                        eingaben=eingaben, monkeypatch=monkeypatch)
    assert code == 0
    assert "Ist das Kind schon geboren?" in out
    assert "Lebt der andere Elternteil" in out
    assert "BürgerAI – Lebensereignis Geburt" in out
    gespeichert = json.loads(ziel.read_text())
    assert gespeichert["fakten"]["mutter.beschaeftigt"] == "unbekannt"
    assert gespeichert["fakten"]["errechneter_termin"] == "2026-12-15"
    # "weiß nicht" wurde nicht erneut gefragt
    assert out.count("Ist die Mutter (gebärende Person) angestellt") == 1


@pytest.mark.anforderung("ANF-CLI-02", "ANF-GEB-04")
def test_interaktiv_unbekannte_plz(capsys, monkeypatch):
    code, out, _ = lauf(capsys, "interaktiv", eingaben=["10115", "BE", "q"], monkeypatch=monkeypatch)
    assert code == 0
    assert "nicht erfasst" in out and "kein Pilotland" in out


@pytest.mark.anforderung("ANF-CLI-02")
def test_interaktiv_falsche_eingabe_wird_wiederholt(capsys, monkeypatch):
    code, out, _ = lauf(capsys, "interaktiv", "--plz", "80331", eingaben=["vielleicht", "ja", "q"], monkeypatch=monkeypatch)
    assert code == 0 and "bitte 'ja' oder 'nein'" in out


@pytest.mark.anforderung("ANF-CLI-04")
@pytest.mark.parametrize(
    "argv,meldung",
    [
        (["pruefen"], "Bitte --plz"),
        (["pruefen", "--plz", "123"], "Ungültige PLZ"),
        (["pruefen", "--plz", "10115"], "Bundesland"),
        (["pruefen", "--plz", "80331", "-f", "gibtsnicht=1"], "Unbekannter Fakt"),
        (["pruefen", "--plz", "80331", "-f", "zve_eltern=viel"], "Zahl erwartet"),
        (["pruefen", "--plz", "80331", "-f", "mutter.krankenversicherung=gkv"], "erlaubt sind"),
        (["pruefen", "--plz", "80331", "-f", "wohnsitz_land=BY"], "automatisch abgeleitet"),
        (["pruefen", "--plz", "80331", "-f", "ohne_gleich"], "NAME=WERT"),
        (["pruefen", "-s", "gibt_es_nicht"], "nicht gefunden"),
    ],
)
def test_fehlermeldungen(capsys, argv, meldung):
    code, _, err = lauf(capsys, *argv)
    assert code == 2 and meldung in err


def test_hilfsbefehle(capsys):
    for argv in (["gebiet", "80331"], ["leistungen"], ["fakten"], ["quellen", "--offen"], ["daten"],
                 ["szenarien"], ["erklaeren", "elterngeld", "-s", "muenchen_hohes_einkommen"]):
        code, out, _ = lauf(capsys, *argv)
        assert code == 0, argv
        assert out.strip(), argv
    assert lauf(capsys, "szenarien", "--pruefen")[0] == 0
    assert lauf(capsys, "erklaeren", "gibtsnicht", "--plz", "80331")[0] == 1
