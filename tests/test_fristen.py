from datetime import date

import pytest

from buergerai.fristen import berechne, plus_monate
from buergerai.modell import Frist

STICHTAG = date(2026, 10, 24)


@pytest.mark.anforderung("ANF-FRI-02")
@pytest.mark.parametrize(
    "start,monate,ergebnis",
    [
        (date(2026, 1, 31), 1, date(2026, 2, 28)),
        (date(2024, 1, 31), 1, date(2024, 2, 29)),
        (date(2026, 11, 15), 3, date(2027, 2, 15)),
        (date(2026, 8, 31), 6, date(2027, 2, 28)),
        (date(2026, 3, 15), -3, date(2025, 12, 15)),
    ],
)
def test_plus_monate(start, monate, ergebnis):
    assert plus_monate(start, monate) == ergebnis


@pytest.mark.anforderung("ANF-FRI-01")
def test_frist_ab_geburt_und_termin():
    frist = Frist("eine Woche", bezug="geburt", tage=7)
    geboren = berechne(frist, {"kind_geboren": True, "geburtsdatum": date(2026, 10, 20)}, STICHTAG)
    assert geboren.datum == date(2026, 10, 27) and not geboren.voraussichtlich and geboren.tage_bis == 3
    erwartet = berechne(frist, {"kind_geboren": False, "errechneter_termin": date(2026, 12, 1)}, STICHTAG)
    assert erwartet.datum == date(2026, 12, 8) and erwartet.voraussichtlich
    assert berechne(frist, {}, STICHTAG).datum is None


@pytest.mark.anforderung("ANF-FRI-01")
def test_frist_vor_termin():
    frist = Frist("7 Wochen vorher", bezug="termin", art="fruehestens", wochen=-7)
    assert berechne(frist, {"errechneter_termin": date(2026, 12, 15)}, STICHTAG).datum == date(2026, 10, 27)


@pytest.mark.anforderung("ANF-FRI-03")
def test_abgelaufen():
    f = berechne(Frist("t", bezug="geburt", tage=7), {"kind_geboren": True, "geburtsdatum": date(2026, 10, 1)}, STICHTAG)
    assert f.abgelaufen
    # "frühestens ab"-Fristen laufen nicht ab
    f2 = berechne(Frist("t", bezug="geburt", art="fruehestens"), {"kind_geboren": True, "geburtsdatum": date(2026, 10, 1)}, STICHTAG)
    assert not f2.abgelaufen
