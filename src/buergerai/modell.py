"""Datenmodell v2: Gebietshierarchie, Leistungen, Leistungsvarianten, Quellen.

Alle Objekte sind unveränderlich (frozen) und werden aus den JSON-Dateien unter
``data/`` geladen (siehe ``wissensbasis.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Optional


class Ebene(Enum):
    """Verwaltungsebene. Der Rang gibt an, wie spezifisch eine Ebene ist."""

    BUND = "bund"
    LAND = "land"
    KREIS = "kreis"
    GEMEINDE = "gemeinde"

    @property
    def rang(self) -> int:
        return {"bund": 0, "land": 1, "kreis": 2, "gemeinde": 3}[self.value]


class Abdeckung(Enum):
    """Wie spezifisch sind die Daten für einen Ort? (ADR 0004, ADR 0007)

    Je Leistung (berechnet im Planer):

    - ERFASST: Es gibt eine Variante auf der Ebene, auf der die Leistung
      tatsächlich verwaltet wird (z. B. Standesamt der Gemeinde, Elterngeldstelle
      des Landes).
    - ALLGEMEIN: Es gibt nur eine allgemeinere Variante (z. B. Bundes- statt
      Gemeindedaten). Die Aussage stimmt grundsätzlich, die Stelle vor Ort fehlt.

    Je Land und Lebensereignis (aus ``abdeckung`` in den Daten):

    - ERFASST: Landesleistungen sind recherchiert (oder ausdrücklich "keine").
    - FEHLT: Für das Land ist noch nicht recherchiert, ob es eigene Leistungen gibt.
    """

    ERFASST = "erfasst"
    ALLGEMEIN = "allgemein"
    FEHLT = "fehlt"


class Pruefstatus(Enum):
    """Wie gut ist eine Quelle/Angabe gegen Primärquellen geprüft?

    - VERIFIZIERT: Ein Mensch hat die Angabe im Volltext der Primärquelle
      (Gesetz, Behördenseite, offizieller Rechner) geprüft.
    - TEILWEISE: Kernaussagen wurden abgeglichen (z. B. über Suchergebnisse
      oder Sekundärquellen), der Volltext der Primärquelle aber nicht gelesen.
    - UNGEPRUEFT: Noch nicht geprüft.
    - WIDERSPRUECHLICH: Quellen widersprechen sich; die Engine gibt dann
      bewusst "unklar" aus.
    """

    VERIFIZIERT = "verifiziert"
    TEILWEISE = "teilweise"
    UNGEPRUEFT = "ungeprueft"
    WIDERSPRUECHLICH = "widerspruechlich"


def parse_datum(wert: Optional[str]) -> Optional[date]:
    if wert is None:
        return None
    return date.fromisoformat(wert)


@dataclass(frozen=True)
class Zeitraum:
    gueltig_ab: Optional[date] = None
    gueltig_bis: Optional[date] = None

    def enthaelt(self, tag: date) -> bool:
        if self.gueltig_ab and tag < self.gueltig_ab:
            return False
        if self.gueltig_bis and tag > self.gueltig_bis:
            return False
        return True


@dataclass(frozen=True)
class Gebiet:
    id: str  # Amtlicher Schlüssel (AGS bzw. Kreis-/Landesschlüssel), "DE" für den Bund
    name: str
    ebene: Ebene
    parent_id: Optional[str]
    plz: tuple[str, ...] = ()
    plz_praefixe: tuple[str, ...] = ()
    kuerzel: Optional[str] = None  # z. B. "BY" für Länder
    quellen: tuple[str, ...] = ()
    art: Optional[str] = None  # bei Kreisen: Landkreis, Kreisfreie Stadt, ...
    verband: Optional[tuple[str, str]] = None  # Gemeindeverband (Schlüssel, Name), falls bekannt


@dataclass(frozen=True)
class Landesabdeckung:
    """Nachweis, dass die Landesleistungen eines Landes für ein Ereignis recherchiert sind.

    ``landesleistungen``: ``erfasst`` (eigene Leistungen sind als Varianten
    hinterlegt) oder ``keine`` (recherchiert: das Land hat keine eigenen).
    """

    gebiet_id: str
    ereignis: str
    landesleistungen: str
    stand: date
    quellen: tuple[str, ...]
    notiz: Optional[str] = None


@dataclass(frozen=True)
class Quelle:
    id: str
    titel: str
    url: Optional[str]
    typ: str  # gesetz | behoerde | rechner | parlament | sekundaer
    herausgeber: Optional[str]
    pruefstatus: Pruefstatus
    geprueft_am: Optional[date]
    geprueft_von: Optional[str]
    notiz: Optional[str] = None


@dataclass(frozen=True)
class Zustaendigkeit:
    id: str
    name: str
    beschreibung: Optional[str] = None
    url: Optional[str] = None
    quellen: tuple[str, ...] = ()


@dataclass(frozen=True)
class Frist:
    """Frist relativ zu einem Ereignis.

    ``bezug``: ``geburt`` (Geburtsdatum, sonst errechneter Termin) oder
    ``termin`` (errechneter Entbindungstermin) oder ``keiner`` (nur Text).
    ``art``: ``spaetestens`` | ``fruehestens`` | ``empfohlen``.
    """

    text: str
    bezug: str = "keiner"
    art: str = "spaetestens"
    tage: int = 0
    wochen: int = 0
    monate: int = 0
    quellen: tuple[str, ...] = ()


@dataclass(frozen=True)
class Betrag:
    text: str
    zeitraum: Zeitraum = field(default_factory=Zeitraum)
    quellen: tuple[str, ...] = ()


@dataclass(frozen=True)
class Verfahren:
    unterlagen: tuple[str, ...] = ()
    schritte: tuple[str, ...] = ()
    fristen: tuple[Frist, ...] = ()
    kosten: Optional[str] = None
    online_url: Optional[str] = None
    hinweise: tuple[str, ...] = ()


@dataclass(frozen=True)
class Leistung:
    """Abstrakte Leistung, unabhängig vom Ort (z. B. "Elterngeld")."""

    id: str
    name: str
    kurz: str
    ereignisse: tuple[str, ...]  # z. B. ("geburt",)
    verwaltungsebene: Ebene  # Ebene, auf der die Leistung konkret verwaltet wird
    fuer: str  # haushalt | mutter | jeder_elternteil
    voraussetzungen: tuple[str, ...] = ()  # IDs von Leistungen, die vorher erledigt sein sollten
    betraege: tuple[Betrag, ...] = ()
    # pflicht (gesetzliche Pflicht, z. B. Geburtsanzeige) | antrag | geldleistung | information
    art: str = "antrag"


@dataclass(frozen=True)
class Leistungsvariante:
    """Ausprägung einer Leistung für ein konkretes Gebiet."""

    id: str
    leistung_id: str
    gebiet_id: str
    regel: dict[str, Any]
    zustaendigkeit_id: str
    verfahren: Verfahren
    zeitraum: Zeitraum
    quellen: tuple[str, ...]
    hinweise: tuple[str, ...] = ()
