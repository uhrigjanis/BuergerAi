import json
import shutil
from pathlib import Path

import pytest

from buergerai.wissensbasis import STANDARD_DATENVERZEICHNIS, DatenFehler, Wissensbasis


def kopie(tmp_path: Path) -> Path:
    ziel = tmp_path / "data"
    shutil.copytree(STANDARD_DATENVERZEICHNIS, ziel)
    return ziel


def bearbeite(datei: Path, aendern) -> None:
    inhalt = json.loads(datei.read_text(encoding="utf-8"))
    aendern(inhalt)
    datei.write_text(json.dumps(inhalt, ensure_ascii=False), encoding="utf-8")


@pytest.mark.anforderung("ANF-DAT-06")
def test_echte_daten_sind_konsistent(kb):
    assert kb.konsistenz_pruefen() == []
    assert kb.unbenutzte_fakten() == []


@pytest.mark.anforderung("ANF-DAT-06")
@pytest.mark.parametrize(
    "aendern,meldung",
    [
        (lambda d: d["varianten"][0].update(zustaendigkeit_id="gibt_es_nicht"), "unbekannte Zuständigkeit"),
        (lambda d: d["varianten"][1]["regel"].update(fakt="gibt_es_nicht"), "unbekannter Fakt"),
        (lambda d: d["varianten"][1]["regel"].update(op="~="), "unbekannter Operator"),
        (lambda d: d["varianten"][1]["regel"].pop("text"), "braucht einen 'text'"),
        (lambda d: d["varianten"][0].update(quellen=["gibt_es_nicht"]), "unbekannte Quelle"),
        (lambda d: d["varianten"][0].update(quellen=[]), "mindestens eine Quelle"),
        (lambda d: d["leistungen"][0].update(voraussetzungen=["gibt_es_nicht"]), "unbekannte Voraussetzung"),
        (lambda d: d["varianten"][1]["regel"].update(fakt="person.beschaeftigt"), "'person.'-Fakten nur"),
    ],
)
def test_fehler_werden_erkannt(tmp_path, aendern, meldung):
    daten = kopie(tmp_path)
    bearbeite(daten / "bund" / "geburt.json", aendern)
    with pytest.raises(DatenFehler) as info:
        Wissensbasis.laden(daten)
    assert any(meldung in f for f in info.value.fehler), info.value.fehler


@pytest.mark.anforderung("ANF-DAT-06")
def test_auswahlwert_muss_option_sein(tmp_path):
    daten = kopie(tmp_path)

    def aendern(d):
        v = next(v for v in d["varianten"] if v["id"] == "mutterschaftsgeld_bas_bund")
        v["regel"]["alle"][1]["wert"] = ["privat", "tippfehler"]

    bearbeite(daten / "bund" / "geburt.json", aendern)
    with pytest.raises(DatenFehler, match="tippfehler"):
        Wissensbasis.laden(daten)


@pytest.mark.anforderung("ANF-DAT-06")
def test_doppelte_ids_und_kaputtes_json(tmp_path):
    daten = kopie(tmp_path)
    (daten / "doppelt.json").write_text(json.dumps({"gebiete": [{"id": "09", "name": "X", "ebene": "land", "parent_id": "DE"}]}))
    (daten / "kaputt.json").write_text("{ nicht json")
    with pytest.raises(DatenFehler) as info:
        Wissensbasis.laden(daten)
    text = "\n".join(info.value.fehler)
    assert "doppelte ID 09" in text and "ungültiges JSON" in text


@pytest.mark.anforderung("ANF-DAT-07")
def test_vererbung_von_varianten(kb):
    bund, by = kb.varianten["elterngeld_bund"], kb.varianten["elterngeld_by"]
    assert by.regel == bund.regel
    assert by.verfahren == bund.verfahren
    assert by.zustaendigkeit_id == "zbfs_elterngeld"  # überschrieben
    muenchen = kb.varianten["geburtsanzeige_muenchen"]
    assert muenchen.verfahren != kb.varianten["geburtsanzeige_bund"].verfahren  # eigenes Verfahren


@pytest.mark.anforderung("ANF-DAT-07")
def test_vererbung_unbekannte_basis(tmp_path):
    daten = kopie(tmp_path)
    bearbeite(daten / "laender" / "by" / "geburt.json", lambda d: d["varianten"][0].update(erbt_von="fehlt"))
    with pytest.raises(DatenFehler, match="erbt_von unbekannte Variante"):
        Wissensbasis.laden(daten)


@pytest.mark.anforderung("ANF-QS-02")
def test_verifiziert_braucht_pruefer(tmp_path):
    daten = kopie(tmp_path)

    def aendern(d):
        d["quellen"][0].update(pruefstatus="verifiziert")
        d["quellen"][0].pop("geprueft_von", None)

    bearbeite(daten / "bund" / "quellen.json", aendern)
    with pytest.raises(DatenFehler, match="braucht geprueft_am und geprueft_von"):
        Wissensbasis.laden(daten)


@pytest.mark.anforderung("ANF-QS-02")
def test_keine_quelle_ohne_menschliche_pruefung_verifiziert(kb):
    """Bis ein Mensch geprüft hat, darf nichts als verifiziert gelten."""
    for q in kb.quellen.values():
        if q.pruefstatus.value == "verifiziert":
            assert q.geprueft_von and not q.geprueft_von.startswith("Claude")
