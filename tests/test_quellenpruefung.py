"""Werkzeuge für die Quellenprüfung (#53): Verwendungen, Protokollgerüst, Phase-1-Filter."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date

import pytest

from buergerai import quellenpruefung as qp
from buergerai.cli import main
from buergerai.modell import Pruefstatus

# Quellen der Phase 1 laut Issue #45 (destatis_gv ist seit #40 durch destatis_kreise und openplz_strassen ersetzt)
PHASE1_LAUT_ISSUE = {
    "stmas_familiengeld_2024", "landtag_by_familiengeld", "beeg_1", "estg_62", "sgb5_10", "muschg_19_20",
    "sgb5_24i", "bkgg_6a", "bgb_1592_1594", "bgb_1626a", "pstg_18", "beeg_7", "estg_66", "beeg_15_16",
    "familienportal_elterngeld", "familienportal_mutterschaft", "ba_kindergeld", "bas_mutterschaftsgeld",
    "zbfs_elterngeld", "fim_by_elterngeld", "muenchen_geburtsurkunde", "elterngeldrechner", "kiz_lotse",
    "destatis_kreise", "openplz_strassen",
}


def lauf(capsys, *argv):
    code = main(["--keine-farbe", *argv])
    out = capsys.readouterr()
    return code, out.out, out.err


@pytest.mark.anforderung("ANF-QS-03")
def test_verwendungen_mit_datei_pfad_und_art(kb):
    liste = qp.verwendungen(kb, "pstg_18")
    fristen = [v for v in liste if v.art == "Frist"]
    assert fristen, "Die Wochenfrist der Geburtsanzeige zitiert § 18 PStG"
    v = next(v for v in fristen if v.objekt == "geburtsanzeige_bund")
    assert v.datei == "fachmodule/familie/geburt.json"
    assert v.pfad.endswith(".verfahren.fristen[0]") and v.pfad.startswith("varianten[")
    assert "Woche" in v.text
    # Der Pfad führt in der Datei tatsächlich zu einem Knoten, der die Quelle nennt
    knoten = json.loads((qp.STANDARD_DATENVERZEICHNIS / v.datei).read_text(encoding="utf-8"))
    for teil in v.pfad.replace("[", ".[").split("."):
        knoten = knoten[int(teil[1:-1])] if teil.startswith("[") else knoten[teil]
    assert "pstg_18" in knoten["quellen"]


@pytest.mark.anforderung("ANF-QS-03")
def test_verwendungen_bedingungen_betraege_und_vererbung(kb):
    liste = qp.verwendungen(kb, "beeg_1")
    bedingungen = [v for v in liste if v.art == "Bedingung"]
    assert any("32" in v.text and "erwerbsstunden" in v.text for v in bedingungen)
    assert any(v.text.startswith("Prüfung nötig:") for v in bedingungen)
    # Die Bundesvariante wird von den Landesvarianten geerbt – je Variante einmal genannt, nicht je Bedingung
    mit_erben = [v for v in liste if v.erben]
    assert len({v.objekt for v in mit_erben}) == len(mit_erben)
    bund = next(v for v in mit_erben if v.objekt == "elterngeld_bund")
    assert "elterngeld_by" in bund.erben
    assert "gilt per erbt_von auch für" in qp.beschreibung(bund)

    assert any(v.art == "Betrag" for v in qp.verwendungen(kb, "elterngeldrechner"))
    assert any(v.art == "Zuständigkeit" for v in qp.verwendungen(kb, "zbfs_elterngeld"))


@pytest.mark.anforderung("ANF-QS-03")
def test_grosse_gruppen_gekuerzt_pilotgebiete_bleiben(kb):
    liste = qp.verwendungen(kb, "destatis_kreise")
    assert len(liste) > 300
    kurz = qp.zusammenfassen(liste, qp.phase1_gebiete(kb))
    gezeigt = {v.objekt for v in kurz if not isinstance(v, str)}
    assert {"09162", "09178"} <= gezeigt and len(gezeigt) <= 5
    hinweis = [v for v in kurz if isinstance(v, str)]
    assert len(hinweis) == 1 and f"{len(liste) - len(gezeigt)} weitere" in hinweis[0]


@pytest.mark.anforderung("ANF-QS-03")
def test_phase1_quellen(kb):
    phase1 = set(qp.phase1_quellen(kb))
    assert PHASE1_LAUT_ISSUE <= phase1
    # Nichts aus anderen Ländern oder Lebenslagen
    assert "sachsen_landeserziehungsgeld" not in phase1
    assert not any(q.startswith(("bb_", "be_", "nrw_")) for q in phase1)


@pytest.mark.anforderung("ANF-QS-03")
def test_protokoll_geruest(kb):
    text = qp.protokoll_geruest(kb, "beeg_1", date(2026, 10, 27))
    assert text.startswith("# Prüfprotokoll: beeg_1")
    assert "https://www.gesetze-im-internet.de/beeg/__1.html" in text
    assert "Fassung/Stand:" in text and "Abnahme: <Name, Datum>" in text
    assert f"## Verwendungen in der Wissensbasis ({len(qp.verwendungen(kb, 'beeg_1'))})" in text
    assert "`varianten[7].regel.alle[3]`" in text or "erwerbsstunden_nach_geburt <= 32" in text
    assert "## Abweichungen und Folgeaktionen" in text
    # Tabellenzeilen haben alle gleich viele Spalten
    zeilen = [z for z in text.splitlines() if z.startswith("| ") and not z.startswith("| #")]
    assert zeilen and all(z.count(" | ") == 4 for z in zeilen)


@pytest.mark.anforderung("ANF-QS-03")
def test_ohne_protokoll(kb, tmp_path):
    q = kb.quellen["fim_by_elterngeld"]
    assert q.pruefstatus is Pruefstatus.TEILWEISE
    assert "fim_by_elterngeld" in qp.ohne_protokoll(kb, tmp_path)
    assert all(kb.quellen[i].pruefstatus is not Pruefstatus.UNGEPRUEFT for i in qp.ohne_protokoll(kb, tmp_path))

    (tmp_path / "fim_by_elterngeld.md").write_text("# Prüfprotokoll: fim_by_elterngeld\n", encoding="utf-8")
    assert not qp.hat_protokoll(q, tmp_path), "Datei allein reicht nicht – die Notiz muss verlinken"
    verlinkt = replace(q, notiz="Protokoll: docs/pruefprotokolle/fim_by_elterngeld.md")
    assert qp.hat_protokoll(verlinkt, tmp_path)
    assert not qp.hat_protokoll(verlinkt, tmp_path / "leer"), "Link ohne Datei reicht nicht"


@pytest.mark.anforderung("ANF-QS-03")
def test_cli_verwendung(capsys):
    code, out, _ = lauf(capsys, "quellen", "--verwendung", "pstg_18")
    assert code == 0
    assert "Verwendungen von pstg_18" in out and "fachmodule/familie/geburt.json" in out
    assert "verfahren.fristen[0]" in out

    code, out, _ = lauf(capsys, "quellen", "--verwendung", "openplz_strassen")
    assert "weitere Einträge der Art Gebiet" in out and "09162000" in out

    code, _, err = lauf(capsys, "quellen", "--verwendung", "gibt_es_nicht")
    assert code == 2 and "Unbekannte Quelle" in err


@pytest.mark.anforderung("ANF-QS-03")
def test_cli_protokoll_ueberschreibt_nicht(capsys, monkeypatch, tmp_path):
    monkeypatch.setattr(qp, "PROTOKOLL_VERZEICHNIS", tmp_path / "pruefprotokolle")
    code, out, _ = lauf(capsys, "quellen", "--protokoll", "beeg_7")
    ziel = tmp_path / "pruefprotokolle" / "beeg_7.md"
    assert code == 0 and ziel.is_file() and "Protokoll angelegt" in out
    assert "# Prüfprotokoll: beeg_7" in ziel.read_text(encoding="utf-8")

    ziel.write_text("eigene Notizen", encoding="utf-8")
    code, _, err = lauf(capsys, "quellen", "--protokoll", "beeg_7")
    assert code == 1 and "nicht überschrieben" in err
    assert ziel.read_text(encoding="utf-8") == "eigene Notizen"


@pytest.mark.anforderung("ANF-QS-03")
def test_cli_phase1_und_warnung(capsys):
    code, out, _ = lauf(capsys, "quellen", "--phase1", "--offen")
    assert code == 0 and "Phase 1" in out
    assert "[teilweise] beeg_1" in out and "sachsen_landeserziehungsgeld" not in out

    code, out, _ = lauf(capsys, "daten")
    assert code == 0 and "ohne verlinktes Prüfprotokoll" in out
