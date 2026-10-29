"""Befunde aus der Prüfung der Bundesgesetze (#55, #56): Tests, die die Fehler gefunden hätten."""

from datetime import date

import pytest

from buergerai import quellenpruefung as qp
from conftest import familie


@pytest.mark.anforderung("ANF-EZ-02")
def test_elternzeit_textform_seit_mai_2025(kb):
    """§ 16 Abs. 1 BEEG i. d. F. des BEG IV: Textform genügt für Geburten ab 1.5.2025."""
    schritte = " ".join(kb.varianten["elternzeit_bund"].verfahren.schritte)
    assert "Textform" in schritte and "1.5.2025" in schritte
    assert "schriftlich" in schritte, "für ältere Kinder bleibt die Schriftform"


@pytest.mark.anforderung("ANF-KG-03")
def test_kindergeld_rueckwirkung_zitiert_paragraf_70(kb):
    """Die Sechs-Monats-Rückwirkung steht seit 2019 in § 70 Abs. 1 Satz 2 EStG (vorher § 66 Abs. 3)."""
    frist = kb.varianten["kindergeld_bund"].verfahren.fristen[0]
    assert frist.monate == 6 and frist.quellen == ("estg_70",)
    assert "Höhe" in kb.quellen["estg_66"].titel and "6 Monate" not in kb.quellen["estg_66"].titel


@pytest.mark.anforderung("ANF-EG-02")
def test_grenze_200000_zitiert_uebergangsvorschrift(kb):
    """Die 200.000-€-Grenze für Geburten 1.4.2024–31.3.2025 steht in § 28 Abs. 5 BEEG, nicht in § 1."""
    texte = {v.text for v in qp.verwendungen(kb, "beeg_28") if v.art == "Bedingung"}
    assert any("200.000" in t for t in texte)
    assert not any("200.000" in v.text for v in qp.verwendungen(kb, "beeg_1"))


@pytest.mark.anforderung("ANF-EG-02")
def test_keine_eigene_grenze_fuer_alleinerziehende_2024(plane):
    """150.000 € für Alleinerziehende stand nur im Entwurf; beschlossen sind 200.000 € für alle."""
    b = plane(familie(kind_geboren="ja", errechneter_termin=None, geburtsdatum="2024-10-01",
                      partner_im_haushalt="nein", zve_eltern=180000), stichtag=date(2025, 1, 15))
    assert b.eintrag("elterngeld").ergebnis.value == "ja"
