"""Router: Lebenslagen aus Freitext (#76). Ohne Netz, mit FakeLLM."""

import json
import logging

import pytest

from buergerai import evaluation
from buergerai.cli import main
from buergerai.llm import FakeLLM, LLMUngueltigeAusgabe
from buergerai.llm import router
from buergerai.llm.router import ABWEISEN, HINWEISE, KATEGORIEN, erkennen, pruefen

TEXT = "Wir bekommen im März ein Kind und ziehen vorher nach Freising."


def _fake(antwort=None, fehler=None):
    eintrag = {"aufgabe": "router"}
    eintrag.update({"fehler": fehler} if fehler else {"antwort": antwort})
    return FakeLLM([eintrag])


def _antwort(kategorie, *ids):
    return {"kategorie": kategorie, "lebenslagen": [{"id": i, "begruendung": f"passt: {i}"} for i in ids]}


# ------------------------------------------------------------------ Prompt und Schema

@pytest.mark.anforderung("ANF-LLM-11")
def test_schema_und_prompt_aus_dem_katalog(kb):
    s = router.schema(kb)
    assert s["properties"]["kategorie"]["enum"] == list(KATEGORIEN)
    assert s["properties"]["lebenslagen"]["items"]["properties"]["id"]["enum"] == sorted(kb.lebenslagen)
    assert s["required"] == ["kategorie", "lebenslagen"] and s["additionalProperties"] is False
    prompt = router.system_prompt(kb)
    assert prompt == router.system_prompt(kb)  # stabil, für Prompt-Caching
    for ll in kb.lebenslagen.values():
        assert f"## {ll.id}: {ll.name}" in prompt
        assert ll.synonyme[0] in prompt and ll.beispiele[0] in prompt
    assert evaluation.KATEGORIEN is KATEGORIEN and evaluation.ABWEISEN is ABWEISEN


@pytest.mark.anforderung("ANF-LLM-11")
def test_prompt_grenzt_mehrdeutige_woerter_ab(kb):
    """Wörter, die zu mehreren Lebenslagen passen, lösen allein keine aus (#110, Test der Oberfläche)."""
    p = router.SYSTEM_ANFANG
    for teil in ['"Kind" allein ist kein Schulstart', "kein geringes Einkommen", "Ein Alter allein ist kein Ruhestand",
                 "Kandidaten der Stichwortsuche sind nur ein Hinweis", "Zukunft und Vergangenheit zählen gleich",
                 "Im Zweifel eine Lebenslage weniger"]:
        assert teil in p, teil
    # Beispiele nennen nur IDs aus dem Katalog
    beispiele = p.split("Beispiele (Text -> Lebenslagen):")[1].split("Katalog der Lebenslagen:")[0]
    ids = {i.strip() for zeile in beispiele.splitlines() if "->" in zeile for i in zeile.split("->")[1].split(",")}
    assert ids and ids <= set(kb.lebenslagen)
    # Kein Beispiel im Prompt ist wörtlich eine Anfrage aus den Judge-Tests (sonst prüft der Test das Beispiel)
    from buergerai import judge

    for t in judge.laden(kb)[0]:
        assert t.anfrage not in p, t.id


@pytest.mark.anforderung("ANF-LLM-11")
def test_eingabe_mit_kandidaten_und_text_getrennt(kb):
    fake = _fake(_antwort("lebenslage", "geburt", "umzug"))
    erkennen(fake, kb, TEXT)
    aufruf = fake.aufrufe[0]
    assert aufruf["aufgabe"] == "router"
    assert TEXT not in aufruf["system"]
    assert aufruf["eingabe"].startswith("Kandidaten der Stichwortsuche: ")
    assert "geburt" in aufruf["eingabe"].split("\n")[0]
    assert f"<<<\n{TEXT}\n>>>" in aufruf["eingabe"]


# ------------------------------------------------------------------ Prüfung

@pytest.mark.anforderung("ANF-LLM-11")
def test_mehrere_lebenslagen_mit_begruendung(kb):
    r = erkennen(_fake(_antwort("lebenslage", "geburt", "umzug", "geburt")), kb, TEXT)
    assert (r.kategorie, r.quelle, r.fehler, r.ids) == ("lebenslage", "llm", None, ["geburt", "umzug"])
    assert r.lebenslagen[0].begruendung == "passt: geburt" and r.hinweis is None


@pytest.mark.anforderung("ANF-LLM-11")
def test_unbekannte_ids_werden_verworfen(kb):
    r = pruefen(kb, {"kategorie": "lebenslage", "lebenslagen": [
        {"id": "lottogewinn", "begruendung": "x"}, {"id": "umzug", "begruendung": "y"}, "geburt", 7]})
    assert r.ids == ["umzug", "geburt"] and r.verworfen == ["lottogewinn", "7"]


@pytest.mark.anforderung("ANF-LLM-11")
@pytest.mark.parametrize("kategorie", sorted(ABWEISEN))
def test_abweisen_ergibt_nie_eine_lebenslage(kb, kategorie):
    r = erkennen(_fake(_antwort(kategorie, "geburt", "geringes_einkommen")), kb, "Wie verheimliche ich mein Baby?")
    assert r.kategorie == kategorie and r.ids == [] and r.quelle == "llm"
    assert r.hinweis == HINWEISE[kategorie]


@pytest.mark.anforderung("ANF-LLM-11")
def test_notlage_behaelt_lebenslagen_und_zeigt_hilfe(kb):
    r = erkennen(_fake(_antwort("notlage", "geringes_einkommen")), kb, "Ich habe seit Tagen nichts gegessen.")
    assert r.ids == ["geringes_einkommen"] and "112" in r.hinweis and "0800 111 0 111" in r.hinweis
    r = erkennen(_fake(_antwort("notlage")), kb, "Ich habe Angst, nach Hause zu gehen.")
    assert r.kategorie == "notlage" and r.ids == [] and r.quelle == "llm"


@pytest.mark.anforderung("ANF-LLM-11")
@pytest.mark.parametrize("ausgabe", [None, [], {}, {"kategorie": "spam", "lebenslagen": []},
                                     {"kategorie": "lebenslage"}, {"kategorie": "lebenslage", "lebenslagen": "geburt"}])
def test_falsche_form_ist_ungueltig(kb, ausgabe):
    with pytest.raises(LLMUngueltigeAusgabe):
        pruefen(kb, ausgabe)


# ------------------------------------------------------------------ Fallback

@pytest.mark.anforderung("ANF-LLM-11", "ANF-LLM-05")
@pytest.mark.parametrize("fehler", ["timeout", "rate_limit", "ablehnung", "ungueltig", "dienst", "konfiguration"])
def test_fallback_bei_llm_fehler(kb, fehler):
    r = erkennen(_fake(fehler=fehler), kb, TEXT)
    assert (r.quelle, r.fehler) == ("fallback", fehler)
    assert r.ids == router.stichwortsuche(kb, TEXT, None).ids and "geburt" in r.ids


@pytest.mark.anforderung("ANF-LLM-11")
def test_fallback_hoechstens_drei_lebenslagen(kb):
    from buergerai.suche import lebenslagen_suchen

    faelle, _ = evaluation.laden(kb)
    # ein Testfall, zu dem die Suche ungekürzt mehr als drei Lebenslagen findet
    text, alle = next((f.text, ids) for f in faelle
                      if len(ids := [ll.id for ll, _ in lebenslagen_suchen(kb, f.text)]) > router.MAX_KANDIDATEN)
    assert router.MAX_KANDIDATEN == 3
    r = erkennen(_fake(fehler="rate_limit"), kb, text)
    assert r.ids == alle[:3]


@pytest.mark.anforderung("ANF-LLM-11")
def test_fallback_ohne_llm_und_bei_leerer_antwort(kb):
    assert erkennen(None, kb, TEXT).fehler == "aus"
    r = erkennen(_fake(_antwort("lebenslage")), kb, TEXT)
    assert (r.quelle, r.fehler) == ("fallback", "leer") and "geburt" in r.ids
    r = erkennen(_fake(_antwort("lebenslage", "erfunden")), kb, "Was ist die Hauptstadt von Australien?")
    assert (r.kategorie, r.quelle, r.ids) == ("kein_thema", "fallback", [])
    assert r.hinweis == HINWEISE["kein_thema"]


@pytest.mark.anforderung("ANF-LLM-11", "ANF-LLM-06")
def test_logs_ohne_text(kb, caplog):
    with caplog.at_level(logging.INFO, logger="buergerai.llm"):
        erkennen(_fake(_antwort("lebenslage", "geburt", "umzug")), kb, "GEHEIM-4711 " + TEXT)
        erkennen(_fake(fehler="timeout"), kb, "GEHEIM-4711 " + TEXT)
    assert "GEHEIM-4711" not in caplog.text and "Freising" not in caplog.text and "passt:" not in caplog.text
    assert "kategorie=lebenslage lebenslagen=geburt,umzug" in caplog.text and "grund=timeout" in caplog.text


# ------------------------------------------------------------------ Evaluation und CLI

def _alle_falsch_fake():
    """Ein Modell, das bösartig jedem Text Lebenslagen unterschiebt, auch bei Abweisung."""
    return FakeLLM([
        {"aufgabe": "router", "enthaelt": "Ignoriere", "antwort": _antwort("kein_thema", "geburt")},
        {"aufgabe": "router", "enthaelt": "Jobcenter", "antwort": _antwort("umgehung", "geringes_einkommen")},
        {"aufgabe": "router", "antwort": _antwort("rechtsberatung", "heirat")},
    ])


@pytest.mark.anforderung("ANF-LLM-12")
def test_eval_verfahren_llm(kb):
    faelle, fehler = evaluation.laden(kb)
    assert not fehler
    ergebnisse = evaluation.bewerten(kb, faelle, evaluation.llm_router(kb, llm=_alle_falsch_fake()))
    assert all(e.vorhersage.lebenslagen == [] for e in ergebnisse)  # Abweisung schlägt jede Lebenslage
    k = evaluation.kennzahlen(ergebnisse)
    assert k["abweisung"]["richtig"] == 1.0 and k["fallback"] == {}
    ergebnisse = evaluation.bewerten(kb, faelle[:4], evaluation.llm_router(kb, llm=_fake(fehler="dienst")))
    assert evaluation.kennzahlen(ergebnisse)["fallback"] == {"dienst": 4}
    assert "Fallback auf die Stichwortsuche: 4 × dienst" in evaluation.als_text(
        evaluation.kennzahlen(ergebnisse), "llm")
    assert evaluation.kennzahlen(evaluation.bewerten(kb, faelle[:4], evaluation.stichwortsuche(kb)))["fallback"] == {}


@pytest.mark.anforderung("ANF-LLM-12")
def test_eval_cli_braucht_llm(capsys, monkeypatch, tmp_path):
    monkeypatch.delenv("BUERGERAI_LLM_ANBIETER", raising=False)
    assert main(["--keine-farbe", "eval", "intake", "--verfahren", "llm"]) == 2
    datei = tmp_path / "fake.json"
    datei.write_text(json.dumps([{"aufgabe": "router", "fehler": "timeout"}]), encoding="utf-8")
    monkeypatch.setenv("BUERGERAI_LLM_ANBIETER", "fake")
    monkeypatch.setenv("BUERGERAI_LLM_FAKE_DATEI", str(datei))
    capsys.readouterr()
    assert main(["--keine-farbe", "eval", "intake", "--verfahren", "llm", "--pause", "0", "--json"]) == 0
    k = json.loads(capsys.readouterr().out)
    assert k["verfahren"] == "llm" and k["fallback"] == {"timeout": k["faelle"]}
    datei = next(evaluation.ERGEBNIS_VERZEICHNIS.glob("*_llm_fake.json"))
    daten = json.loads(datei.read_text(encoding="utf-8"))
    assert daten["modell"] == "fake/fake" and all(f["fallback"] == "timeout" for f in daten["faelle"])


@pytest.mark.anforderung("ANF-LLM-11")
def test_cli_router(capsys, monkeypatch, tmp_path):
    datei = tmp_path / "fake.json"
    datei.write_text(json.dumps([
        {"aufgabe": "router", "enthaelt": "Ei", "antwort": _antwort("kein_thema")},
        {"aufgabe": "router", "antwort": _antwort("lebenslage", "geburt", "umzug")},
        {"aufgabe": "extraktion", "antwort": {"fakten": {"kind_geboren": {"wert": "nein", "beleg": "bekommen"}}}},
    ]), encoding="utf-8")
    monkeypatch.delenv("BUERGERAI_LLM_ANBIETER", raising=False)
    assert main(["--keine-farbe", "llm", "--router", TEXT]) == 1
    monkeypatch.setenv("BUERGERAI_LLM_ANBIETER", "fake")
    monkeypatch.setenv("BUERGERAI_LLM_FAKE_DATEI", str(datei))
    capsys.readouterr()
    assert main(["--keine-farbe", "llm", "--router", TEXT]) == 0
    out = capsys.readouterr().out
    assert "Kategorie: lebenslage" in out and "geburt – Geburt" in out and "umzug – Umzug" in out
    assert main(["--keine-farbe", "llm", "--router", "Wie kocht man ein Ei?", "--json"]) == 0
    daten = json.loads(capsys.readouterr().out.split("\n", 1)[1])
    assert daten["kategorie"] == "kein_thema" and daten["lebenslagen"] == [] and daten["hinweis"]
    # --extrahieren ohne -l nutzt den Router
    assert main(["--keine-farbe", "llm", "--extrahieren", TEXT]) == 0
    out = capsys.readouterr().out
    assert "Lebenslagen aus dem Router: geburt, umzug" in out and "kind_geboren = nein" in out
    assert main(["--keine-farbe", "llm", "--extrahieren", "Wie kocht man ein Ei?"]) == 0
    assert "keine Extraktion" in capsys.readouterr().out
