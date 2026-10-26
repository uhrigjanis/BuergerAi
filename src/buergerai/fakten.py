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


def ist_jahreszahl(fid: Optional[str]) -> bool:
    """Fakten, deren ID auf "jahr" endet, sind Jahreszahlen (Typ zahl, Anzeige ohne Tausenderpunkt).

    Die Datenprüfung stellt sicher, dass solche Fakten den Typ "zahl" haben.
    """
    return bool(fid) and fid.endswith("jahr")


def wert_als_text(wert: Any, jahreszahl: bool = False) -> str:
    """Wert für die Anzeige; ``jahreszahl``: Zahl ohne Tausenderpunkt (2027 statt 2.027)."""
    if wert is UNBEKANNT:
        return "unbekannt"
    if isinstance(wert, bool):
        return "ja" if wert else "nein"
    if isinstance(wert, date):
        return wert.strftime("%d.%m.%Y")
    if isinstance(wert, int) and jahreszahl:
        return str(wert)
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


def abgeleitete_fakten(fakten: dict[str, Any], stichtag: Optional[date] = None) -> dict[str, Any]:
    """Berechnet Fakten, die sich aus anderen Angaben ergeben."""
    neu: dict[str, Any] = {}
    geboren = fakten.get("kind_geboren")
    if geboren is True and isinstance(fakten.get("geburtsdatum"), date):
        neu["geburtsdatum_oder_termin"] = fakten["geburtsdatum"]
    elif geboren is False and isinstance(fakten.get("errechneter_termin"), date):
        neu["geburtsdatum_oder_termin"] = fakten["errechneter_termin"]
    # Schule: Alter im Jahr der Einschulung (Geburtstag wird mit dem Stichtag des Landes verglichen)
    geburt, jahr = fakten.get("bildung.kind_geburtsdatum"), fakten.get("bildung.einschulungsjahr")
    if isinstance(geburt, date) and isinstance(jahr, int) and not isinstance(jahr, bool):
        neu["bildung.alter_im_einschulungsjahr"] = jahr - geburt.year
    elif UNBEKANNT in (geburt, jahr):
        neu["bildung.alter_im_einschulungsjahr"] = UNBEKANNT
    # Ruhestand: Alter bei Rentenbeginn und ob die Regelaltersgrenze dann erreicht ist
    geburt, beginn = fakten.get("ruhestand.geburtsdatum"), fakten.get("ruhestand.rentenbeginn")
    if isinstance(geburt, date) and isinstance(beginn, date):
        neu["ruhestand.alter_bei_rentenbeginn"] = alter_am(geburt, beginn)
        neu["ruhestand.regelaltersgrenze_erreicht"] = beginn >= regelaltersrente_ab(geburt)
    elif UNBEKANNT in (geburt, beginn):
        neu["ruhestand.alter_bei_rentenbeginn"] = UNBEKANNT
        neu["ruhestand.regelaltersgrenze_erreicht"] = UNBEKANNT
    # Das Alter heute nicht noch einmal fragen, wenn das Geburtsdatum schon bekannt ist
    if "alter" not in fakten and isinstance(geburt, date) and stichtag is not None:
        neu["alter"] = alter_am(geburt, stichtag)
    return neu


def alter_am(geburt: date, tag: date) -> int:
    """Alter in vollen Jahren an einem Tag (am Geburtstag zählt das neue Lebensjahr)."""
    return tag.year - geburt.year - ((tag.month, tag.day) < (geburt.month, geburt.day))


def widersprueche(fakten: dict[str, Any], stichtag: date) -> list[str]:
    """Hinweise auf Angaben, die nicht zueinander passen. Es wird nichts überschrieben."""
    hinweise: list[str] = []
    geburt, alter = fakten.get("ruhestand.geburtsdatum"), fakten.get("alter")
    if isinstance(geburt, date) and isinstance(alter, int) and not isinstance(alter, bool):
        berechnet = alter_am(geburt, stichtag)
        if berechnet != alter:
            hinweise.append(
                f"Ihre Angabe zum Alter ({alter}) passt nicht zum Geburtsdatum {geburt.strftime('%d.%m.%Y')} "
                f"(das wären {berechnet} Jahre). Die Rente wird mit dem Geburtsdatum geprüft, andere Leistungen mit der "
                "Altersangabe – bitte prüfen Sie Ihre Angaben."
            )
    return hinweise


def regelaltersgrenze(geburtsjahr: int) -> tuple[int, int]:
    """Regelaltersgrenze (Jahre, Monate) nach § 35 und § 235 SGB VI.

    Bis Jahrgang 1946: 65; 1947–1958: je Jahrgang einen Monat mehr; 1959–1963: je zwei Monate mehr; ab 1964: 67.
    """
    if geburtsjahr <= 1946:
        monate = 0
    elif geburtsjahr <= 1958:
        monate = geburtsjahr - 1946
    elif geburtsjahr <= 1963:
        monate = 12 + (geburtsjahr - 1958) * 2
    else:
        monate = 24
    return 65 + monate // 12, monate % 12


def regelaltersrente_ab(geburt: date) -> date:
    """Erster möglicher Beginn der Regelaltersrente.

    Ein Lebensalter ist mit Ablauf des Tages vor dem Geburtstag vollendet. Die Rente beginnt am Ersten des Monats,
    zu dessen Beginn die Altersgrenze erreicht ist (§ 99 SGB VI). Wer am Ersten eines Monats geboren ist, vollendet
    das Alter also am Monatsletzten davor und bekommt die Rente schon ab dem Monat seines (rechnerischen) Geburtstags;
    alle anderen ab dem Folgemonat.
    """
    jahre, monate = regelaltersgrenze(geburt.year)
    monat = geburt.month + monate
    jahr = geburt.year + jahre + (monat - 1) // 12
    monat = (monat - 1) % 12 + 1
    if geburt.day == 1:
        return date(jahr, monat, 1)
    return date(jahr + (monat == 12), monat % 12 + 1, 1)
