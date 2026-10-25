"""Datenmodell v3: Fachmodule, Lebenslagen, Gebietshierarchie, Leistungen, Varianten, Quellen.

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

    Je Land und Lebenslage (aus ``abdeckung`` in den Daten):

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
    """Nachweis, dass die Landesleistungen eines Landes für eine Lebenslage recherchiert sind.

    ``landesleistungen``: ``erfasst`` (eigene Leistungen sind als Varianten
    hinterlegt) oder ``keine`` (recherchiert: das Land hat keine eigenen).
    """

    gebiet_id: str
    lebenslage: str
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

    ``bezug``: ``geburt`` (Geburtsdatum, sonst errechneter Termin),
    ``termin`` (errechneter Entbindungstermin), ``keiner`` (nur Text) oder die
    ID eines Fakts vom Typ ``datum`` (z. B. ein Einzugsdatum).
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
class Fachmodul:
    """Fachlicher Experte für ein Gebiet (ADR 0008), z. B. Familie.

    Ein Fachmodul ist ein Datenpaket unter ``data/fachmodule/<id>/``: Lebenslagen,
    Rollen, Fakten und Leistungen. Alle Module laufen auf derselben Engine.
    """

    id: str
    name: str
    beschreibung: str
    abgrenzung: tuple[str, ...] = ()
    importiert_fakten: tuple[str, ...] = ()  # Fakten anderer Module, die Regeln hier verwenden dürfen


@dataclass(frozen=True)
class Lebenslage:
    """Auswählbare Lebenslage eines Fachmoduls, z. B. Geburt (Modul Familie).

    ``typ``: ``ereignis`` (mit Datum und Fristen, z. B. Geburt, Umzug) oder
    ``situation`` (dauert an, z. B. Pflege, geringes Einkommen).
    """

    id: str
    name: str
    typ: str
    modul: str
    beschreibung: str
    einstiegsfragen: tuple[str, ...] = ()  # werden vor allen anderen Fragen gestellt
    synonyme: tuple[str, ...] = ()
    beispiele: tuple[str, ...] = ()
    # Bewusst nicht erfasste Leistungen: (Name, Begründung). Der Bericht nennt sie.
    nicht_erfasst: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Rolle:
    """Person im Haushalt, für die Leistungen einzeln geprüft werden (z. B. Mutter).

    Fakten mit dem Präfix ``person.`` werden je Rolle aufgelöst
    (``person.beschaeftigt`` -> ``mutter.beschaeftigt``). Die ``vorbedingung``
    (Regelknoten) entscheidet, ob es die Person im Haushalt gibt.
    """

    id: str
    name: str  # kurz, z. B. "Mutter"
    wer: str  # im Satz, z. B. "die Mutter (gebärende Person)"
    modul: str
    vorbedingung: Optional[dict[str, Any]] = None

    @property
    def wer_gross(self) -> str:
        return self.wer[:1].upper() + self.wer[1:]


@dataclass(frozen=True)
class Leistung:
    """Abstrakte Leistung, unabhängig vom Ort (z. B. "Elterngeld")."""

    id: str
    name: str
    kurz: str
    lebenslagen: tuple[str, ...]  # z. B. ("geburt",); eine Leistung kann zu mehreren gehören
    verwaltungsebene: Ebene  # Ebene, auf der die Leistung konkret verwaltet wird
    fuer: tuple[str, ...]  # leer = Haushalt, sonst Rollen, die einzeln geprüft werden
    voraussetzungen: tuple[str, ...] = ()  # IDs von Leistungen, die vorher erledigt sein sollten
    betraege: tuple[Betrag, ...] = ()
    # pflicht (z. B. Geburtsanzeige) | antrag | geldleistung | foerderprogramm | information
    art: str = "antrag"
    rechtsanspruch: bool = True  # False: Ermessen bzw. Förderung, solange Mittel reichen
    beantragt_von: str = "selbst"  # selbst | arbeitgeber | angehoerige | von_amts_wegen
    ortsbezug: Optional[str] = None  # None = Wohnort, sonst ID eines Fakts vom Typ "ort"


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
