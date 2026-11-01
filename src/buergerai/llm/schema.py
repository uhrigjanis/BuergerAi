"""JSON-Schema für die Fakten-Extraktion und Prüfung der LLM-Ausgabe (#75, ADR 0009 §1).

Das LLM darf nur liefern, was der Katalog kennt. Das Schema wird aus den
Fachmodulen der gewählten Lebenslagen erzeugt, nicht von Hand gepflegt.

Form der Ausgabe::

    {"fakten": {"kind_geboren": {"wert": "nein", "beleg": "Wir bekommen im März ein Kind"},
                "mutter.beschaeftigt": {"wert": "ja", "beleg": "ich arbeite als Pflegerin"}}}

``pruefen`` prüft jede Angabe unabhängig vom Anbieter. Was nicht besteht, wird
verworfen, nicht repariert. Nichts geht ungeprüft in die Engine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from ..fakten import UNBEKANNT, EingabeFehler, FaktDefinition, parse_wert
from ..regeln import fakten_in_regel
from ..wissensbasis import Wissensbasis
from .basis import LLMUngueltigeAusgabe

UNBEKANNT_TEXT = "unbekannt"

# Gründe fürs Verwerfen. Sie enthalten nie den Wert und dürfen deshalb ins Log (ADR 0009 §3).
GRUND_UNBEKANNT = "unbekannter_fakt"  # ID steht nicht im Katalog
GRUND_NICHT_IM_SCHEMA = "nicht_im_schema"  # ID gibt es, aber nicht für diese Lebenslagen
GRUND_FORM = "form"  # kein Objekt mit "wert" und "beleg"
GRUND_WERT = "wert"  # parse_wert lehnt den Wert ab
GRUND_BELEG = "beleg"  # Beleg fehlt oder steht nicht in der Eingabe
GRUND_NUR_WENN = "nur_wenn"  # Bedingung des Fakts ist nachweislich nicht erfüllt
GRUND_WIDERSPRUCH = "widerspruch"  # Aufrufe je Lebenslage liefern verschiedene Werte (#77)


# ------------------------------------------------------------------ Welche Fakten?

def _aufloesen(kb: Wissensbasis, fid: str, rollen: Iterable[str]) -> list[str]:
    """``person.x`` -> ``mutter.x``, ``anderer_elternteil.x``; sonst die ID selbst."""
    if fid.startswith("person."):
        return [f"{r}.{fid.split('.', 1)[1]}" for r in rollen]
    return [fid]


def erlaubte_fakten(kb: Wissensbasis, lebenslagen: Iterable[str]) -> dict[str, FaktDefinition]:
    """Fakt-IDs, die das LLM für diese Lebenslagen liefern darf, mit ihrer Definition.

    Dazu gehören die Fakten der Fachmodule, die Einstiegsfragen und alle Fakten, die
    Regeln, Fristen und Ortsbezüge der Leistungen verwenden (auch Kern und Importe).
    Abgeleitete Fakten rechnet die Engine selbst; sie stehen nie im Schema.
    """
    lagen = [ll for ll in lebenslagen if ll in kb.lebenslagen]
    module = {kb.lebenslagen[ll].modul for ll in lagen}
    leistungen = kb.leistungen_fuer(lagen)
    rollen = sorted({r for l in leistungen for r in l.fuer} | {r.id for r in kb.rollen.values() if r.modul in module})

    roh: list[str] = [f.id for f in kb.fakten.values() if f.modul in module]
    roh += [d.id for d in kb.einstiegsfragen(lagen)]
    for l in leistungen:
        if l.ortsbezug:
            roh.append(l.ortsbezug)
        for v in kb.varianten_von(l.id):
            roh += fakten_in_regel(v.regel)
            for fr in v.verfahren.fristen:
                if fr.bezug not in ("geburt", "termin", "keiner"):
                    roh.append(fr.bezug)
                if fr.nicht_vor:
                    roh.append(fr.nicht_vor[0])
    for r in kb.rollen.values():
        if r.id in rollen and r.vorbedingung:
            roh += fakten_in_regel(r.vorbedingung)

    ergebnis: dict[str, FaktDefinition] = {}
    offen = list(roh)
    while offen:
        fid = offen.pop(0)
        d = kb.fakt_definition(fid)  # auch Rollen-Fakten wie "mutter.krankenversicherung"
        if d is None or d.abgeleitet:
            continue
        for aufgeloest in _aufloesen(kb, fid, rollen):
            if aufgeloest not in ergebnis:
                ergebnis[aufgeloest] = d
        if d.nur_wenn and d.nur_wenn[0] not in ergebnis:
            offen.append(d.nur_wenn[0])  # die Bedingung muss das LLM auch liefern dürfen
    return dict(sorted(ergebnis.items()))


# ------------------------------------------------------------------ Schema

def _beschreibung(kb: Wissensbasis, fid: str, d: FaktDefinition) -> str:
    rolle = kb.rolle_von_fakt(fid)
    text = d.frage_fuer(rolle.wer if rolle else None)
    text = re.sub(r"\s*\((TT\.MM\.JJJJ|JJJJ)\)", "", text).strip()
    if d.typ == "datum":
        text += " Datum als JJJJ-MM-TT."
    if d.hilfe:
        text += " " + d.hilfe
    return text


def _wert_schema(d: FaktDefinition) -> dict[str, Any]:
    if d.typ == "ja_nein":
        return {"type": "string", "enum": ["ja", "nein", UNBEKANNT_TEXT]}
    if d.typ == "auswahl":
        return {"type": "string", "enum": [w for w, _ in d.optionen] + [UNBEKANNT_TEXT]}
    if d.typ == "zahl":
        # Nur Zahlen: Unbekannte Zahlen lässt das LLM weg, die Engine fragt dann nach.
        return {"type": "number"}
    return {"type": "string"}  # datum, ort, text


def fakt_schema(kb: Wissensbasis, fid: str, d: FaktDefinition) -> dict[str, Any]:
    return {
        "type": "object",
        "description": _beschreibung(kb, fid, d),
        "properties": {
            "wert": _wert_schema(d),
            "beleg": {"type": "string", "description": "wörtliches Zitat aus dem Text, das den Wert belegt"},
        },
        "required": ["wert", "beleg"],
        "additionalProperties": False,
    }


def schema_aus(kb: Wissensbasis, erlaubt: dict[str, FaktDefinition]) -> dict[str, Any]:
    """JSON-Schema der Extraktion für diese Fakten. Jede Angabe ist freiwillig."""
    return {
        "type": "object",
        "properties": {
            "fakten": {
                "type": "object",
                "description": "Nur Angaben, die der Text ausdrücklich enthält. Alles andere weglassen.",
                "properties": {fid: fakt_schema(kb, fid, d) for fid, d in erlaubt.items()},
                "additionalProperties": False,
            },
        },
        "required": ["fakten"],
        "additionalProperties": False,
    }


def schema_fuer(kb: Wissensbasis, lebenslagen: Iterable[str]) -> dict[str, Any]:
    """JSON-Schema der Extraktion für die Lebenslagen."""
    return schema_aus(kb, erlaubte_fakten(kb, lebenslagen))


def frage_text(kb: Wissensbasis, fid: str) -> Optional[str]:
    """Frage zum Fakt, wie das Formular sie stellt (mit eingesetzter Person)."""
    d = kb.fakt_definition(fid)
    if d is None:
        return None
    rolle = kb.rolle_von_fakt(fid)
    return d.frage_fuer(rolle.wer if rolle else None)


# ------------------------------------------------------------------ Prüfung

@dataclass(frozen=True)
class Vorschlag:
    """Geprüfte Angabe. Der Nutzer bestätigt sie, bevor sie in den Bericht eingeht (#79)."""

    id: str
    wert: Any  # wie parse_wert, UNBEKANNT bei "unbekannt"
    beleg: str


@dataclass(frozen=True)
class Verworfen:
    id: str
    grund: str  # GRUND_*, ohne Wert


@dataclass
class Pruefung:
    vorschlaege: list[Vorschlag] = field(default_factory=list)
    verworfen: list[Verworfen] = field(default_factory=list)

    def fakten(self) -> dict[str, Any]:
        return {v.id: v.wert for v in self.vorschlaege}


def _normalisieren(text: str) -> str:
    text = text.casefold()
    for alt, neu in (("„", '"'), ("“", '"'), ("”", '"'), ("‚", "'"), ("‘", "'"), ("’", "'"), ("–", "-"), ("—", "-")):
        text = text.replace(alt, neu)
    return " ".join(text.split())


def beleg_im_text(beleg: Any, eingabe: str) -> bool:
    """Steht das Zitat (bis auf Groß-/Kleinschreibung, Leerraum, Anführungszeichen) im Text?"""
    if not isinstance(beleg, str):
        return False
    zitat = _normalisieren(beleg).strip(" .,;:!?\"'…")
    return bool(zitat) and zitat in _normalisieren(eingabe)


def _bedingung_id(fid: str, d: FaktDefinition) -> Optional[str]:
    if d.nur_wenn is None:
        return None
    ziel = d.nur_wenn[0]
    if ziel.startswith("person.") and "." in fid:
        return fid.split(".", 1)[0] + "." + ziel.split(".", 1)[1]
    return ziel


def eintraege_pruefen(kb: Wissensbasis, ausgabe: Any, eingabe: str,
                      erlaubt: dict[str, FaktDefinition]) -> tuple[dict[str, Vorschlag], list[Verworfen]]:
    """Jede Angabe für sich: ID erlaubt, Form, Wert (``parse_wert``), Beleg im Text.

    ``nur_wenn`` prüft ``nur_wenn_pruefen`` danach, weil die Bedingung auch aus einem
    anderen Aufruf kommen kann. Falsche äußere Form ist ``LLMUngueltigeAusgabe``.
    """
    if not isinstance(ausgabe, dict) or not isinstance(ausgabe.get("fakten"), dict):
        raise LLMUngueltigeAusgabe("Objekt mit 'fakten' erwartet")
    gueltig: dict[str, Vorschlag] = {}
    verworfen: list[Verworfen] = []
    for fid, eintrag in ausgabe["fakten"].items():
        fid = str(fid)
        d = erlaubt.get(fid)
        if d is None:
            grund = GRUND_NICHT_IM_SCHEMA if kb.fakt_definition(fid) is not None else GRUND_UNBEKANNT
            verworfen.append(Verworfen(fid, grund))
            continue
        if not isinstance(eintrag, dict) or "wert" not in eintrag or "beleg" not in eintrag:
            verworfen.append(Verworfen(fid, GRUND_FORM))
            continue
        roh = eintrag["wert"]
        if d.typ == "zahl" and isinstance(roh, str) and roh.strip().lower() != UNBEKANNT_TEXT:
            # "1.500" hieße für parse_wert 1500, "1.5" aber 15: Zahlen nur als JSON-Zahl
            verworfen.append(Verworfen(fid, GRUND_WERT))
            continue
        try:
            wert = parse_wert(d, roh)
        except EingabeFehler:
            verworfen.append(Verworfen(fid, GRUND_WERT))
            continue
        if not beleg_im_text(eintrag["beleg"], eingabe):
            verworfen.append(Verworfen(fid, GRUND_BELEG))
            continue
        if d.typ == "ort" and wert is not UNBEKANNT and wert not in eintrag["beleg"]:
            # PLZ oder Gemeindeschlüssel nur, wenn die Person sie selbst schreibt; sonst wären sie geraten
            verworfen.append(Verworfen(fid, GRUND_BELEG))
            continue
        gueltig[fid] = Vorschlag(fid, wert, eintrag["beleg"].strip())
    return gueltig, verworfen


def nur_wenn_pruefen(kb: Wissensbasis, gueltig: dict[str, Vorschlag],
                     bekannt: Optional[dict[str, Any]] = None) -> Pruefung:
    """Verwirft Vorschläge, deren Bedingung bekannt ist und nicht zutrifft.

    Bekannt heißt: in ``bekannt`` (schon bestätigt) oder selbst vorgeschlagen.
    Fehlt die Bedingung ganz, bleibt der Vorschlag; der Nutzer sieht und bestätigt ihn.
    """
    ergebnis = Pruefung()
    werte = {**(bekannt or {}), **{fid: v.wert for fid, v in gueltig.items()}}
    for fid, v in gueltig.items():
        d = kb.fakt_definition(fid)
        ziel = _bedingung_id(fid, d) if d else None
        if ziel is not None and ziel in werte:
            ziel_def = kb.fakt_definition(ziel)
            try:
                soll = parse_wert(ziel_def, d.nur_wenn[1]) if ziel_def else d.nur_wenn[1]
            except EingabeFehler:
                soll = d.nur_wenn[1]
            if werte[ziel] is UNBEKANNT or werte[ziel] != soll:
                ergebnis.verworfen.append(Verworfen(fid, GRUND_NUR_WENN))
                continue
        ergebnis.vorschlaege.append(v)
    return ergebnis


def pruefen(kb: Wissensbasis, ausgabe: Any, eingabe: str, lebenslagen: Iterable[str],
            bekannt: Optional[dict[str, Any]] = None) -> Pruefung:
    """Prüft die Ausgabe des LLM gegen Katalog, Eingabetext und ``nur_wenn``.

    ``bekannt``: schon bestätigte Angaben (geparste Werte), für ``nur_wenn``.
    Ist die äußere Form falsch, gilt die ganze Ausgabe als ungültig (``LLMUngueltigeAusgabe``,
    der Aufrufer fällt dann aufs Formular zurück).
    """
    gueltig, verworfen = eintraege_pruefen(kb, ausgabe, eingabe, erlaubte_fakten(kb, lebenslagen))
    ergebnis = nur_wenn_pruefen(kb, gueltig, bekannt)
    ergebnis.verworfen[:0] = verworfen
    return ergebnis


__all__ = [
    "GRUND_BELEG", "GRUND_FORM", "GRUND_NICHT_IM_SCHEMA", "GRUND_NUR_WENN", "GRUND_UNBEKANNT", "GRUND_WERT",
    "GRUND_WIDERSPRUCH", "Pruefung", "Verworfen", "Vorschlag", "beleg_im_text", "eintraege_pruefen",
    "erlaubte_fakten", "fakt_schema", "frage_text", "nur_wenn_pruefen", "pruefen", "schema_aus", "schema_fuer",
]
