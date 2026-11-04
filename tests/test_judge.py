"""Judge-Tests für den Router (#83): Laden, deterministische Prüfung, Judge mit FakeLLM, CLI.

Echte Läufe brauchen ein LLM und sind kein Teil von pytest. Hier läuft nur das Gerüst.
"""

import json
import textwrap

import pytest
import yaml

from buergerai import judge
from buergerai.cli import main
from buergerai.llm import FakeLLM
from buergerai.llm.router import Routing, Treffer


def _router(*ids, kategorie="lebenslage"):
    return FakeLLM([{"aufgabe": "router", "antwort": {
        "kategorie": kategorie, "lebenslagen": [{"id": i, "begruendung": f"Text nennt {i}"} for i in ids]}}])


def _urteil(**werte):
    return {k: {"erfuellt": werte.get(k, True), "begruendung": f"{k} geprüft"} for k in judge.KRITERIEN}


class Folge:
    """Gibt nacheinander vorbereitete Judge-Antworten zurück (FakeLLM liefert immer dieselbe)."""

    name = "folge"

    def __init__(self, *antworten):
        self.antworten, self.aufrufe = list(antworten), []

    def strukturiert(self, system, eingabe, schema, *, aufgabe, max_tokens=1024):
        self.aufrufe.append({"system": system, "eingabe": eingabe, "schema": schema, "aufgabe": aufgabe})
        return self.antworten.pop(0)


def _datei(tmp_path, inhalt):
    pfad = tmp_path / "tests.yaml"
    pfad.write_text(textwrap.dedent(inhalt), encoding="utf-8")
    return pfad


# ------------------------------------------------------------------ Laden

@pytest.mark.anforderung("ANF-LLM-23")
def test_mitgelieferte_tests_sind_gueltig(kb):
    tests, fehler = judge.laden(kb)
    assert fehler == []
    ids = {t.id for t in tests}
    assert "beispiel-leer" not in ids  # Vorlage ohne Anfrage wird übersprungen
    assert {"geburt-umzug-01", "jobverlust-experte-01", "geburt-kind-mai"} <= ids
    mai = next(t for t in tests if t.id == "geburt-kind-mai")
    assert (mai.lebenslagen, mai.nicht_lebenslagen) == (["geburt"], ["schule", "geringes_einkommen"])
    assert mai.stichtag == "2026-11-03" and mai.experte
    assert len([t for t in tests if t.datei == "router.yaml"]) >= 20


@pytest.mark.anforderung("ANF-LLM-23")
def test_jedes_szenario_hat_einen_judge_test(kb):
    """szenarien.yaml passt zu szenarien/*.json: ein Test je Szenario, dieselben Lebenslagen."""
    from buergerai.szenarien import SZENARIO_VERZEICHNIS

    tests = {t.id: t for t in judge.laden(kb, [judge.JUDGE_VERZEICHNIS / "szenarien.yaml"])[0]}
    dateien = sorted(SZENARIO_VERZEICHNIS.glob("*.json"))
    assert len(tests) == len(dateien) > 60
    for pfad in dateien:
        roh = json.loads(pfad.read_text(encoding="utf-8"))
        t = tests.get("szenario-" + pfad.stem.replace("_", "-"))
        assert t, f"{pfad.name}: kein Test in szenarien.yaml"
        lagen = roh.get("lebenslagen") or ["geburt"]
        assert t.stichtag == roh["stichtag"] and t.kategorie == "lebenslage", t.id
        if t.lebenslagen is None:  # zweite Lage vertretbar: dann entscheidet die Fachperson
            assert t.experte and not set(lagen) & set(t.nicht_lebenslagen), t.id
        else:
            assert sorted(t.lebenslagen) == sorted(lagen), t.id
        assert set(t.leistungen) == {k for k, v in roh["erwartet"].items() if v == "ja"}, t.id


@pytest.mark.anforderung("ANF-LLM-23")
def test_fehler_in_den_tests_werden_gemeldet(kb, tmp_path):
    pfad = _datei(tmp_path, """
        tests:
          - id: Gross_Schreibung
            anfrage: "Text"
            erwartet: {lebenslagen: [erfunden], kategorie: vielleicht}
          - id: doppelt
            anfrage: "Text"
            erwartet: {lebenslagen: [geburt], nicht_erwartet: {lebenslagen: [geburt], leistungen: [gibt_es_nicht]}}
          - id: doppelt
            anfrage: "Text"
          - id: leer
            anfrage: ""
        """)
    tests, fehler = judge.laden(kb, [pfad])
    text = "\n".join(fehler)
    for teil in ["id nur aus a-z", "Lebenslage 'erfunden' unbekannt", "Kategorie 'vielleicht' unbekannt",
                 "geburt steht in lebenslagen und nicht_erwartet", "Leistung 'gibt_es_nicht' unbekannt",
                 "doppelt: keine Erwartung", "id doppelt mehrfach vergeben"]:
        assert teil in text, teil
    assert "leer" not in {t.id for t in tests}
    assert judge.laden(kb, [_datei(tmp_path, "nur: text")])[1] == ["tests.yaml: Liste 'tests' fehlt"]
    assert "kein gültiges YAML" in judge.laden(kb, [_datei(tmp_path, "tests: [unvollständig")])[1][0]


# ------------------------------------------------------------------ Deterministisch

@pytest.mark.anforderung("ANF-LLM-23")
def test_lebenslagen_genau_und_ausgeschlossene(kb):
    t = judge.JudgeTest(id="t", anfrage="Wir bekommen im Mai ein Kind", datei="x", kategorie="lebenslage",
                        lebenslagen=["geburt"], nicht_lebenslagen=["schule", "geringes_einkommen"])
    ok = judge.ausfuehren(kb, [t], _router("geburt"))[0]
    assert ok.bestanden and [b.kriterium for b in ok.befunde] == ["kategorie", "lebenslagen", "nicht_erwartet"]
    falsch = judge.ausfuehren(kb, [t], _router("geburt", "schule", "geringes_einkommen"))[0]
    assert not falsch.bestanden
    befund = {b.kriterium: b for b in falsch.befunde}
    assert "zusätzlich: geringes_einkommen, schule" in befund["lebenslagen"].text
    assert not befund["nicht_erwartet"].bestanden and befund["kategorie"].bestanden
    fehlt = judge.ausfuehren(kb, [t], _router("umzug"))[0]
    assert "fehlt: geburt" in {b.kriterium: b for b in fehlt.befunde}["lebenslagen"].text


@pytest.mark.anforderung("ANF-LLM-23")
def test_nur_angegebene_erwartungen_werden_geprueft(kb):
    # lebenslagen fehlt -> nicht geprüft; [] -> keine erwartet
    nur_nicht = judge.JudgeTest(id="a", anfrage="x", datei="x", nicht_lebenslagen=["heirat"])
    assert [b.kriterium for b in judge.deterministisch(nur_nicht, Routing("lebenslage", [Treffer("umzug")]))] \
        == ["nicht_erwartet"]
    keine = judge.JudgeTest(id="b", anfrage="x", datei="x", kategorie="kein_thema", lebenslagen=[])
    assert all(b.bestanden for b in judge.deterministisch(keine, Routing("kein_thema")))


@pytest.mark.anforderung("ANF-LLM-23")
def test_ohne_llm_wird_die_stichwortsuche_geprueft(kb):
    t = judge.JudgeTest(id="t", anfrage="Wir bekommen im Mai ein Kind", datei="x", lebenslagen=["geburt"])
    e = judge.ausfuehren(kb, [t], None)[0]
    assert (e.routing.quelle, e.routing.ids, e.bestanden) == ("fallback", ["geburt"], True)


# ------------------------------------------------------------------ Judge

@pytest.mark.anforderung("ANF-LLM-23")
def test_judge_bekommt_text_auswahl_und_erwartung(kb):
    t = judge.JudgeTest(id="t", anfrage="Ich bin 63 und mir wurde gekündigt.", datei="x",
                        experte="Jobverlust, nicht Ruhestand.")
    j = Folge(_urteil())
    e = judge.ausfuehren(kb, [t], _router("jobverlust"), j)[0]
    assert e.judge_gelaufen and e.judge_bestanden and e.bestanden
    aufruf = j.aufrufe[0]
    assert aufruf["aufgabe"] == "judge" and aufruf["schema"] == judge.judge_schema()
    assert "<<<\nIch bin 63 und mir wurde gekündigt.\n>>>" in aufruf["eingabe"]
    assert "<<<\nJobverlust, nicht Ruhestand.\n>>>" in aufruf["eingabe"]
    assert "- jobverlust (Job verloren oder gekündigt): Text nennt jobverlust" in aufruf["eingabe"]
    assert t.anfrage not in aufruf["system"]  # Prompt stabil, Text nur in der Eingabe
    for k in judge.KRITERIEN:
        assert k in aufruf["system"]
    assert judge.judge_schema()["required"] == list(judge.KRITERIEN)


@pytest.mark.anforderung("ANF-LLM-23")
def test_judge_nur_bei_experte_und_nur_einstimmig(kb):
    ohne = judge.JudgeTest(id="a", anfrage="Wir heiraten.", datei="x", lebenslagen=["heirat"])
    mit = judge.JudgeTest(id="b", anfrage="Wir heiraten.", datei="x", experte="Heirat.")
    j = Folge(_urteil(), _urteil(nichts_zu_viel=False), _urteil())
    a, b = judge.ausfuehren(kb, [ohne, mit], _router("heirat"), j, wiederholungen=3)
    assert not a.judge_gelaufen and a.bestanden
    assert len(j.aufrufe) == 3  # nur der Test mit experte, dreimal
    urteil = {u.kriterium: u for u in b.urteile}
    assert urteil["nichts_zu_viel"].stimmen == [True, False, True] and not urteil["nichts_zu_viel"].einig
    assert not b.judge_bestanden and not b.bestanden and b.deterministisch_bestanden
    z = judge.zusammenfassung([a, b])
    assert z["judge"] == {"bewertet": 1, "bestanden": 0, "uneinig": 1, "fehler": 0}
    assert z["fehlgeschlagen"] == ["b"]


@pytest.mark.anforderung("ANF-LLM-23")
def test_judge_fehler_zaehlt_als_nicht_bestanden(kb):
    t = judge.JudgeTest(id="t", anfrage="Wir heiraten.", datei="x", experte="Heirat.")
    kaputt = Folge({"kategorie": {"erfuellt": "ja"}})
    e = judge.ausfuehren(kb, [t], _router("heirat"), kaputt)[0]
    assert (e.judge_fehler, e.judge_bestanden, e.bestanden) == ("ungueltig", False, False)
    weg = FakeLLM([{"aufgabe": "judge", "fehler": "timeout"}])
    assert judge.ausfuehren(kb, [t], _router("heirat"), weg)[0].judge_fehler == "timeout"


@pytest.mark.anforderung("ANF-LLM-23")
def test_judge_umgebung_eigenes_modell():
    env = {"BUERGERAI_LLM_ANBIETER": "gemini", "BUERGERAI_LLM_MODELL": "klein", "GEMINI_API_KEY": "k"}
    assert judge.judge_umgebung(env) is None
    j = judge.judge_umgebung({**env, "BUERGERAI_JUDGE_ANBIETER": "mistral", "BUERGERAI_JUDGE_MODELL": "gross"})
    assert (j["BUERGERAI_LLM_ANBIETER"], j["BUERGERAI_LLM_MODELL"], j["GEMINI_API_KEY"]) == ("mistral", "gross", "k")


# ------------------------------------------------------------------ Ergebnisdatei

@pytest.mark.anforderung("ANF-LLM-23")
def test_ergebnisdatei_yaml(kb, tmp_path, monkeypatch):
    from datetime import datetime, timezone

    t = judge.JudgeTest(id="mai", anfrage="Wir bekommen im Mai ein Kind", datei="router.yaml", lebenslagen=["geburt"])
    ergebnisse = judge.ausfuehren(kb, [t], None)
    zeit = datetime(2026, 11, 4, 19, 30, 5, tzinfo=timezone.utc)
    daten = judge.ergebnis_daten(ergebnisse, None, zeitpunkt=zeit)
    assert judge.dateiname(daten) == "2026-11-04_193005_stichwortsuche.yaml"
    assert judge.dateiname({**daten, "router": "gemini/gemini-2.5-flash-lite", "judge": "mistral/mistral-large"}) \
        == "2026-11-04_193005_gemini-2.5-flash-lite_judge-mistral-large.yaml"
    monkeypatch.setattr(judge, "ERGEBNIS_VERZEICHNIS", tmp_path / "judge")
    pfad = judge.ergebnis_speichern(daten)
    assert pfad == tmp_path / "judge" / "2026-11-04_193005_stichwortsuche.yaml"
    text = pfad.read_text(encoding="utf-8")
    assert text.startswith("# Ergebnis von ./bai eval judge")
    geladen = yaml.safe_load(text)
    assert geladen["zusammenfassung"]["bestanden"] == 1 and geladen["router"] == "stichwortsuche"
    assert geladen["tests"][0]["befunde"][0] == {"kriterium": "lebenslagen", "bestanden": True,
                                                 "text": "erwartet geburt, erkannt geburt"}


# ------------------------------------------------------------------ CLI

@pytest.fixture
def ohne_llm(monkeypatch, tmp_path):
    leer = tmp_path / "leer.env"
    leer.write_text("", encoding="utf-8")
    monkeypatch.setenv("BUERGERAI_ENV_DATEI", str(leer))
    for k in ("BUERGERAI_LLM_ANBIETER", "BUERGERAI_JUDGE_ANBIETER"):
        monkeypatch.delenv(k, raising=False)


@pytest.mark.anforderung("ANF-LLM-23")
def test_cli_exit_codes(ohne_llm, tmp_path, capsys):
    gut = _datei(tmp_path, """
        tests:
          - id: mai
            anfrage: "Wir bekommen im Mai ein Kind"
            erwartet: {lebenslagen: [geburt], nicht_erwartet: {lebenslagen: [schule]}}
        """)
    assert main(["--keine-farbe", "eval", "judge", "--datei", str(gut), "--keine-datei"]) == 0
    out = capsys.readouterr().out
    assert "OK     mai" in out and "1 von 1 Tests bestanden" in out
    schlecht = tmp_path / "schlecht.yaml"
    schlecht.write_text('tests:\n  - id: wetter\n    anfrage: "Wie wird das Wetter?"\n'
                        '    erwartet: {lebenslagen: [geburt]}\n', encoding="utf-8")
    assert main(["--keine-farbe", "eval", "judge", "--datei", str(schlecht), "--keine-datei"]) == 1
    assert "FEHLER wetter" in capsys.readouterr().out
    assert main(["--keine-farbe", "eval", "judge", "--datei", str(gut), "--nur", "gibtsnicht", "--keine-datei"]) == 2
    assert main(["--keine-farbe", "eval", "judge", "--datei", str(gut), "--judge", "--keine-datei"]) == 2
    assert "BUERGERAI_JUDGE_ANBIETER" in capsys.readouterr().out
    assert main(["--keine-farbe", "eval", "judge", "--datei", str(gut), "--json", "--keine-datei"]) == 0
    daten = json.loads(capsys.readouterr().out)
    assert daten["zusammenfassung"]["bestanden"] == 1 and daten["tests"][0]["erkannt"]["lebenslagen"] == ["geburt"]


@pytest.mark.anforderung("ANF-LLM-23")
def test_cli_mit_fake_router_und_judge(ohne_llm, tmp_path, monkeypatch, capsys):
    antworten = tmp_path / "antworten.json"
    antworten.write_text(json.dumps([
        {"aufgabe": "router", "antwort": {"kategorie": "lebenslage",
                                         "lebenslagen": [{"id": "geburt", "begruendung": "Kind im Mai"}]}},
        {"aufgabe": "judge", "antwort": _urteil(nichts_fehlt=False)},
    ]), encoding="utf-8")
    for k, v in {"BUERGERAI_LLM_ANBIETER": "fake", "BUERGERAI_LLM_FAKE_DATEI": str(antworten),
                 "BUERGERAI_JUDGE_ANBIETER": "fake", "BUERGERAI_JUDGE_FAKE_DATEI": str(antworten)}.items():
        monkeypatch.setenv(k, v)
    pfad = _datei(tmp_path, """
        tests:
          - id: mai
            anfrage: "Wir bekommen im Mai ein Kind"
            erwartet: {lebenslagen: [geburt]}
            experte: "Nur Geburt."
        """)
    ziel = tmp_path / "ergebnis.yaml"
    assert main(["--keine-farbe", "eval", "judge", "--datei", str(pfad), "--judge", "--pause", "0",
                 "--ausgabe", str(ziel)]) == 1
    out = capsys.readouterr().out
    assert f"Ergebnisse gespeichert: {ziel}" in out
    daten = yaml.safe_load(ziel.read_text(encoding="utf-8"))
    assert (daten["router"], daten["judge"], daten["wiederholungen"]) == ("fake/fake", "fake/fake", 1)
    test = daten["tests"][0]
    assert test["erkannt"] == {"kategorie": "lebenslage", "lebenslagen": ["geburt"], "quelle": "llm",
                               "fallback_grund": None}
    assert test["judge"]["kriterien"][2] == {"kriterium": "nichts_fehlt", "stimmen": [False],
                                             "begruendungen": ["nichts_fehlt geprüft"]}
    assert "Wir bekommen" not in ziel.read_text(encoding="utf-8")  # Anfrage steht nur in der Testdatei
    assert "FEHLER mai  → lebenslage: geburt" in out and "(Stichwortsuche)" not in out
    assert "✗ judge nichts_fehlt [n]: nichts_fehlt geprüft" in out
    assert "Judge: 1 bewertet, 0 bestanden" in out
