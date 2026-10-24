"""Deterministische Regel-Engine mit dreiwertiger Logik (Ja / Nein / Unklar).

Regeln sind verschachtelte JSON-Objekte. Knotentypen:

``{"alle": [...]}``
    Und-Verknüpfung. Nein, sobald ein Teil Nein ist. Leere Liste = Ja.
``{"eine": [...]}``
    Oder-Verknüpfung. Ja, sobald ein Teil Ja ist.
``{"nicht": {...}, "text": "..."}``
    Verneinung (Ja <-> Nein, Unklar bleibt Unklar). Braucht einen eigenen Text.
``{"fakt": "id", "op": "<=", "wert": 32, "text": "...", "quellen": [...]}``
    Vergleich eines Fakts aus dem Profil. Fehlt der Fakt, ist das Ergebnis
    Unklar und der Fakt wird als Rückfrage gemeldet.
``{"pruefung_noetig": "...", "quellen": [...]}``
    Ist immer Unklar. Für Voraussetzungen, die sich nicht sicher regelbasiert
    entscheiden lassen (z. B. Aufenthaltstitel). Die Engine erfindet nie ein Ja.

Fakten mit dem Präfix ``person.`` werden je Elternteil aufgelöst
(``person.beschaeftigt`` -> ``mutter.beschaeftigt`` bzw. ``partner.beschaeftigt``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Iterable, Optional

from .fakten import UNBEKANNT


class Wert(Enum):
    JA = "ja"
    NEIN = "nein"
    UNKLAR = "unklar"


OPERATOREN = ("==", "!=", "<", "<=", ">", ">=", "in", "nicht_in")
KNOTENTYPEN = ("alle", "eine", "nicht", "fakt", "pruefung_noetig")


@dataclass
class Schritt:
    """Ergebnis eines Regelknotens inklusive Begründungsbaum."""

    art: str
    wert: Wert
    text: Optional[str] = None
    fakt: Optional[str] = None
    ist: Any = None
    quellen: tuple[str, ...] = ()
    kinder: list["Schritt"] = field(default_factory=list)
    # Fakten, deren Angabe das Ergebnis entscheiden könnte (nur bei UNKLAR)
    fehlend: list[str] = field(default_factory=list)


class RegelFehler(ValueError):
    pass


def knotentyp(knoten: dict[str, Any]) -> str:
    typen = [t for t in KNOTENTYPEN if t in knoten]
    if len(typen) != 1:
        raise RegelFehler(f"Regelknoten braucht genau einen Typ aus {KNOTENTYPEN}: {knoten}")
    return typen[0]


def fakt_id(roh: str, person: Optional[str]) -> str:
    if roh.startswith("person."):
        if person is None:
            raise RegelFehler(f"Fakt {roh} braucht eine Person (Leistung 'jeder_elternteil')")
        return person + "." + roh[len("person.") :]
    return roh


def _vergleiche(ist: Any, op: str, soll: Any) -> bool:
    if isinstance(ist, date):
        if isinstance(soll, str):
            soll = date.fromisoformat(soll)
        elif isinstance(soll, list):
            soll = [date.fromisoformat(s) for s in soll]
    if op == "==":
        return ist == soll
    if op == "!=":
        return ist != soll
    if op == "<":
        return ist < soll
    if op == "<=":
        return ist <= soll
    if op == ">":
        return ist > soll
    if op == ">=":
        return ist >= soll
    if op == "in":
        return ist in soll
    if op == "nicht_in":
        return ist not in soll
    raise RegelFehler(f"Unbekannter Operator: {op}")


def _eindeutig(werte: Iterable[str]) -> list[str]:
    gesehen: list[str] = []
    for w in werte:
        if w not in gesehen:
            gesehen.append(w)
    return gesehen


def auswerten(knoten: dict[str, Any], fakten: dict[str, Any], person: Optional[str] = None) -> Schritt:
    typ = knotentyp(knoten)
    text = knoten.get("text")
    quellen = tuple(knoten.get("quellen", ()))

    if typ == "fakt":
        fid = fakt_id(knoten["fakt"], person)
        if fid not in fakten:
            return Schritt("fakt", Wert.UNKLAR, text, fid, None, quellen, fehlend=[fid])
        ist = fakten[fid]
        if ist is UNBEKANNT:
            return Schritt("fakt", Wert.UNKLAR, text, fid, ist, quellen)
        try:
            ok = _vergleiche(ist, knoten["op"], knoten.get("wert"))
        except TypeError as exc:
            raise RegelFehler(f"Typfehler bei Fakt {fid}={ist!r}: {exc}") from exc
        return Schritt("fakt", Wert.JA if ok else Wert.NEIN, text, fid, ist, quellen)

    if typ == "pruefung_noetig":
        return Schritt("pruefung_noetig", Wert.UNKLAR, knoten["pruefung_noetig"], quellen=quellen)

    if typ == "nicht":
        kind = auswerten(knoten["nicht"], fakten, person)
        wert = {Wert.JA: Wert.NEIN, Wert.NEIN: Wert.JA, Wert.UNKLAR: Wert.UNKLAR}[kind.wert]
        return Schritt("nicht", wert, text, quellen=quellen, kinder=[kind], fehlend=list(kind.fehlend))

    kinder = [auswerten(k, fakten, person) for k in knoten[typ]]
    werte = {k.wert for k in kinder}
    if typ == "alle":
        if Wert.NEIN in werte:
            wert = Wert.NEIN
        elif Wert.UNKLAR in werte:
            wert = Wert.UNKLAR
        else:
            wert = Wert.JA
    else:  # eine
        if Wert.JA in werte:
            wert = Wert.JA
        elif Wert.UNKLAR in werte:
            wert = Wert.UNKLAR
        else:
            wert = Wert.NEIN
    # Rückfragen nur, wenn sie das Ergebnis noch ändern können
    fehlend: list[str] = []
    if wert is Wert.UNKLAR:
        fehlend = _eindeutig(f for k in kinder if k.wert is Wert.UNKLAR for f in k.fehlend)
    return Schritt(typ, wert, text, quellen=quellen, kinder=kinder, fehlend=fehlend)


def begruendung(schritt: Schritt) -> list[Schritt]:
    """Liefert die Blatt-Schritte, die das Gesamtergebnis erklären (ohne Dubletten)."""
    ergebnis: list[Schritt] = []
    gesehen: set[tuple] = set()
    for s in _begruendung(schritt):
        schluessel = (s.art, s.text, s.fakt, s.wert)
        if schluessel not in gesehen:
            gesehen.add(schluessel)
            ergebnis.append(s)
    return ergebnis


def _begruendung(schritt: Schritt) -> list[Schritt]:
    if schritt.art in ("fakt", "pruefung_noetig") or (schritt.art == "nicht" and schritt.text):
        return [schritt]
    if schritt.art == "nicht":
        return _begruendung(schritt.kinder[0])
    relevante: list[Schritt]
    if schritt.wert is Wert.JA:
        if schritt.art == "alle":
            relevante = schritt.kinder
        else:
            relevante = [next(k for k in schritt.kinder if k.wert is Wert.JA)]
    elif schritt.wert is Wert.NEIN:
        relevante = [k for k in schritt.kinder if k.wert is Wert.NEIN] if schritt.art == "alle" else schritt.kinder
    else:
        relevante = [k for k in schritt.kinder if k.wert is Wert.UNKLAR]
    ergebnis: list[Schritt] = []
    for k in relevante:
        ergebnis.extend(_begruendung(k))
    return ergebnis


def fakten_in_regel(knoten: dict[str, Any]) -> list[str]:
    """Alle Fakt-IDs (unaufgelöst, also ggf. mit ``person.``) einer Regel."""
    typ = knotentyp(knoten)
    if typ == "fakt":
        return [knoten["fakt"]]
    if typ == "pruefung_noetig":
        return []
    if typ == "nicht":
        return fakten_in_regel(knoten["nicht"])
    return _eindeutig(f for k in knoten[typ] for f in fakten_in_regel(k))


def quellen_in_regel(knoten: dict[str, Any]) -> list[str]:
    typ = knotentyp(knoten)
    eigene = list(knoten.get("quellen", ()))
    if typ in ("fakt", "pruefung_noetig"):
        return eigene
    if typ == "nicht":
        return _eindeutig(eigene + quellen_in_regel(knoten["nicht"]))
    return _eindeutig(eigene + [q for k in knoten[typ] for q in quellen_in_regel(k)])
