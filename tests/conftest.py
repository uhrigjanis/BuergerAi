from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from buergerai.planer import Anfrage, Bericht, planen
from buergerai.szenarien import fakten_parsen
from buergerai.wissensbasis import Wissensbasis

STICHTAG = date(2026, 10, 24)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "anforderung(*ids): Test deckt Anforderung(en) aus docs/anforderungen.json ab")


@pytest.fixture(scope="session")
def kb() -> Wissensbasis:
    return Wissensbasis.laden()


def familie(**abweichungen: Any) -> dict[str, Any]:
    """Vollständig beschriebene Familie (verheiratet, beide angestellt, GKV)."""
    fakten: dict[str, Any] = {
        "kind_geboren": "nein",
        "errechneter_termin": "2026-12-15",
        "partner_im_haushalt": "ja",
        "eltern_verheiratet": "ja",
        "kind_lebt_im_haushalt": "ja",
        "zve_eltern": 90000,
        "brutto_haushalt_monat": 7000,
        "mutter.staatsangehoerigkeit": "deutsch",
        "mutter.krankenversicherung": "gesetzlich_mitglied",
        "mutter.beschaeftigt": "ja",
        "mutter.erwerbsstunden_nach_geburt": 0,
        "mutter.betreut_kind_selbst": "ja",
        "partner.staatsangehoerigkeit": "deutsch",
        "partner.krankenversicherung": "gesetzlich_mitglied",
        "partner.beschaeftigt": "ja",
        "partner.erwerbsstunden_nach_geburt": 0,
        "partner.betreut_kind_selbst": "ja",
    }
    for k, v in abweichungen.items():
        k = k.replace("__", ".")
        if v is None:
            fakten.pop(k, None)
        else:
            fakten[k] = v
    return fakten


@pytest.fixture
def plane(kb: Wissensbasis):
    def _plane(fakten: dict[str, Any] | None = None, plz: str | None = "80331", land: str | None = None,
               stichtag: date = STICHTAG, gemeinde: str | None = None) -> Bericht:
        anfrage = Anfrage(fakten=fakten_parsen(kb, fakten or {}), plz=plz, land=land,
                          gemeinde=gemeinde, stichtag=stichtag)
        return planen(kb, anfrage)

    return _plane
