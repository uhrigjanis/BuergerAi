import pytest

from buergerai import szenarien
from buergerai.planer import planen

ALLE = sorted(p.stem for p in szenarien.SZENARIO_VERZEICHNIS.glob("*.json"))


@pytest.mark.anforderung("ANF-CLI-03")
@pytest.mark.parametrize("name", ALLE)
def test_szenario_erwartungen(kb, name):
    s = szenarien.finden(kb, name)
    assert s.erwartet, "Szenario braucht Erwartungen"
    bericht = planen(kb, s.anfrage)
    ist = bericht.ergebnisse()
    abweichungen = {l: (w, ist.get(l)) for l, w in s.erwartet.items() if ist.get(l) != w}
    assert not abweichungen
    if s.erwartet_fehlend is not None:
        assert bericht.fehlend == s.erwartet_fehlend


@pytest.mark.anforderung("ANF-CLI-03")
def test_speichern_und_laden(kb, tmp_path):
    s = szenarien.finden(kb, "freising_unverheiratet_privat")
    ziel = tmp_path / "kopie.json"
    szenarien.speichern(ziel, s.anfrage, "Kopie")
    wieder = szenarien.laden(kb, ziel)
    assert wieder.anfrage.fakten == s.anfrage.fakten
    assert planen(kb, wieder.anfrage).ergebnisse() == planen(kb, s.anfrage).ergebnisse()
