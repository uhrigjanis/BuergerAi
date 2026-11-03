"""Freitext in der Web-Oberfläche (#79) und neue Felder für die Checkliste (#86). Ohne Netz, mit FakeLLM."""

import json
import re
import threading
from pathlib import Path

import pytest

from buergerai.llm import FakeLLM
from buergerai.web import api
from buergerai.web.server import MODULE, erstellen
from buergerai.wissensbasis import Wissensbasis

from test_web import STICHTAG, alles_js, anfrage, http

STATIC = Path(__file__).resolve().parents[1] / "src" / "buergerai" / "web" / "static"
TEXT = "Wir bekommen im März ein Baby, mein Mann und ich ziehen nach Freising. Ich bin 34."


def fake_llm(**weitere):
    return FakeLLM([
        {"aufgabe": "router", "antwort": {"kategorie": "lebenslage", "lebenslagen": [
            {"id": "geburt", "begruendung": "Baby"}, {"id": "umzug", "begruendung": "Umzug"}]}},
        {"aufgabe": "extraktion", "enthaelt": "(geburt)", "antwort": {"fakten": {
            "kind_geboren": {"wert": "nein", "beleg": "wir bekommen im märz ein Baby"},
            "partner_im_haushalt": {"wert": "ja", "beleg": "mein Mann und ich"},
            # Beleg steht nicht im Text: wird verworfen und nie vorgeschlagen
            "mutter.beschaeftigt": {"wert": "ja", "beleg": "ich arbeite Vollzeit"},
        }}},
        {"aufgabe": "extraktion", "enthaelt": "(umzug)", "antwort": {"fakten": {}}},
        {"aufgabe": "extraktion", "enthaelt": "Gestellte Frage", "antwort": {"fakten": {
            "errechneter_termin": {"wert": "2027-03-14", "beleg": "am 14. März"}}}},
        *weitere.get("extra", []),
    ])


# ------------------------------------------------------------------ /api/intake
@pytest.mark.anforderung("ANF-LLM-16")
def test_intake_liefert_vorschlaege_mit_beleg_und_stelle(kb):
    r = api.intake(kb, fake_llm(), {"text": TEXT, "stichtag": STICHTAG})
    assert r["kategorie"] == "lebenslage" and r["quelle"] == "llm"
    assert [l["id"] for l in r["lebenslagen"]] == ["geburt", "umzug"]
    vs = {v["id"]: v for v in r["vorschlaege"]}
    assert set(vs) == {"kind_geboren", "partner_im_haushalt"}
    kg = vs["kind_geboren"]
    assert kg["wert"] is False and kg["anzeige"] == "nein" and kg["typ"] == "ja_nein"
    von, bis = kg["stelle"]
    assert TEXT[von:bis] == "Wir bekommen im März ein Baby"
    # kein Bericht, keine Berechnung
    assert not {"leistungen", "fragen", "angaben"} & set(r)


@pytest.mark.anforderung("ANF-LLM-16")
@pytest.mark.parametrize("beleg, erwartet", [
    ("ziehen nach Freising.", "ziehen nach Freising"),
    ("MEIN  mann und ich", "mein Mann und ich"),
    ("„Baby“", "Baby"),
    ("gibt es nicht", None),
])
def test_beleg_stelle(beleg, erwartet):
    stelle = api.beleg_stelle(TEXT, beleg)
    assert (TEXT[stelle[0]:stelle[1]] if stelle else None) == erwartet


@pytest.mark.anforderung("ANF-LLM-17")
def test_intake_bei_llm_fehler_mit_hinweis_statt_fehler(kb):
    fake = FakeLLM([
        {"aufgabe": "router", "antwort": {"kategorie": "lebenslage", "lebenslagen": [{"id": "geburt", "begruendung": "x"}]}},
        {"aufgabe": "extraktion", "fehler": "timeout"},
    ])
    r = api.intake(kb, fake, {"text": TEXT})
    assert [l["id"] for l in r["lebenslagen"]] == ["geburt"]
    assert r["vorschlaege"] == [] and api.HINWEIS_OHNE_ANGABEN in r["hinweise"]
    # Router fällt aus: Stichwortsuche, keine Extraktion
    r = api.intake(kb, FakeLLM([{"aufgabe": "router", "fehler": "dienst"}]), {"text": "Wir bekommen ein Baby"})
    assert r["quelle"] == "fallback" and "geburt" in [l["id"] for l in r["lebenslagen"]] and r["vorschlaege"] == []


@pytest.mark.anforderung("ANF-LLM-16")
def test_intake_abweisung_ohne_lebenslagen_und_ohne_extraktion(kb):
    fake = FakeLLM([{"aufgabe": "router", "antwort": {"kategorie": "kein_thema", "lebenslagen": [{"id": "geburt", "begruendung": "x"}]}}])
    r = api.intake(kb, fake, {"text": "Schreib mir ein Gedicht"})
    assert r["lebenslagen"] == [] and r["vorschlaege"] == [] and r["hinweise"]
    assert [a["aufgabe"] for a in fake.aufrufe] == ["router"]


@pytest.mark.anforderung("ANF-LLM-16", "ANF-WEB-07")
@pytest.mark.parametrize("daten", [{}, {"text": ""}, {"text": 5}, {"text": "x" * (api.MAX_FREITEXT + 1)}, []])
def test_intake_ungueltig(kb, daten):
    with pytest.raises(api.ApiFehler) as info:
        api.intake(kb, fake_llm(), daten)
    assert info.value.status == 400


# ------------------------------------------------------------------ /api/antwort
@pytest.mark.anforderung("ANF-LLM-16")
def test_antwort_auf_offene_frage(kb):
    daten = {**anfrage(kind_geboren=False), "frage": "errechneter_termin", "text": "Der Termin ist am 14. März."}
    fake = fake_llm()
    r = api.antwort(kb, fake, daten)
    assert [(v["id"], v["wert"]) for v in r["vorschlaege"]] == [("errechneter_termin", "2027-03-14")]
    assert r["hinweise"] == []
    eingabe = fake.aufrufe[0]["eingabe"]
    assert "Gestellte Frage" in eingabe and "Heute: Samstag, 2026-10-24" in eingabe
    # Nicht mehr offen: abgelehnt
    with pytest.raises(api.ApiFehler):
        api.antwort(kb, fake, {**daten, "frage": "kind_geboren"})


@pytest.mark.anforderung("ANF-LLM-17")
def test_antwort_ohne_ergebnis_mit_hinweis(kb):
    fake = FakeLLM([{"aufgabe": "extraktion", "fehler": "ungueltig"}])
    r = api.antwort(kb, fake, {**anfrage(kind_geboren=False), "frage": "errechneter_termin", "text": "bald"})
    assert r == {"vorschlaege": [], "hinweise": [api.HINWEIS_ANTWORT_LEER]}


# ------------------------------------------------------------------ Server
@pytest.fixture()
def server_mit():
    gestartet = []

    def starten(llm):
        server = erstellen(Wissensbasis.laden(), "127.0.0.1", 0, llm)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        gestartet.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}"

    yield starten
    for s in gestartet:
        s.shutdown()
        s.server_close()


@pytest.mark.anforderung("ANF-LLM-17", "ANF-WEB-11")
def test_ohne_llm_nur_suche_und_formular(server_mit):
    basis = server_mit(None)
    meta = json.loads(http(basis + "/api/meta")[2])
    assert meta["freitext"] is False
    assert http(basis + "/api/intake", {"text": TEXT})[0] == 404
    assert http(basis + "/api/antwort", {"text": "ja"})[0] == 404
    status, _, inhalt = http(basis + "/api/suche", {"text": "Wir bekommen ein Baby"})
    assert status == 200 and json.loads(inhalt)["lebenslagen"][0] == "geburt"


@pytest.mark.anforderung("ANF-LLM-16", "ANF-LLM-18")
def test_ende_zu_ende_freitext_bestaetigung_bericht(server_mit):
    """Freitext -> Vorschläge -> (Nutzer korrigiert und bestätigt) -> Bericht über HTTP."""
    basis = server_mit(fake_llm())
    assert json.loads(http(basis + "/api/meta")[2])["freitext"] is True
    status, _, inhalt = http(basis + "/api/intake", {"text": TEXT, "stichtag": STICHTAG})
    assert status == 200
    intake = json.loads(inhalt)
    # Bestätigung: der Nutzer übernimmt "kind_geboren", nimmt den Partner-Vorschlag heraus
    bestaetigt = {v["id"]: v["wert"] for v in intake["vorschlaege"] if v["id"] != "partner_im_haushalt"}
    lagen = [l["id"] for l in intake["lebenslagen"]]
    status, _, inhalt = http(basis + "/api/bericht", {"plz": "85354", "stichtag": STICHTAG, "fakten": bestaetigt, "lebenslagen": lagen})
    assert status == 200
    bericht = json.loads(inhalt)
    assert {a["id"]: a["wert"] for a in bericht["angaben"]} == {"kind_geboren": False}
    assert "partner_im_haushalt" in [f["id"] for f in bericht["fragen"]]
    # Freie Antwort auf die nächste offene Frage, wieder erst nach Bestätigung im Bericht
    status, _, inhalt = http(basis + "/api/antwort", {"plz": "85354", "stichtag": STICHTAG, "fakten": bestaetigt,
                                                      "lebenslagen": lagen, "frage": "errechneter_termin",
                                                      "text": "Termin ist am 14. März"})
    assert status == 200 and json.loads(inhalt)["vorschlaege"][0]["id"] == "errechneter_termin"


@pytest.mark.anforderung("ANF-LLM-18")
def test_oberflaeche_uebernimmt_vorschlaege_nur_nach_bestaetigung():
    """Statisch: Vorschläge gehen nur über werte() der Bestätigungsliste in zustand.fakten."""
    start = (STATIC / "start.js").read_text(encoding="utf-8")
    frage = (STATIC / "frage.js").read_text(encoding="utf-8")
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    # Einstieg: Fakten = angehakte Werte, erst beim Absenden mit "Stimmt so"
    assert "bestaetigt = bestaetigung ? bestaetigung.werte() : {}" in start
    assert "fakten: bestaetigt" in start
    assert re.search(r"Stimmt so – Checkliste erstellen", start)
    # Freie Antwort: nur über "Übernehmen"
    assert "uebernehmen(liste.werte())" in frage
    for js in (start, frage):
        assert not re.search(r"zustand\.fakten\s*=\s*.*vorschl", js)
    # Einwilligung und Hinweis vor dem Absenden
    assert 'id="einwilligung-ja"' in html and "KI-Dienst" in html
    assert "einwilligung-ja\").checked" in start
    # Freitext wird nicht im Browser gespeichert
    gemeinsam = (STATIC / "gemeinsam.js").read_text(encoding="utf-8")
    gespeichert = re.search(r"const \{ ([^}]+) \} = zustand;", gemeinsam).group(1)
    assert "text" not in gespeichert and "vorschlaege" not in gespeichert


# ------------------------------------------------------------------ Checkliste (#86)
@pytest.mark.anforderung("ANF-WEB-12")
def test_fragen_nennen_betroffene_leistungen(kb):
    b = api.bericht(kb, anfrage(kind_geboren=False))
    termin = next(f for f in b["fragen"] if f["id"] == "errechneter_termin")
    assert termin["betrifft"] and {x["art"] for x in termin["betrifft"]} == {"frist"}
    assert "Kindergeld" in [x["name"] for x in termin["betrifft"]]
    b = api.bericht(kb, anfrage(kind_geboren=False, errechneter_termin="2026-12-15", partner_im_haushalt=True))
    anspruch = [f for f in b["fragen"] if any(x["art"] == "anspruch" for x in f["betrifft"])]
    assert anspruch
    for f in anspruch:
        for x in f["betrifft"]:
            if x["art"] == "anspruch":
                l = next(l for l in b["leistungen"] if l["id"] == x["id"])
                assert l["offene_fragen"] > 0


@pytest.mark.anforderung("ANF-WEB-13")
def test_zeitgruppen_und_klaeren_mit(kb):
    b = api.bericht(kb, anfrage(kind_geboren=True, geburtsdatum="2026-10-20", partner_im_haushalt=True))
    gruppen = [g["id"] for g in b["zeitgruppen"]]
    assert gruppen[0] == "abgelaufen" and gruppen[-1] == "ohne_frist"
    offen = {f["id"] for f in b["fragen"]}
    for l in b["leistungen"]:
        assert l["zeitgruppe"] in gruppen
        if l["leitfrist"] is not None:
            assert l["zeitgruppe"] == l["fristen"][l["leitfrist"]]["gruppe"]
        if l["klaeren_mit"]:
            assert l["klaeren_mit"] in offen
    def anzeige(bericht):
        return next(l for l in bericht["leistungen"] if l["name"].startswith("Geburt anzeigen"))

    assert anzeige(b)["zeitgruppe"] == "diese_woche"  # eine Woche nach dem 20.10.: 27.10., Stichtag 24.10.
    frueher = api.bericht(kb, anfrage(kind_geboren=True, geburtsdatum="2026-10-10", partner_im_haushalt=True))
    assert anzeige(frueher)["zeitgruppe"] == "abgelaufen"
    unklar = [l for l in b["leistungen"] if l["ergebnis"] == "unklar" and l["offene_fragen"]]
    assert unklar and all(l["klaeren_mit"] for l in unklar)


@pytest.mark.anforderung("ANF-WEB-11")
def test_einstieg_suche_kacheln_und_dev_modus():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    start = (STATIC / "start.js").read_text(encoding="utf-8")
    assert "Was ist bei Ihnen los?" in html
    assert '/api/suche' in start and 'aria-pressed' in start and "BEREICHE" in start
    assert 'id="beispiele" class="beispiele" hidden' in html and 'has("dev")' in start


@pytest.mark.anforderung("ANF-WEB-13")
def test_checkliste_ansichten_und_druck():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    js = (STATIC / "checkliste.js").read_text(encoding="utf-8")
    for ansicht in ("zeit", "stelle", "ergebnis"):
        assert f'data-ansicht="{ansicht}"' in html
    assert "Jetzt klären" in js and "klaeren_mit" in js and "datenstand(l)" in js
    assert "Behördenmappe" in js and 'id="druck"' in html
    assert '<dialog id="detail"' in html


@pytest.mark.anforderung("ANF-WEB-14")
def test_module_eine_spalte_und_ergebnis_nicht_nur_farbe():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert '<script type="module" src="app.js' in html
    for m in MODULE:
        assert (STATIC / f"{m}.js").exists()
    # Eine Spalte ohne Reiter; Angaben, Lebenslagen, Datum und Dateien in einer Schublade (#99)
    assert 'class="reiter"' not in html and "data-reiter" not in html
    schublade = html[html.index('<dialog id="schublade"'):html.index("</dialog>", html.index('<dialog id="schublade"'))]
    for teil in ('id="angaben"', 'id="lebenslagen-wahl-arbeit"', 'id="stichtag"', 'id="speichern"', 'id="datei-laden"', 'id="neu"'):
        assert teil in schublade, teil
    gemeinsam = (STATIC / "gemeinsam.js").read_text(encoding="utf-8")
    # Ergebnis immer als Wort (Ja/Unklar/Nein), ohne Symbole
    assert "ERGEBNIS_TEXT[wert]" in gemeinsam and "SYMBOL" not in alles_js()
    assert "✓" not in alles_js().replace("☐", "") and "✗" not in alles_js()
    # "Weiß nicht" bei jeder Frage
    assert '"Weiß nicht")' in (STATIC / "frage.js").read_text(encoding="utf-8")
