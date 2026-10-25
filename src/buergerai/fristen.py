"""Fristberechnung relativ zu Geburt, errechnetem Termin oder einem Datumsfakt."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Optional

from .modell import Frist


def plus_monate(tag: date, monate: int) -> date:
    """Addiert Kalendermonate; am Monatsende wird auf den letzten Tag gekürzt."""
    index = tag.month - 1 + monate
    jahr, monat = tag.year + index // 12, index % 12 + 1
    letzter = calendar.monthrange(jahr, monat)[1]
    return date(jahr, monat, min(tag.day, letzter))


@dataclass(frozen=True)
class BerechneteFrist:
    frist: Frist
    datum: Optional[date]
    voraussichtlich: bool  # Basis ist der errechnete Termin, nicht die Geburt
    tage_bis: Optional[int]

    @property
    def abgelaufen(self) -> bool:
        return self.frist.art != "fruehestens" and self.tage_bis is not None and self.tage_bis < 0


def berechne(frist: Frist, fakten: dict[str, Any], stichtag: date) -> BerechneteFrist:
    basis: Optional[date] = None
    voraussichtlich = False
    if frist.bezug == "geburt":
        if fakten.get("kind_geboren") is True and isinstance(fakten.get("geburtsdatum"), date):
            basis = fakten["geburtsdatum"]
        elif fakten.get("kind_geboren") is False and isinstance(fakten.get("errechneter_termin"), date):
            basis = fakten["errechneter_termin"]
            voraussichtlich = True
    elif frist.bezug == "termin":
        if isinstance(fakten.get("errechneter_termin"), date):
            basis = fakten["errechneter_termin"]
    elif frist.bezug != "keiner" and isinstance(fakten.get(frist.bezug), date):
        basis = fakten[frist.bezug]  # beliebiger Datumsfakt, z. B. Einzugsdatum
    if basis is None:
        return BerechneteFrist(frist, None, False, None)
    datum = plus_monate(basis, frist.monate) + timedelta(weeks=frist.wochen, days=frist.tage)
    return BerechneteFrist(frist, datum, voraussichtlich, (datum - stichtag).days)
