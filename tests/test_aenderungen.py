"""Änderungswächter für geprüfte Quellen (#64) – ohne Netz, mit gespeicherten Texten."""

from __future__ import annotations

import io
import json
import shutil
import zipfile
from datetime import date
from pathlib import Path

import pytest

from buergerai import aenderungen as ae
from buergerai import quellenpruefung as qp
from buergerai import quelltext as qt
from buergerai.cli import main
from buergerai.modell import Pruefstatus
from buergerai.wissensbasis import STANDARD_DATENVERZEICHNIS, Wissensbasis

DATEN = Path(__file__).parent / "daten" / "quelltext"
BEEG_XML = (DATEN / "beeg_auszug.xml").read_text(encoding="utf-8")
BEEG_URL = "https://www.gesetze-im-internet.de/beeg/__1.html"
BY_URL = "https://www.gesetze-bayern.de/Content/Document/BayFamGG-9a"
AM = date(2026, 10, 30)
SPAETER = date(2026, 11, 9)

SEITE = """<html><body><nav>Zur Startseite</nav><p>{nav}</p><p>Text gilt ab: {stand}</p>
<p>Nächstes Dokument (inaktiv)</p>
<h1>Art. 9a</h1><p>Übergangsvorschriften</p>
<p>(1) Hinsichtlich vor dem 1. Januar 2025 geborener Kinder sind Art. 2 bis 8 weiter anzuwenden.</p>
<p>(2) Anträge auf Familiengeld für Kinder, die ab dem {datum} geboren wurden, sind unbeachtlich.</p>
<p>{zusatz}</p>
<p>Bayern.de</p><p>Datenschutz</p><p>{fuss}</p></body></html>"""


def seite(nav: str = "Inhaltsverzeichnis", stand: str = "31.12.2025", datum: str = "1. Januar 2025",
          zusatz: str = "Seite aktualisiert am 30.10.2026", fuss: str = "Kontrastwechsel") -> qt.Quelltext:
    html = SEITE.format(nav=nav, stand=stand, datum=datum, zusatz=zusatz, fuss=fuss)
    return qt.Quelltext(BY_URL, qt.OK, qt.html_text(html.encode("utf-8"), "text/html; charset=utf-8"))


def gesetz(xml: str = BEEG_XML, url: str = BEEG_URL) -> qt.Quelltext:
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w") as z:
        z.writestr("BJNR274810006.xml", xml)
    speicher = qt.Zwischenspeicher(lambda _u: (puffer.getvalue(), "application/zip"))
    return qt.holen(url, speicher)


NEUER_STAND = "Zuletzt geändert durch Art. 1 G v. 1.1.2026 I Nr. 1", "Zuletzt geändert durch Art. 3 G v. 1.6.2026 I Nr. 99"


# ------------------------------------------------------------------ Bezugstext
@pytest.mark.anforderung("ANF-QS-07")
def test_bezugstext_html_nur_inhaltsbereich():
    zeilen, stand = ae.bezugstext(seite())
    assert stand == "Text gilt ab: 31.12.2025"
    assert zeilen[0] == "Art. 9a" and "Bayern.de" not in zeilen and "Kontrastwechsel" not in zeilen
    assert not any("Inhaltsverzeichnis" in z or "aktualisiert" in z for z in zeilen)
    # „1. Januar“ wird nicht als Satzende getrennt
    assert any("vor dem 1. Januar 2025 geborener Kinder" in z for z in zeilen)


@pytest.mark.anforderung("ANF-QS-07")
def test_bezugstext_gesetz_paragraf_in_saetzen():
    q = gesetz()
    zeilen, stand = ae.bezugstext(q)
    assert stand == NEUER_STAND[0]
    assert zeilen[0] == "§ 1 Berechtigte" and zeilen[1].startswith("(1) Anspruch auf Elterngeld")
    assert any(z.startswith("(6) Eine Person ist nicht voll erwerbstätig") for z in zeilen), "je Absatz eine Zeile"
    assert not any("drei Lebensmonate" in z for z in zeilen), "nur der Paragraf aus der URL (§ 1), nicht § 7"


# ------------------------------------------------------------------ Vergleich
@pytest.fixture
def ablage(tmp_path):
    return tmp_path / "pruefprotokolle"


@pytest.mark.anforderung("ANF-QS-07")
def test_html_unveraendert_unwesentlich_und_geaendert(ablage):
    fa = ae.speichern(seite(), "bayfamgg_9a", AM, "abnahme", ablage)
    assert ae.lesen(ablage)["bayfamgg_9a"] == fa
    assert (ablage / "texte" / "bayfamgg_9a.txt").read_text(encoding="utf-8").startswith("Art. 9a\n")

    assert ae.vergleichen("bayfamgg_9a", seite(), fa, SPAETER, ablage).status == ae.UNVERAENDERT
    # Nur Unwesentliches: Navigation, Fußzeile, „Seite aktualisiert am“
    unwesentlich = seite(nav="Neues Menü", zusatz="Seite aktualisiert am 08.11.2026", fuss="Leichte Sprache")
    assert ae.vergleichen("bayfamgg_9a", unwesentlich, fa, SPAETER, ablage).status == ae.UNVERAENDERT

    v = ae.vergleichen("bayfamgg_9a", seite(datum="1. September 2026"), fa, SPAETER, ablage)
    assert v.geaendert
    assert "-(2) Anträge auf Familiengeld für Kinder, die ab dem 1. Januar 2025 geboren wurden, sind unbeachtlich." in v.diff
    assert "+(2) Anträge auf Familiengeld für Kinder, die ab dem 1. September 2026 geboren wurden, sind unbeachtlich." in v.diff
    assert "GEÄNDERT (+1/−1 Zeilen)" in v.zusammenfassung()


@pytest.mark.anforderung("ANF-QS-07")
def test_gesetz_erst_stand_dann_paragraf(ablage):
    fa = ae.speichern(gesetz(), "beeg_1", AM, "abnahme", ablage)
    assert fa.stand == NEUER_STAND[0] and fa.abschnitt == "§ 1 BEEG"

    # Gleicher Stand: unverändert, ohne den Text zu vergleichen
    gleich = gesetz(BEEG_XML.replace("32 Wochenstunden", "30 Wochenstunden"))
    assert ae.vergleichen("beeg_1", gleich, fa, SPAETER, ablage).status == ae.UNVERAENDERT

    # Neuer Stand, aber nur § 7 geändert: § 1 unverändert
    nur_7 = gesetz(BEEG_XML.replace(*NEUER_STAND).replace("drei Lebensmonate", "vier Lebensmonate"))
    v = ae.vergleichen("beeg_1", nur_7, fa, SPAETER, ablage)
    assert v.status == ae.UNVERAENDERT and "Gesetz geändert, Abschnitt nicht" in v.zusammenfassung()

    # Neuer Stand und § 1 geändert
    neu = gesetz(BEEG_XML.replace(*NEUER_STAND).replace("32 Wochenstunden", "30 Wochenstunden"))
    v = ae.vergleichen("beeg_1", neu, fa, SPAETER, ablage)
    assert v.geaendert and v.stand_neu == NEUER_STAND[1]
    assert any(z.startswith("+(6)") and "30 Wochenstunden" in z for z in v.diff)
    assert any(z.startswith("-(6)") and "32 Wochenstunden" in z for z in v.diff)


@pytest.mark.anforderung("ANF-QS-07")
def test_sonderfaelle(ablage):
    assert ae.vergleichen("beeg_1", gesetz(), None, SPAETER, ablage).status == ae.KEIN_FINGERABDRUCK
    fa = ae.speichern(gesetz(), "beeg_1", AM, "abnahme", ablage)
    andere_url = gesetz(url="https://www.gesetze-im-internet.de/beeg/__7.html")
    assert ae.vergleichen("beeg_1", andere_url, fa, SPAETER, ablage).status == ae.URL_GEAENDERT
    weg = qt.Quelltext(BEEG_URL, qt.NICHT_ERREICHBAR, meldung="timed out")
    v = ae.vergleichen("beeg_1", weg, fa, SPAETER, ablage)
    assert v.status == qt.NICHT_ERREICHBAR and not v.geaendert
    with pytest.raises(ValueError, match="nicht verfügbar"):
        ae.speichern(weg, "beeg_1", AM, "abnahme", ablage)


# ------------------------------------------------------------------ Daten und Ausgabe
@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    daten = tmp_path / "data"
    shutil.copytree(STANDARD_DATENVERZEICHNIS, daten)
    protokolle = tmp_path / "pruefprotokolle"
    shutil.copytree(qp.PROTOKOLL_VERZEICHNIS, protokolle,
                    ignore=shutil.ignore_patterns(ae.DATEINAME, ae.TEXTE))  # ohne eingecheckte Fingerabdrücke
    monkeypatch.setattr(qp, "PROTOKOLL_VERZEICHNIS", protokolle)
    return daten, protokolle


@pytest.mark.anforderung("ANF-QS-07")
def test_vermerken_aendert_nur_das_feld_und_zeigt_hinweis(umgebung, capsys):
    daten, _ = umgebung
    kb = Wissensbasis.laden(daten)
    datei = qp._quelldatei(kb, "beeg_1")
    vorher = datei.read_text(encoding="utf-8")
    ae.vermerken(kb, "beeg_1", SPAETER)
    nachher = json.loads(datei.read_text(encoding="utf-8"))
    eintrag = next(q for q in nachher["quellen"] if q["id"] == "beeg_1")
    assert eintrag[ae.FELD] == "2026-11-09"
    del eintrag[ae.FELD]
    assert nachher == json.loads(vorher), "sonst ändert sich nichts"

    kb2 = Wissensbasis.laden(daten)
    q = kb2.quellen["beeg_1"]
    assert q.seit_pruefung_geaendert == SPAETER and q.pruefstatus is kb.quellen["beeg_1"].pruefstatus

    argv = ["--keine-farbe", "--daten", str(daten), "pruefen", "-s", "muenchen_verheiratet_angestellt"]
    assert main([*argv, "--details"]) == 0
    out = capsys.readouterr().out
    assert "Quelle seit Prüfung geändert" in out and "festgestellt am 09.11.2026" in out
    assert main([*argv, "--json"]) == 0
    eintraege = json.loads(capsys.readouterr().out)["leistungen"]
    assert any("beeg_1" in e["quellen_seit_pruefung_geaendert"] for e in eintraege)

    from buergerai.planer import Anfrage, planen
    from buergerai.web import api

    bericht = planen(kb2, Anfrage(plz="80331", stichtag=AM, lebenslagen=["geburt"], fakten={}))
    elterngeld = next(e for e in bericht.eintraege if any(q.id == "beeg_1" for q in e.quellen))
    j = api._eintrag_json(elterngeld, kb2)
    assert "Quelle seit Prüfung geändert" in j["pruef_text"]
    assert next(q for q in j["quellen"] if q["id"] == "beeg_1")["seit_pruefung_geaendert"] == "2026-11-09"

    ae.vermerken(kb2, "beeg_1", None)
    assert datei.read_text(encoding="utf-8") == vorher, "Entfernen stellt den alten Text her"


@pytest.mark.anforderung("ANF-QS-07")
def test_abnahme_entfernt_hinweis(umgebung):
    daten, protokolle = umgebung
    kb = Wissensbasis.laden(daten)
    ae.vermerken(kb, "bayfamgg_9a", SPAETER)
    kb = Wissensbasis.laden(daten)
    qp.abnehmen(kb, "bayfamgg_9a", "Janis Uhrig", AM, protokolle=protokolle)
    q = Wissensbasis.laden(daten).quellen["bayfamgg_9a"]
    assert q.pruefstatus is Pruefstatus.VERIFIZIERT and q.seit_pruefung_geaendert is None


# ------------------------------------------------------------------ CLI und Issue
class Netz:
    def __init__(self, inhalte: dict[str, tuple[bytes, str]]):
        self.inhalte = inhalte

    def __call__(self, url: str) -> tuple[bytes, str]:
        if url not in self.inhalte:
            raise qt.AbrufFehler("timed out", netz=True)
        return self.inhalte[url]


def html(**kw: str) -> tuple[bytes, str]:
    return SEITE.format(**{"nav": "x", "stand": "31.12.2025", "datum": "1. Januar 2025", "zusatz": "",
                           "fuss": "", **kw}).encode("utf-8"), "text/html; charset=utf-8"


@pytest.mark.anforderung("ANF-QS-07")
def test_cli_abnahme_fingerabdruck_aenderungen_issue(umgebung, capsys, monkeypatch, tmp_path):
    daten, protokolle = umgebung
    argv = ["--keine-farbe", "--daten", str(daten), "quellen"]
    monkeypatch.setattr(qt, "http_abruf", Netz({BY_URL: html()}))

    # Abnahme speichert den Fingerabdruck
    assert main([*argv, "--abnehmen", "bayfamgg_9a", "--von", "Janis Uhrig", "--ohne-cache"]) == 0
    assert "Fingerabdruck: sha256:" in capsys.readouterr().out
    assert ae.lesen(protokolle)["bayfamgg_9a"].anlass == "abnahme"

    # Unverändert
    assert main([*argv, "--aenderungen", "bayfamgg_9a", "--ohne-cache"]) == 0
    assert "bayfamgg_9a: Text seit" in capsys.readouterr().out

    # Geändert: Diff, Hinweis in den Daten, Issue-Text
    monkeypatch.setattr(qt, "http_abruf", Netz({BY_URL: html(datum="1. September 2026")}))
    issues = tmp_path / "issues"
    bericht = tmp_path / "bericht.md"
    code = main([*argv, "--aenderungen", "--ohne-cache", "--vermerken", "--issues", str(issues),
                 "--bericht", str(bericht)])
    out = capsys.readouterr().out
    assert code == 1, out
    assert "GEÄNDERT" in out and "+(2) Anträge auf Familiengeld für Kinder, die ab dem 1. September 2026" in out
    assert Wissensbasis.laden(daten).quellen["bayfamgg_9a"].seit_pruefung_geaendert == date.today()
    text = (issues / "bayfamgg_9a.md").read_text(encoding="utf-8")
    assert "```diff" in text and "1. September 2026" in text
    assert "### Betroffene Verwendungen" in text and "familiengeld" in text
    assert "--fingerabdruck bayfamgg_9a" in text and "verifiziert (geprüft am" in text
    assert "🔴" in bericht.read_text(encoding="utf-8")

    # Unwesentlich: neu erfassen entfernt den Hinweis
    assert main([*argv, "--fingerabdruck", "bayfamgg_9a", "--ohne-cache"]) == 0
    assert "Hinweis „seit Prüfung geändert“ entfernt" in capsys.readouterr().out
    assert Wissensbasis.laden(daten).quellen["bayfamgg_9a"].seit_pruefung_geaendert is None
    assert ae.lesen(protokolle)["bayfamgg_9a"].anlass == "erfasst"
    assert main([*argv, "--aenderungen", "bayfamgg_9a", "--ohne-cache"]) == 0
    capsys.readouterr()

    # Abnahme nach einer Änderung seit dem Fingerabdruck: verweigert, mit Diff
    assert main([*argv, "--zuruecksetzen", "bayfamgg_9a"]) == 0
    capsys.readouterr()
    monkeypatch.setattr(qt, "http_abruf", Netz({BY_URL: html(datum="1. Mai 2026")}))
    assert main([*argv, "--abnehmen", "bayfamgg_9a", "--von", "Janis Uhrig", "--ohne-cache"]) == 1
    err = capsys.readouterr().err
    assert "seit dem Fingerabdruck" in err and "1. Mai 2026" in err
    assert Wissensbasis.laden(daten).quellen["bayfamgg_9a"].pruefstatus is Pruefstatus.TEILWEISE

    # Kein Netz
    monkeypatch.setattr(qt, "http_abruf", Netz({}))
    assert main([*argv, "--aenderungen", "--ohne-cache"]) == 2
    assert "Keine Quelle erreichbar" in capsys.readouterr().out


@pytest.mark.anforderung("ANF-QS-07")
def test_cli_abnahme_ohne_netz_meldet_nachholen(umgebung, capsys, monkeypatch):
    daten, protokolle = umgebung
    monkeypatch.setattr(qt, "http_abruf", Netz({}))
    assert main(["--keine-farbe", "--daten", str(daten), "quellen", "--abnehmen", "bayfamgg_9a",
                 "--von", "Janis Uhrig", "--ohne-cache"]) == 0, "Abnahme gelingt auch ohne Netz"
    out = capsys.readouterr().out
    assert "Fingerabdruck nicht gespeichert" in out and "--fingerabdruck bayfamgg_9a" in out


@pytest.mark.anforderung("ANF-QS-07")
def test_gespeicherte_fingerabdruecke_passen_zu_den_texten():
    """Die eingecheckten Bezugstexte gehören zu ihren Prüfsummen und zu Quellen mit gleicher URL."""
    kb = Wissensbasis.laden()
    for qid, fa in ae.lesen().items():
        zeilen = ae.textpfad(qid).read_text(encoding="utf-8").splitlines()
        assert ae.pruefsumme(zeilen) == fa.pruefsumme, qid
        assert kb.quellen[qid].url == fa.url, f"{qid}: URL geändert – Fingerabdruck neu erfassen"
