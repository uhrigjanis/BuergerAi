"""Faktenkatalog: welche Angaben die Regeln brauchen und wie man danach fragt.

Der Katalog liegt in ``data/fakten.json``. Fakten mit ``je_person: true`` gibt es
einmal je Elternteil (``mutter.*`` und ``partner.*``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Optional


class _Unbekannt:
    """Markiert eine Angabe, die die Person ausdrücklich nicht weiß."""

    _instanz: Optional["_Unbekannt"] = None

    def __new__(cls) -> "_Unbekannt":
        if cls._instanz is None:
            cls._instanz = super().__new__(cls)
        return cls._instanz

    def __repr__(self) -> str:
        return "unbekannt"


UNBEKANNT = _Unbekannt()

PERSONEN = {
    "mutter": ("die Mutter (gebärende Person)", "Die Mutter (gebärende Person)"),
    "partner": ("der andere Elternteil", "Der andere Elternteil"),
}

TYPEN = ("ja_nein", "zahl", "datum", "auswahl", "text")


@dataclass(frozen=True)
class FaktDefinition:
    id: str  # bei je_person mit Präfix "person."
    typ: str
    frage: str
    hilfe: Optional[str] = None
    optionen: tuple[tuple[str, str], ...] = ()  # (wert, beschriftung)
    je_person: bool = False
    abgeleitet: bool = False
    grunddaten: bool = False  # wird immer zuerst erfragt
    nur_wenn: Optional[tuple[str, Any]] = None  # nur fragen, wenn Fakt == Wert

    def frage_fuer(self, person: Optional[str]) -> str:
        if person is None:
            return self.frage
        klein, gross = PERSONEN[person]
        return self.frage.replace("{wer}", klein).replace("{Wer}", gross)


class EingabeFehler(ValueError):
    pass


JA_WERTE = {"ja", "j", "true", "1", "yes", "y"}
NEIN_WERTE = {"nein", "n", "false", "0", "no"}
UNBEKANNT_WERTE = {"unbekannt", "?", "weiss nicht", "weiß nicht", "wn"}


def parse_wert(definition: FaktDefinition, roh: Any) -> Any:
    """Wandelt eine Eingabe (Text oder JSON-Wert) in den passenden Typ."""
    if roh is UNBEKANNT:
        return UNBEKANNT
    if isinstance(roh, str) and roh.strip().lower() in UNBEKANNT_WERTE:
        return UNBEKANNT
    typ = definition.typ
    if typ == "ja_nein":
        if isinstance(roh, bool):
            return roh
        text = str(roh).strip().lower()
        if text in JA_WERTE:
            return True
        if text in NEIN_WERTE:
            return False
        raise EingabeFehler(f"{definition.id}: bitte 'ja' oder 'nein' angeben (war: {roh!r})")
    if typ == "zahl":
        if isinstance(roh, bool):
            raise EingabeFehler(f"{definition.id}: Zahl erwartet (war: {roh!r})")
        if isinstance(roh, (int, float)):
            return roh
        text = str(roh).strip().replace(".", "").replace(" ", "").replace("€", "").replace(",", ".")
        try:
            zahl = float(text)
        except ValueError as exc:
            raise EingabeFehler(f"{definition.id}: Zahl erwartet (war: {roh!r})") from exc
        return int(zahl) if zahl.is_integer() else zahl
    if typ == "datum":
        if isinstance(roh, date):
            return roh
        text = str(roh).strip()
        try:
            if "." in text:
                tag, monat, jahr = text.split(".")
                return date(int(jahr), int(monat), int(tag))
            return date.fromisoformat(text)
        except ValueError as exc:
            raise EingabeFehler(
                f"{definition.id}: Datum als TT.MM.JJJJ oder JJJJ-MM-TT erwartet (war: {roh!r})"
            ) from exc
    if typ == "auswahl":
        werte = [w for w, _ in definition.optionen]
        text = str(roh).strip()
        if text in werte:
            return text
        if text.isdigit() and 1 <= int(text) <= len(werte):
            return werte[int(text) - 1]
        raise EingabeFehler(f"{definition.id}: erlaubt sind {', '.join(werte)} (war: {roh!r})")
    return str(roh)


def wert_als_text(wert: Any) -> str:
    if wert is UNBEKANNT:
        return "unbekannt"
    if isinstance(wert, bool):
        return "ja" if wert else "nein"
    if isinstance(wert, date):
        return wert.strftime("%d.%m.%Y")
    if isinstance(wert, (int, float)):
        return f"{wert:,}".replace(",", ".")
    return str(wert)


def grund_rueckfragen(definitionen: list[FaktDefinition], fakten: dict[str, Any]) -> list[str]:
    """Grunddaten, die noch fehlen (unter Beachtung von ``nur_wenn``)."""
    offen: list[str] = []
    for d in definitionen:
        if not d.grunddaten or d.id in fakten:
            continue
        if d.nur_wenn is not None and fakten.get(d.nur_wenn[0]) != d.nur_wenn[1]:
            continue
        offen.append(d.id)
    return offen


def abgeleitete_fakten(fakten: dict[str, Any]) -> dict[str, Any]:
    """Berechnet Fakten, die sich aus anderen Angaben ergeben."""
    neu: dict[str, Any] = {}
    geboren = fakten.get("kind_geboren")
    if geboren is True and isinstance(fakten.get("geburtsdatum"), date):
        neu["geburtsdatum_oder_termin"] = fakten["geburtsdatum"]
    elif geboren is False and isinstance(fakten.get("errechneter_termin"), date):
        neu["geburtsdatum_oder_termin"] = fakten["errechneter_termin"]
    return neu
