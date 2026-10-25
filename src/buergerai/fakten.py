"""Faktenkatalog: welche Angaben die Regeln brauchen und wie man danach fragt.

Gemeinsame Fakten liegen in ``data/kern/fakten.json``, die Fakten eines
Fachmoduls in ``data/fachmodule/<id>/fakten.json``. Fakten mit
``je_person: true`` gibt es einmal je Rolle (z. B. ``mutter.*`` und ``partner.*``).
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

# "ort": Postleitzahl (5 Ziffern) oder Gemeindeschlüssel (8 Ziffern), z. B. Lage einer Immobilie
TYPEN = ("ja_nein", "zahl", "datum", "auswahl", "text", "ort")
# Abgeleitete Vergleiche eines Ortsfakts mit dem Wohnort, z. B. "Umzug innerhalb derselben Gemeinde?"
ABLEITUNGEN = {"gleiche_gemeinde": "gemeinde", "gleicher_kreis": "kreis", "gleiches_land": "land"}


@dataclass(frozen=True)
class FaktDefinition:
    id: str  # bei je_person mit Präfix "person."
    typ: str
    frage: str
    hilfe: Optional[str] = None
    optionen: tuple[tuple[str, str], ...] = ()  # (wert, beschriftung)
    je_person: bool = False
    abgeleitet: bool = False
    nur_wenn: Optional[tuple[str, Any]] = None  # nur fragen, wenn Fakt == Wert
    modul: str = "kern"  # "kern" oder ID des Fachmoduls, aus dem Ablageort abgeleitet
    # (Art, Ortsfakt): Vergleich des Ortsfakts mit dem Wohnort, siehe ABLEITUNGEN
    ableitung: Optional[tuple[str, str]] = None

    def frage_fuer(self, wer: Optional[str]) -> str:
        """Frage mit eingesetzter Person (``wer`` im Satz, z. B. "die Mutter")."""
        if wer is None:
            return self.frage
        return self.frage.replace("{wer}", wer).replace("{Wer}", wer[:1].upper() + wer[1:])


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
    if typ == "ort":
        text = str(roh).strip()
        if not (text.isdigit() and len(text) in (5, 8)):
            raise EingabeFehler(
                f"{definition.id}: Postleitzahl (5 Ziffern) oder Gemeindeschlüssel (8 Ziffern) erwartet (war: {roh!r})"
            )
        return text
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


def einstiegs_rueckfragen(definitionen: list[FaktDefinition], fakten: dict[str, Any]) -> list[str]:
    """Einstiegsfragen (in dieser Reihenfolge), die noch fehlen, unter Beachtung von ``nur_wenn``."""
    offen: list[str] = []
    for d in definitionen:
        if d.id in fakten or d.id in offen:
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
