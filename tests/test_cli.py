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
        "2",      # Lebenslage Geburt
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
    assert "BürgerAI – Lebenslage Geburt" in out
    gespeichert = json.loads(ziel.read_text())
    assert gespeichert["fakten"]["mutter.beschaeftigt"] == "unbekannt"
    assert gespeichert["fakten"]["errechneter_termin"] == "2026-12-15"
    # "weiß nicht" wurde nicht erneut gefragt
    assert out.count("Ist die Mutter (gebärende Person) angestellt") == 1


@pytest.mark.anforderung("ANF-CLI-02", "ANF-GEB-04")
def test_interaktiv_unbekannte_plz(capsys, monkeypatch):
    # 80001 ist eine Postfach-PLZ in München: keiner Gemeinde zugeordnet
    code, out, _ = lauf(capsys, "interaktiv", eingaben=["1", "80001", "BY", "q"], monkeypatch=monkeypatch)
    assert code == 0
    assert "keiner Gemeinde zugeordnet" in out and "nicht als Gemeinde erfasst" in out


@pytest.mark.anforderung("ANF-CLI-02", "ANF-GEB-03")
def test_interaktiv_mehrdeutige_plz_zeigt_kreis(capsys, monkeypatch):
    code, out, _ = lauf(capsys, "interaktiv", eingaben=["1", "85356", "0", "3", "q"], monkeypatch=monkeypatch)
    assert code == 0
    assert "Oberding" in out and "(Landkreis Erding)" in out
    assert "Bitte eine Zahl von 1 bis 3" in out
    assert "Wohnort: Oberding → Landkreis Erding" in out


@pytest.mark.anforderung("ANF-CLI-02")
def test_interaktiv_falsche_eingabe_wird_wiederholt(capsys, monkeypatch):
    code, out, _ = lauf(capsys, "interaktiv", "--plz", "80331", "-l", "geburt", eingaben=["vielleicht", "ja", "q"], monkeypatch=monkeypatch)
    assert code == 0 and "bitte 'ja' oder 'nein'" in out


@pytest.mark.anforderung("ANF-CLI-04")
@pytest.mark.parametrize(
    "argv,meldung",
    [
        (["pruefen"], "Bitte --plz"),
        (["pruefen", "--plz", "123"], "Ungültige PLZ"),
        (["pruefen", "--plz", "80001"], "Bundesland"),
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
    for argv in (["gebiet", "80331"], ["abdeckung"], ["leistungen"], ["fakten"], ["quellen", "--offen"], ["daten"],
                 ["szenarien"], ["erklaeren", "elterngeld", "-s", "muenchen_hohes_einkommen"]):
        code, out, _ = lauf(capsys, *argv)
        assert code == 0, argv
        assert out.strip(), argv
    assert lauf(capsys, "szenarien", "--pruefen")[0] == 0
    assert lauf(capsys, "erklaeren", "gibtsnicht", "--plz", "80331")[0] == 1


@pytest.mark.anforderung("ANF-MOD-02", "ANF-MOD-09")
def test_lebenslagen_befehl(capsys):
    code, out, _ = lauf(capsys, "lebenslagen")
    assert code == 0 and "Fachmodul Familie und Kinder" in out and "geburt – Geburt (ereignis)" in out
    code, out, _ = lauf(capsys, "lebenslagen", "--suche", "Wir bekommen ein Baby")
    assert code == 0 and out.startswith("geburt")
    code, out, _ = lauf(capsys, "lebenslagen", "--suche", "Steuern auf Kapitalerträge")
    assert code == 1


@pytest.mark.anforderung("ANF-MOD-02")
def test_lebenslage_option(capsys):
    code, out, _ = lauf(capsys, "pruefen", "-s", "nur_plz", "--lebenslage", "geburt")
    assert code == 0 and "BürgerAI – Lebenslage Geburt" in out
    code, _, err = lauf(capsys, "pruefen", "-s", "nur_plz", "-l", "heirat")
    assert code == 2 and "Unbekannte Lebenslage heirat" in err
    code, out, _ = lauf(capsys, "pruefen", "-s", "nur_plz", "--json")
    assert json.loads(out)["anfrage"]["lebenslagen"] == ["geburt"]


@pytest.mark.anforderung("ANF-MOD-01")
def test_fakten_nach_modul(capsys):
    code, out, _ = lauf(capsys, "fakten")
    assert code == 0
    assert out.index("== Kern (alle Fachmodule) ==") < out.index("brutto_haushalt_monat")
    assert out.index("== Fachmodul Familie und Kinder ==") < out.index("eltern_verheiratet")
    assert "Einstiegsfrage Geburt" in out


@pytest.mark.anforderung("ANF-CLI-05")
def test_interaktiv_fragt_lebenslage(capsys, monkeypatch):
    eingaben = ["7", "6", "80331", "15.10.2026", "q"]  # erst ungültig, dann Umzug
    code, out, _ = lauf(capsys, "interaktiv", "--stichtag", "2026-10-24", eingaben=eingaben, monkeypatch=monkeypatch)
    assert code == 0
    assert "Worum geht es?" in out and "Bitte Nummern von 1 bis 6" in out
    assert "Wann ziehen Sie in die neue Wohnung ein" in out
    assert "BürgerAI – Lebenslage Umzug" in out
    code, out, _ = lauf(capsys, "interaktiv", "--plz", "80331", "--stichtag", "2026-10-24",
                        eingaben=["2, 6", "q"], monkeypatch=monkeypatch)
    assert code == 0 and "BürgerAI – Lebenslagen Geburt, Umzug" in out
