"""CI als Pflicht-Check (#69): Zusammenfassung der Testläufe und stabiler Workflow."""

import importlib.util
import re
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
WORKFLOW = WURZEL / ".github" / "workflows" / "tests.yml"

_spec = importlib.util.spec_from_file_location("pytest_zusammenfassung", WURZEL / "scripts" / "pytest_zusammenfassung.py")
zf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(zf)

GRUEN = """\
........................................................................ [ 50%]
........................................................................ [100%]
============================= slowest 10 durations =============================
4.12s call     tests/test_performance.py::test_zielgroesse_laden_und_planen
1.03s setup    tests/test_web.py::test_server
499 passed in 138.26s (0:02:18)
"""

ROT = """\
.....F..                                                                 [100%]
=================================== FAILURES ===================================
___________________________________ test_x _____________________________________
E   assert 1 == 2
============================= slowest 10 durations =============================
0.50s call     tests/test_a.py::test_x
=========================== short test summary info ============================
FAILED tests/test_a.py::test_x - assert 1 == 2
1 failed, 7 passed in 1.20s
"""


@pytest.mark.anforderung("ANF-QS-08")
def test_zusammenfassung_gruen():
    text = zf.zusammenfassung(GRUEN, "Python 3.13")
    assert text.startswith("### Tests (Python 3.13): ✅ 499 passed in 138.26s")
    assert "test_performance.py::test_zielgroesse_laden_und_planen" in text
    assert "Fehlgeschlagen" not in text
    langsam = text[text.index("Langsamste"):]
    assert "passed" not in langsam, "mit -q steht die Ergebniszeile ohne Trenner direkt nach den Laufzeiten"


@pytest.mark.anforderung("ANF-QS-08")
def test_zusammenfassung_rot_nennt_fehlschlaege():
    text = zf.zusammenfassung(ROT, "Python 3.10")
    assert "❌ 1 failed, 7 passed in 1.20s" in text
    assert "FAILED tests/test_a.py::test_x - assert 1 == 2" in text
    assert "E   assert" not in text, "nur die Kurzliste, nicht die ganze Fehlerausgabe"


@pytest.mark.anforderung("ANF-QS-08")
def test_zusammenfassung_ohne_ergebnis_ist_rot():
    text = zf.zusammenfassung("ImportError: cannot import name 'x'\n", "Python 3.10")
    assert "❌" in text and "kein Ergebnis" in text


@pytest.mark.anforderung("ANF-QS-08")
def test_zusammenfassung_ergebniszeile_mit_trennern():
    """pytest ohne -q setzt die Ergebniszeile zwischen Gleichheitszeichen."""
    log = "========================= 3 passed, 1 skipped in 0.10s =========================\n"
    assert "✅ 3 passed, 1 skipped in 0.10s" in zf.zusammenfassung(log, "x")


@pytest.mark.anforderung("ANF-QS-09")
def test_workflow_laeuft_bei_jedem_pr_ohne_pfadfilter():
    text = WORKFLOW.read_text(encoding="utf-8")
    ausloeser = text[text.index("\non:"):text.index("\npermissions:")]
    assert re.search(r"^  pull_request:\s*$", ausloeser, re.M)
    assert "paths" not in ausloeser, "ein Pfadfilter ließe Pflicht-Checks ewig warten"


@pytest.mark.anforderung("ANF-QS-09")
def test_workflow_jobname_stabil():
    """Die Pflicht-Checks im Ruleset heißen „tests (3.10)“ und „tests (3.13)“."""
    text = WORKFLOW.read_text(encoding="utf-8")
    jobs = re.findall(r"^  (\w[\w-]*):\s*$", text[text.index("\njobs:"):], re.M)
    assert jobs == ["tests"]
    assert re.search(r'python: \["3\.10", "3\.13"\]', text)
    assert "\n    name:" not in text, "ein eigener Job-Name würde die Check-Namen ändern"


@pytest.mark.anforderung("ANF-QS-09")
def test_workflow_prueft_alles():
    text = WORKFLOW.read_text(encoding="utf-8")
    for befehl in ("./bai --keine-farbe daten", "szenarien --pruefen", "./bai --keine-farbe anforderungen",
                   "python -m pyflakes src tests scripts", "python -m pytest", "set -o pipefail"):
        assert befehl in text, befehl
