import pytest

from buergerai import szenarien
from buergerai.planer import planen

ALLE = sorted(p.stem for p in szenarien.SZENARIO_VERZEICHNIS.glob("*.json"))


@pytest.mark.anforderung("ANF-CLI-03")
@pytest.mark.parametrize("name", ALLE)
def test_szenario_erwartungen(kb, name):
    s = szenarien.finden(kb, name)
    assert s.erwartet, "Szenario braucht Erwartungen"
    assert szenarien.abweichungen(s, planen(kb, s.anfrage)) == []


@pytest.mark.anforderung("ANF-CLI-03", "ANF-LAND-04")
def test_abweichende_stelle_wird_gemeldet(kb):
    from dataclasses import replace

    s = szenarien.finden(kb, "muenchen_verheiratet_angestellt")
    falsch = replace(s, erwartet_stellen={"elterngeld": "L-Bank"}, erwartet={"elterngeld": "nein"})
    meldungen = szenarien.abweichungen(falsch, planen(kb, s.anfrage))
    assert any("elterngeld: erwartet nein" in m for m in meldungen)
    assert any("'L-Bank'" in m and "ZBFS" in m for m in meldungen)


@pytest.mark.anforderung("ANF-CLI-03")
def test_speichern_und_laden(kb, tmp_path):
    s = szenarien.finden(kb, "freising_unverheiratet_privat")
    ziel = tmp_path / "kopie.json"
    szenarien.speichern(ziel, s.anfrage, "Kopie")
    wieder = szenarien.laden(kb, ziel)
    assert wieder.anfrage.fakten == s.anfrage.fakten
    assert planen(kb, wieder.anfrage).ergebnisse() == planen(kb, s.anfrage).ergebnisse()
