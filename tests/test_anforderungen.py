import pytest

from buergerai import anforderungen


@pytest.mark.anforderung("ANF-QS-01")
def test_jede_anforderung_hat_tests():
    ohne = [a.id for a in anforderungen.testmatrix() if not a.tests]
    assert ohne == []


@pytest.mark.anforderung("ANF-QS-01")
def test_keine_verweise_auf_unbekannte_anforderungen():
    assert anforderungen.unbekannte_verweise() == []


def test_ids_eindeutig():
    ids = [a.id for a in anforderungen.laden()]
    assert len(ids) == len(set(ids))
