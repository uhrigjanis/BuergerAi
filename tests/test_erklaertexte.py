"""Erklärtexte je Leistung und Glossar (#113)."""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from buergerai import erklaertexte as et
from buergerai import quellenpruefung as qp
from buergerai.cli import main
from buergerai.llm.formulierung import modell_daten, vorlage
from buergerai.modell import Pruefstatus
from buergerai import szenarien
from buergerai.planer import planen
from buergerai.web import api
from buergerai.wissensbasis import STANDARD_DATENVERZEICHNIS, DatenFehler, Wissensbasis

STATIC = Path(__file__).resolve().parents[1] / "src" / "buergerai" / "web" / "static"


@pytest.fixture
def daten(tmp_path):
    """Kopie der Wissensbasis, die ein Test verändern darf."""
    ziel = tmp_path / "data"
    shutil.copytree(STANDARD_DATENVERZEICHNIS, ziel)
    return ziel


def _aendern(datei: Path, aendern) -> None:
    inhalt = json.loads(datei.read_text(encoding="utf-8"))
    aendern(inhalt)
    datei.write_text(et.formatiert(inhalt), encoding="utf-8")


def _fehler(daten: Path) -> list[str]:
    with pytest.raises(DatenFehler) as info:
        Wissensbasis.laden(daten)
    return info.value.fehler


# ------------------------------------------------------------------ Abdeckung und Ablage
@pytest.mark.anforderung("ANF-DAT-15")
def test_jede_leistung_hat_einen_erklaertext(kb):
    assert et.ohne_erklaerung(kb) == []
    assert len(kb.erklaerungen) == len(kb.leistungen)


@pytest.mark.anforderung("ANF-DAT-15")
def test_erklaertext_liegt_in_einem_modul_der_leistung(kb):
    for e in kb.erklaerungen.values():
        assert e.modul in kb.module_von_leistung(kb.leistungen[e.leistung_id]), e.leistung_id


@pytest.mark.anforderung("ANF-DAT-15")
def test_falsche_ablage_und_unbekannte_leistung(daten):
    _aendern(daten / "fachmodule/umzug/erklaerungen.json",
             lambda i: i["erklaerungen"].append({**i["erklaerungen"][0], "leistung_id": "elterngeld"}))
    _aendern(daten / "fachmodule/arbeit/erklaerungen.json",
             lambda i: i["erklaerungen"].append({**i["erklaerungen"][0], "leistung_id": "gibt_es_nicht"}))
    fehler = _fehler(daten)
    assert any("doppelter Erklärtext für elterngeld" in f for f in fehler)
    assert any(f.startswith("Erklärtext gibt_es_nicht: unbekannte Leistung") for f in fehler)
    assert any("Erklärtext elterngeld: gehört in ein Modul der Leistung (familie), nicht nach umzug" in f for f in fehler)


@pytest.mark.anforderung("ANF-DAT-15")
def test_glossar_nur_im_kern_erklaerungen_nur_in_modulen(daten):
    (daten / "kern/erklaerungen.json").write_text(
        et.formatiert({"erklaerungen": [{"leistung_id": "x", "was": "y"}]}), encoding="utf-8")
    (daten / "fachmodule/arbeit/glossar.json").write_text(
        et.formatiert({"glossar": [{"id": "x", "begriff": "X", "erklaerung": "y"}]}), encoding="utf-8")
    fehler = _fehler(daten)
    assert any("'erklaerungen' gehört nach data/fachmodule/<id>/" in f for f in fehler)
    assert any("'glossar' gehört nach data/kern/" in f for f in fehler)


# ------------------------------------------------------------------ Textregeln
@pytest.mark.anforderung("ANF-DAT-16")
@pytest.mark.parametrize("text, code", [
    ("Das Elterngeld wird höchstens 14 Monate gezahlt und ist eine wichtige Leistung.", "zahl"),
    ("Die Klage muss innerhalb von drei Wochen beim Arbeitsgericht eingehen, sonst gilt sie.", "menge"),
    ("Gezahlt wird bis zum dritten Lebensjahr des Kindes, unabhängig vom Einkommen der Eltern.", "menge"),
    ("Der Zuschuss beträgt einen festen Anteil in Euro und wird jedes Jahr neu festgelegt.", "betrag"),
    ("Die Rechtsgrundlage steht in § 1 BEEG und regelt, wer das Elterngeld beziehen kann.", "paragraph"),
    ("Weitere Informationen gibt es auf familienportal.de und bei der Elterngeldstelle vor Ort.", "link"),
    ("Mit diesem Antrag bekommen Familien ganz sicher Geld, wenn sie alle Unterlagen einreichen.", "zusage"),
    ("Sie bekommen das Kindergeld, sobald die Familienkasse den Antrag bearbeitet hat und alles passt.", "zusage"),
    ("Auch Menschen ohne Versicherung können sie bekommen, wenn das eigene Geld nicht reicht.", "zusage"),
    ("Damit steht Ihnen eine Leistung zu, die das Einkommen nach der Geburt teilweise ersetzt.", "zusage"),
])
def test_textregeln_finden_verstoesse(text, code):
    assert any(f.startswith(code) for f in et.text_pruefen(text, "was")), et.text_pruefen(text, "was")


@pytest.mark.anforderung("ANF-DAT-16")
def test_textregeln_laenge_und_leerzeichen():
    assert et.text_pruefen("Zu kurz.", "was") == ["zu kurz (8 < 40 Zeichen)"]
    assert any(f.startswith("zu lang") for f in et.text_pruefen("Wort " * 100 + "Ende.", "danach"))
    assert et.text_pruefen(" Leerzeichen am Rand sind nicht erlaubt, auch nicht am Anfang.", "was") == \
        ["Leerzeichen am Rand oder doppelt"]
    assert et.text_pruefen(None, "was") == ["leer"]
    ok = "Kindergeld gibt es für jedes Kind, unabhängig vom Einkommen der Eltern, monatlich und auf Antrag."
    assert et.text_pruefen(ok, "was") == []


@pytest.mark.anforderung("ANF-DAT-16")
def test_textregeln_gelten_beim_laden(daten):
    def kaputt(i):
        i["erklaerungen"][0]["danach"] = "Die Familienkasse zahlt nach 6 Wochen aus."
    _aendern(daten / "fachmodule/familie/erklaerungen.json", kaputt)
    fehler = _fehler(daten)
    assert any(f.startswith("Erklärtext geburtsanzeige (danach): zahl") for f in fehler), fehler


@pytest.mark.anforderung("ANF-DAT-16")
def test_echte_texte_ohne_zahlen_und_zusagen(kb):
    """Doppelte Absicherung zur Prüfung beim Laden: alle Texte der Wissensbasis halten die Regeln ein."""
    for e in kb.erklaerungen.values():
        for art, text in (("was", e.was), ("danach", e.danach), ("achtung", e.achtung)):
            if text is not None:
                assert et.text_pruefen(text, art) == [], (e.leistung_id, art)
    for g in kb.glossar.values():
        assert et.text_pruefen(g.erklaerung, "glossar") == [], g.id


# ------------------------------------------------------------------ Glossar
@pytest.mark.anforderung("ANF-DAT-17")
def test_glossar_begriffe_existieren_und_werden_genutzt(kb):
    assert et.unbenutzte_begriffe(kb) == []
    for e in kb.erklaerungen.values():
        assert set(e.begriffe) <= set(kb.glossar), e.leistung_id


@pytest.mark.anforderung("ANF-DAT-17")
def test_glossar_fehler(daten):
    def doppelt(i):
        i["glossar"].append({**i["glossar"][0], "id": "nochmal", "begriff": i["glossar"][0]["begriff"].upper()})
    _aendern(daten / "kern/glossar.json", doppelt)
    _aendern(daten / "fachmodule/familie/erklaerungen.json",
             lambda i: i["erklaerungen"][0].update(begriffe=["standesamt", "standesamt", "gibt_es_nicht"]))
    fehler = _fehler(daten)
    assert any("Glossarbegriff nochmal: Begriff" in f and "ist schon als" in f for f in fehler)
    assert "Erklärtext geburtsanzeige: unbekannter Glossarbegriff gibt_es_nicht" in fehler
    assert "Erklärtext geburtsanzeige: Glossarbegriff doppelt" in fehler


# ------------------------------------------------------------------ Prüfstatus und Abnahme
@pytest.mark.anforderung("ANF-DAT-18")
def test_dateien_sind_maschinell_formatiert(kb):
    dateien = [d for d in kb.dateien if d.name in (et.DATEI_ERKLAERUNGEN, et.DATEI_GLOSSAR)]
    assert len(dateien) == 12  # elf Module und das Glossar
    for d in dateien:
        text = d.read_text(encoding="utf-8")
        assert et.formatiert(json.loads(text)) == text, d


@pytest.mark.anforderung("ANF-DAT-18", "ANF-QS-02")
def test_kein_text_von_claude_verifiziert(kb):
    """Entwürfe sind höchstens 'teilweise'; 'verifiziert' setzt nur ein Mensch mit Name und Datum."""
    for x in [*kb.erklaerungen.values(), *kb.glossar.values()]:
        if x.pruefstatus is Pruefstatus.VERIFIZIERT:
            assert x.geprueft_von and "claude" not in x.geprueft_von.lower()
    assert all(q for q in (x.quellen for x in kb.erklaerungen.values()))


@pytest.mark.anforderung("ANF-DAT-18")
def test_verifiziert_braucht_name_und_datum(daten):
    _aendern(daten / "kern/glossar.json", lambda i: i["glossar"][0].update(pruefstatus="verifiziert"))
    assert any("'verifiziert' braucht geprueft_am und geprueft_von" in f for f in _fehler(daten))


@pytest.mark.anforderung("ANF-DAT-18", "ANF-QS-02")
def test_abnahme_und_zuruecksetzen_ueber_cli(daten, capsys):
    assert main(["--daten", str(daten), "erklaerungen", "--abnehmen", "kindergeld"]) == 2
    assert "--von" in capsys.readouterr().err
    assert main(["--daten", str(daten), "--keine-farbe", "erklaerungen", "--abnehmen", "kindergeld",
                 "--von", "Erika Muster", "--am", "01.11.2026"]) == 0
    assert "kindergeld: verifiziert von Erika Muster am 01.11.2026" in capsys.readouterr().out
    kb = Wissensbasis.laden(daten)
    e = kb.erklaerungen["kindergeld"]
    assert (e.pruefstatus, e.geprueft_von, e.geprueft_am) == (Pruefstatus.VERIFIZIERT, "Erika Muster", date(2026, 11, 1))
    datei = daten / "fachmodule/familie/erklaerungen.json"
    assert et.formatiert(json.loads(datei.read_text(encoding="utf-8"))) == datei.read_text(encoding="utf-8")

    assert main(["--daten", str(daten), "erklaerungen", "--abnehmen", "bescheid", "--von", "Erika Muster"]) == 0
    assert Wissensbasis.laden(daten).glossar["bescheid"].pruefstatus is Pruefstatus.VERIFIZIERT
    assert main(["--daten", str(daten), "erklaerungen", "--zuruecksetzen", "kindergeld", "--status", "teilweise"]) == 0
    e = Wissensbasis.laden(daten).erklaerungen["kindergeld"]
    assert (e.pruefstatus, e.geprueft_von, e.geprueft_am) == (Pruefstatus.TEILWEISE, None, None)
    capsys.readouterr()
    assert main(["--daten", str(daten), "erklaerungen", "--abnehmen", "gibt_es_nicht", "--von", "X"]) == 1
    assert "Kein Erklärtext und kein Glossarbegriff" in capsys.readouterr().err


@pytest.mark.anforderung("ANF-DAT-18")
def test_abnahme_verweigert_handformatierte_datei(daten):
    datei = daten / "fachmodule/familie/erklaerungen.json"
    datei.write_text(json.dumps(json.loads(datei.read_text(encoding="utf-8")), ensure_ascii=False), encoding="utf-8")
    kb = Wissensbasis.laden(daten)
    with pytest.raises(et.AbnahmeFehler, match="nicht maschinell formatiert"):
        et.status_setzen(kb, "kindergeld", "verifiziert", "Erika Muster")
    assert et.formatieren(kb) == [datei]
    et.status_setzen(kb, "kindergeld", "verifiziert", "Erika Muster")


@pytest.mark.anforderung("ANF-DAT-18")
def test_cli_uebersicht(kb, capsys):
    assert main(["--keine-farbe", "erklaerungen", "--offen"]) == 0
    aus = capsys.readouterr().out
    assert "fachmodule/familie/erklaerungen.json" in aus and "[ungeprueft] elterngeld – Elterngeld" in aus
    assert main(["--keine-farbe", "erklaerungen", "elterngeld", "basiselterngeld"]) == 0
    aus = capsys.readouterr().out
    assert "Was: Elterngeld ersetzt" in aus and "Quelle: § 1 BEEG" in aus and "kern/glossar.json" in aus
    assert main(["--keine-farbe", "daten"]) == 0
    assert f"Erklärtexte: {len(kb.leistungen)} von {len(kb.leistungen)} Leistungen" in capsys.readouterr().out


@pytest.mark.anforderung("ANF-DAT-18")
def test_erklaertexte_erscheinen_in_den_verwendungen_der_quelle(kb):
    liste = qp.verwendungen(kb, "kschg_4")
    arten = {(v.art, v.objekt) for v in liste}
    assert ("Erklärtext", "kuendigungsschutzklage") in arten and ("Glossarbegriff", "arbeitsgericht") in arten


# ------------------------------------------------------------------ Verwendung in Bericht, Web und Formulierung
@pytest.mark.anforderung("ANF-WEB-15")
def test_bericht_enthaelt_erklaertexte_und_glossar(kb):
    b = api.bericht(kb, {"plz": "80331", "stichtag": "2026-10-24", "fakten": {}})
    for l in b["leistungen"]:
        e = kb.erklaerungen[l["id"]]
        assert l["erklaerung"]["was"] == e.was and l["erklaerung"]["pruef_text"] == "Erklärung noch nicht geprüft"
    benutzt = {x for l in b["leistungen"] for x in l["erklaerung"]["begriffe"]}
    assert {g["id"] for g in b["glossar"]} == benutzt
    assert all(g["erklaerung"] == kb.glossar[g["id"]].erklaerung for g in b["glossar"])


@pytest.mark.anforderung("ANF-WEB-15")
def test_detailansicht_zeigt_erklaerung_und_begriffe():
    js = (STATIC / "detail.js").read_text(encoding="utf-8")
    assert 'abschnitt("Was ist das?"' in js and "erklaerungAbschnitt(l, b.glossar || [], relevant)" in js
    assert 'el("details", {}, el("summary", {}, g.begriff)' in js and "e.pruef_text" in js


@pytest.mark.anforderung("ANF-CLI-06")
def test_terminal_zeigt_erklaerung_bei_details(capsys):
    assert main(["--keine-farbe", "pruefen", "--szenario", "muenchen_verheiratet_angestellt", "--details"]) == 0
    aus = capsys.readouterr().out
    assert "Was ist das? [Erklärung noch nicht geprüft]" in aus and "Nach dem Antrag: " in aus
    assert "Begriff Elterngeldstelle:" in aus


@pytest.mark.anforderung("ANF-LLM-23")
def test_formulierung_bekommt_erklaertexte_nach_leistungs_id(kb):
    b = planen(kb, szenarien.finden(kb, "muenchen_verheiratet_angestellt").anfrage)
    daten = modell_daten(kb, b)
    for l in daten["leistungen"]:
        e = kb.erklaerungen[l["id"]]
        assert l["erklaerung"]["was"] == e.was
        if l["ergebnis"] == "nein":
            assert l["erklaerung"]["danach"] is None and l["erklaerung"]["achtung"] is None
        else:
            assert l["erklaerung"]["danach"] == e.danach
    texte = {a.id: a.text for a in vorlage(kb, b, daten).abschnitte}
    ja = next(l for l in daten["leistungen"] if l["ergebnis"] == "ja" and kb.erklaerungen[l["id"]].danach)
    assert kb.erklaerungen[ja["id"]].was in texte[ja["id"]]
    assert "Nach dem Antrag: " + kb.erklaerungen[ja["id"]].danach in texte[ja["id"]]
    nein = [l for l in daten["leistungen"] if l["ergebnis"] == "nein"]
    assert nein, "Szenario soll auch Leistungen mit 'nein' enthalten"
    for l in nein:
        assert kb.erklaerungen[l["id"]].was not in texte[l["id"]]
