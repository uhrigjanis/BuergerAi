import pytest

from buergerai import gebiete
from buergerai.modell import Ebene, Gebiet
from buergerai.wissensbasis import Wissensbasis


@pytest.mark.anforderung("ANF-GEB-01")
def test_muenchen_hierarchie(kb):
    kette = gebiete.aufloesen(kb, plz="80331")
    assert [g.id for g in kette] == ["09162000", "09162", "09", "DE"]
    assert [g.ebene for g in kette] == [Ebene.GEMEINDE, Ebene.KREIS, Ebene.LAND, Ebene.BUND]


@pytest.mark.anforderung("ANF-GEB-01")
def test_freising_hierarchie(kb):
    assert [g.id for g in gebiete.aufloesen(kb, plz="85354")] == ["09178124", "09178", "09", "DE"]


@pytest.mark.anforderung("ANF-GEB-02")
def test_exakte_plz_vor_praefix(kb):
    # Künstliche Gemeinde mit exakter PLZ 80999 neben München (Präfix 80)
    test_kb = Wissensbasis(gebiete=dict(kb.gebiete))
    test_kb.gebiete["09999999"] = Gebiet("09999999", "Testdorf", Ebene.GEMEINDE, "09178", plz=("80999",))
    assert gebiete.aufloesen(test_kb, plz="80999")[0].name == "Testdorf"
    assert gebiete.aufloesen(test_kb, plz="80998")[0].name == "München"


@pytest.mark.anforderung("ANF-GEB-03")
def test_mehrdeutige_plz(kb):
    test_kb = Wissensbasis(gebiete=dict(kb.gebiete))
    test_kb.gebiete["09999998"] = Gebiet("09999998", "Nachbarort", Ebene.GEMEINDE, "09178", plz=("85354",))
    with pytest.raises(gebiete.PlzMehrdeutig) as info:
        gebiete.aufloesen(test_kb, plz="85354")
    assert {g.name for g in info.value.gemeinden} == {"Freising", "Nachbarort"}
    # Auflösung über die gewählte Gemeinde
    assert gebiete.aufloesen(test_kb, plz="85354", gemeinde_id="09999998")[0].name == "Nachbarort"


@pytest.mark.anforderung("ANF-GEB-04")
def test_unbekannte_plz_braucht_land(kb):
    with pytest.raises(gebiete.PlzUnbekannt, match="Bundesland"):
        gebiete.aufloesen(kb, plz="10115")
    assert [g.id for g in gebiete.aufloesen(kb, plz="10115", land="BE")] == ["11", "DE"]
    assert [g.id for g in gebiete.aufloesen(kb, land="by")] == ["09", "DE"]


@pytest.mark.anforderung("ANF-GEB-05")
@pytest.mark.parametrize("plz", ["8033", "803311", "8O331", ""])
def test_ungueltige_plz(kb, plz):
    with pytest.raises(gebiete.GebietFehler):
        gebiete.aufloesen(kb, plz=plz or None)


@pytest.mark.anforderung("ANF-GEB-04")
def test_unbekanntes_land(kb):
    with pytest.raises(gebiete.GebietFehler, match="Bundesland"):
        gebiete.aufloesen(kb, land="XX")


def test_alle_16_laender(kb):
    assert len(gebiete.laender(kb)) == 16
