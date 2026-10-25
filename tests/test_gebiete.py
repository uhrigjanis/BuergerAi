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
    # Künstliche Gemeinden im ungenutzten PLZ-Bereich 00xxx: eine mit Präfix 009, eine mit exakter PLZ 00998
    test_kb = Wissensbasis(gebiete=dict(kb.gebiete))
    test_kb.gebiete["09999990"] = Gebiet("09999990", "Präfixstadt", Ebene.GEMEINDE, "09178", plz_praefixe=("009",))
    test_kb.gebiete["09999999"] = Gebiet("09999999", "Testdorf", Ebene.GEMEINDE, "09178", plz=("00998",))
    assert gebiete.aufloesen(test_kb, plz="00998")[0].name == "Testdorf"
    assert gebiete.aufloesen(test_kb, plz="00997")[0].name == "Präfixstadt"


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
    # 80001: Postfach-PLZ in München, keiner Gemeinde zugeordnet
    with pytest.raises(gebiete.PlzUnbekannt, match="Bundesland"):
        gebiete.aufloesen(kb, plz="80001")
    assert [g.id for g in gebiete.aufloesen(kb, plz="80001", land="BY")] == ["09", "DE"]
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


# ------------------------------------------------------------- bundesweit (#40)
@pytest.mark.anforderung("ANF-GEB-06")
def test_jede_importierte_plz_fuehrt_zu_gemeinde(kb):
    """Keine PLZ aus den Importdaten landet in der Rückfrage nach dem Bundesland."""
    index = kb.plz_index()
    assert len(index) > 8000
    for plz, ids in index.items():
        try:
            kette = gebiete.aufloesen(kb, plz=plz)
            assert kette[0].ebene is Ebene.GEMEINDE and len(ids) == 1
        except gebiete.PlzMehrdeutig as exc:
            assert len(exc.gemeinden) == len(ids) > 1
            kette = gebiete.aufloesen(kb, plz=plz, gemeinde_id=exc.gemeinden[-1].id)
        assert [g.ebene for g in kette] == [Ebene.GEMEINDE, Ebene.KREIS, Ebene.LAND, Ebene.BUND], plz


@pytest.mark.anforderung("ANF-GEB-06")
@pytest.mark.parametrize(
    "plz,gemeinde,kreis,land",
    [
        ("24103", "Kiel", "Kreisfreie Stadt Kiel", "SH"),
        ("20095", "Hamburg", "Kreisfreie Stadt Hamburg", "HH"),
        ("30159", "Hannover", "Region Hannover", "NI"),
        ("28195", "Bremen", "Kreisfreie Stadt Bremen", "HB"),
        ("50667", "Köln", "Kreisfreie Stadt Köln", "NW"),
        ("34225", "Baunatal", "Landkreis Kassel", "HE"),
        ("55116", "Mainz", "Kreisfreie Stadt Mainz", "RP"),
        ("70173", "Stuttgart", "Stadtkreis Stuttgart", "BW"),
        ("80331", "München", "Kreisfreie Stadt München", "BY"),
        ("66111", "Saarbrücken", "Regionalverband Saarbrücken", "SL"),
        ("10115", "Berlin", "Kreisfreie Stadt Berlin", "BE"),
        ("14467", "Potsdam", "Kreisfreie Stadt Potsdam", "BB"),
        ("18055", "Rostock", "Kreisfreie Stadt Rostock", "MV"),
        ("01067", "Dresden", "Kreisfreie Stadt Dresden", "SN"),
        ("39104", "Magdeburg", "Kreisfreie Stadt Magdeburg", "ST"),
        ("99084", "Erfurt", "Kreisfreie Stadt Erfurt", "TH"),
    ],
)
def test_beispielorte_aller_laender(kb, plz, gemeinde, kreis, land):
    g, k, l, _ = gebiete.aufloesen(kb, plz=plz)
    assert (g.name, k.name, l.kuerzel) == (gemeinde, kreis, land)


@pytest.mark.anforderung("ANF-GEB-07")
def test_mehrdeutige_plz_bundesweit_mit_kreis(kb):
    # 85356 (Flughafen München) liegt in drei Gemeinden zweier Landkreise
    with pytest.raises(gebiete.PlzMehrdeutig) as info:
        gebiete.aufloesen(kb, plz="85356")
    namen = [g.name for g in info.value.gemeinden]
    assert namen == sorted(namen) == ["Freising", "Hallbergmoos", "Oberding"]
    assert {gebiete.kreis_von(kb, g).name for g in info.value.gemeinden} == {"Landkreis Freising", "Landkreis Erding"}


def test_kreise_und_gemeinden_vollstaendig(kb):
    kreise = [g for g in kb.gebiete.values() if g.ebene is Ebene.KREIS]
    gemeinden = [g for g in kb.gebiete.values() if g.ebene is Ebene.GEMEINDE]
    assert len(kreise) == 400
    assert len(gemeinden) > 10_000
    assert all(k.art for k in kreise)
    assert {g.parent_id[:2] for g in gemeinden} == {l.id for l in gebiete.laender(kb)}
