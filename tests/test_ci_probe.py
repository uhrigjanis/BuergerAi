"""Absichtlich roter Test für die Probe des Pflicht-Checks (#69).

Dieser PR wird nicht gemergt. Er zeigt nur, dass GitHub den Merge blockiert,
solange „tests (3.10)“ und „tests (3.13)“ rot sind.
"""


def test_pflicht_check_blockiert_merge():
    assert False, "Absichtlich rot: Probe für den Pflicht-Check (#69)"
