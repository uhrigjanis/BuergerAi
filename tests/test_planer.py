from datetime import date

import pytest

from buergerai.modell import Abdeckung, Pruefstatus
from buergerai.planer import beste_variante
from buergerai.regeln import Wert
from conftest import familie


@pytest.mark.anforderung("ANF-DAT-01")
def test_spezifischste_variante(kb, plane):
    assert plane(familie()).eintrag("geburtsanzeige").variante.id == "geburtsanzeige_muenchen"
    assert plane(familie(), plz="85354").eintrag("geburtsanzeige").variante.id == "geburtsanzeige_by"
    assert plane(familie(), plz=None, land="HE").eintrag("geburtsanzeige").variante.id == "geburtsanzeige_bund"
    assert plane(familie()).eintrag("elterngeld").variante.id == "elterngeld_by"


@pytest.mark.anforderung("ANF-DAT-02")
def test_gueltigkeit_von_betraegen(plane):
    assert plane(familie(), stichtag=date(2025, 6, 1)).eintrag("kindergeld").betrag.text.startswith("255 €")
    assert plane(familie(), stichtag=date(2026, 6, 1)).eintrag("kindergeld").betrag.text.startswith("259 €")


@pytest.mark.anforderung("ANF-DAT-02")
def test_gueltigkeit_von_varianten(kb):
    from dataclasses import replace

    from buergerai.gebiete import aufloesen
    from buergerai.modell import Zeitraum

    alt = kb.varianten["geburtsanzeige_muenchen"]
    kb.varianten["geburtsanzeige_muenchen"] = replace(alt, zeitraum=Zeitraum(gueltig_bis=date(2026, 1, 1)))
    try:
        v, _ = beste_variante(kb, kb.leistungen["geburtsanzeige"], aufloesen(kb, plz="80331"), date(2026, 10, 24))
        assert v.id == "geburtsanzeige_by"
    finally:
        kb.varianten["geburtsanzeige_muenchen"] = alt


@pytest.mark.anforderung("ANF-DAT-03", "ANF-BY-03")
def test_abdeckung(plane):
    assert plane(familie()).eintrag("geburtsanzeige").abdeckung is Abdeckung.VOLLSTAENDIG
    assert plane(familie(), plz="85354").eintrag("geburtsanzeige").abdeckung is Abdeckung.ALLGEMEIN
    assert plane(familie(), plz=None, land="NW").eintrag("elterngeld").abdeckung is Abdeckung.ALLGEMEIN
    assert plane(familie()).eintrag("elterngeld").abdeckung is Abdeckung.VOLLSTAENDIG


@pytest.mark.anforderung("ANF-DAT-04")
def test_warnungen_ausserhalb_pilot(plane):
    assert plane(familie()).warnungen == []
    warnungen = plane(familie(), plz="10115", land="BE").warnungen
    assert any("kein Pilotland" in w for w in warnungen)
    assert any("nicht als Gemeinde erfasst" in w for w in warnungen)
    assert "bayerisches_familiengeld" not in plane(familie(), plz=None, land="BE").ergebnisse()


@pytest.mark.anforderung("ANF-DAT-05")
def test_quellen_und_pruefstatus(kb, plane):
    for e in plane(familie()).eintraege:
        assert e.quellen, e.leistung.id
    fg = plane(familie()).eintrag("bayerisches_familiengeld")
    assert fg.pruefstatus is Pruefstatus.WIDERSPRUECHLICH


@pytest.mark.anforderung("ANF-CHK-01")
def test_voraussetzungen_zuerst(plane):
    reihenfolge = [e.leistung.id for e in plane(familie()).eintraege]
    assert reihenfolge.index("geburtsanzeige") < reihenfolge.index("elterngeld")
    assert reihenfolge.index("geburtsanzeige") < reihenfolge.index("kindergeld")
    assert reihenfolge.index("kindergeld") < reihenfolge.index("kinderzuschlag")


@pytest.mark.anforderung("ANF-CHK-02")
def test_sortierung_nach_ergebnis_und_frist(plane):
    eintraege = plane(familie()).eintraege
    raenge = [{"ja": 0, "unklar": 1, "nein": 2}[e.ergebnis.value] for e in eintraege]
    # Abgesehen von Voraussetzungen ist die Reihenfolge Ja < Unklar < Nein
    assert raenge == sorted(raenge)
    ja = [e for e in eintraege if e.ergebnis is Wert.JA and e.naechste_frist]
    assert ja[0].naechste_frist == min(e.naechste_frist for e in ja)


@pytest.mark.anforderung("ANF-ENG-02", "ANF-ENG-03")
def test_rueckfragen(plane):
    leer = plane({})
    assert leer.fehlend[:2] == ["kind_geboren", "partner_im_haushalt"]
    assert "geburtsdatum_oder_termin" not in leer.fehlend  # abgeleitet, nicht direkt erfragt
    assert plane({"kind_geboren": "ja"}).fehlend[0] == "geburtsdatum"
    assert plane({"kind_geboren": "nein"}).fehlend[0] == "errechneter_termin"
    # Vollständige Familie: keine Rückfragen
    assert plane(familie()).fehlend == []
    # Alleinerziehend: keine Fragen zum anderen Elternteil
    allein = plane(familie(partner_im_haushalt="nein", eltern_verheiratet="nein", partner__beschaeftigt=None,
                          partner__staatsangehoerigkeit=None, partner__krankenversicherung=None,
                          partner__erwerbsstunden_nach_geburt=None, partner__betreut_kind_selbst=None))
    assert not [f for f in allein.fehlend if f.startswith("partner.")]


@pytest.mark.anforderung("ANF-ENG-03", "ANF-ENG-08")
def test_rueckfragen_je_elternteil(plane):
    """Auch wenn die Mutter schon Anspruch hat, wird der andere Elternteil weiter geprüft."""
    b = plane(familie(partner__erwerbsstunden_nach_geburt=None))
    assert b.eintrag("elterngeld").ergebnis is Wert.JA
    assert b.fehlend == ["partner.erwerbsstunden_nach_geburt"]


@pytest.mark.anforderung("ANF-ENG-04")
def test_weiss_nicht_im_planer(plane):
    b = plane(familie(zve_eltern="unbekannt"))
    assert b.eintrag("elterngeld").ergebnis is Wert.UNKLAR
    assert "zve_eltern" not in b.fehlend


@pytest.mark.anforderung("ANF-ENG-06")
def test_jede_entscheidung_hat_begruendung(plane):
    from buergerai.regeln import begruendung

    for e in plane(familie()).eintraege:
        for p in e.personen:
            for s in begruendung(p.schritt):
                assert s.text, (e.leistung.id, s)
