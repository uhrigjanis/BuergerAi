"""JSON-Schema für die Fakten-Extraktion und Prüfung der LLM-Ausgabe (#75, ADR 0009 §1).

Das LLM darf nur liefern, was der Katalog kennt. Das Schema wird aus den
Fachmodulen der gewählten Lebenslagen erzeugt, nicht von Hand gepflegt.

Form der Ausgabe::

    {"fakten": {"kind_geboren": {"wert": "nein", "beleg": "Wir bekommen im März ein Kind"},
                "mutter.beschaeftigt": {"wert": "ja", "beleg": "ich arbeite als Pflegerin"}}}

``pruefen`` prüft jede Angabe unabhängig vom Anbieter. Was nicht besteht, wird
verworfen, nicht repariert. Nichts geht ungeprüft in die Engine.

Orte (#115): Für Ortsfakten und den Wohnort nennt das Modell nur den Namen, wie er im
Text steht, und eine PLZ nur, wenn sie als Ziffern dasteht::

    {"wohnort": {"ortsname": "Freising", "plz": "", "beleg": "ziehen nach Freising"},
     "fakten": {"umzug.ort_alt": {"ortsname": "Köln", "plz": "", "beleg": "von Köln"}}}

Gemeindeschlüssel und PLZ kommen ausschließlich aus der Wissensbasis (``gebiete.ort_suchen``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Optional, Union

from .. import gebiete
from ..fakten import UNBEKANNT, EingabeFehler, FaktDefinition, parse_wert
from ..modell import Gebiet
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

# Rolle des Wohnorts in ``Ortsangabe``; die anderen Rollen sind die IDs der Ortsfakten
WOHNORT = "wohnort"


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


def ort_schema(beschreibung: str) -> dict[str, Any]:
    """Ortsangabe: nur der Name aus dem Text, eine PLZ nur als Ziffern aus dem Text (#115)."""
    return {
        "type": "object",
        "description": beschreibung,
        "properties": {
            "ortsname": {"type": "string", "description": "Name der Stadt oder Gemeinde genau wie im Text; "
                                                          "leer, wenn nur eine Postleitzahl dasteht"},
            "plz": {"type": "string", "description": "Postleitzahl nur, wenn sie als Ziffern im Text steht; sonst leer"},
            "beleg": {"type": "string", "description": "wörtliches Zitat aus dem Text, das den Ort nennt"},
        },
        "required": ["ortsname", "plz", "beleg"],
        "additionalProperties": False,
    }


WOHNORT_BESCHREIBUNG = ("Wo wohnt die Person? Bei einem Umzug der neue Wohnort. "
                        "Nur, wenn der Text den Ort ausdrücklich nennt.")


def fakt_schema(kb: Wissensbasis, fid: str, d: FaktDefinition) -> dict[str, Any]:
    if d.typ == "ort":
        return ort_schema(re.sub(r"\s*\(Postleitzahl\)", "", _beschreibung(kb, fid, d)))
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


def schema_aus(kb: Wissensbasis, erlaubt: dict[str, FaktDefinition], wohnort: bool = False) -> dict[str, Any]:
    """JSON-Schema der Extraktion für diese Fakten. Jede Angabe ist freiwillig.

    ``wohnort``: auch nach dem Wohnort fragen (erster Freitext, nicht bei Rückfragen).
    """
    eigenschaften: dict[str, Any] = {
        "fakten": {
            "type": "object",
            "description": "Nur Angaben, die der Text ausdrücklich enthält. Alles andere weglassen.",
            "properties": {fid: fakt_schema(kb, fid, d) for fid, d in erlaubt.items()},
            "additionalProperties": False,
        },
    }
    if wohnort:
        eigenschaften[WOHNORT] = ort_schema(WOHNORT_BESCHREIBUNG)
    return {"type": "object", "properties": eigenschaften, "required": ["fakten"], "additionalProperties": False}


def schema_fuer(kb: Wissensbasis, lebenslagen: Iterable[str]) -> dict[str, Any]:
    """JSON-Schema der Extraktion für die Lebenslagen (erster Freitext, mit Wohnort)."""
    return schema_aus(kb, erlaubte_fakten(kb, lebenslagen), wohnort=True)


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


@dataclass(frozen=True)
class Ortsangabe:
    """Ein Ort aus dem Text (#115). Das Modell liefert Name, Beleg und ggf. PLZ, der Code den Rest.

    ``status``, ``gemeinden`` und ``art`` setzt ``orte_zuordnen`` aus der Wissensbasis.
    """

    id: str  # Rolle: WOHNORT oder die ID des Ortsfakts (z. B. "umzug.ort_alt")
    ortsname: str  # wie im Text, "" wenn nur eine PLZ dasteht
    plz: str  # nur als Ziffern aus dem Text, sonst ""
    beleg: str
    status: str = ""  # gebiete.ORT_EINDEUTIG, ORT_MEHRDEUTIG oder ORT_UNBEKANNT
    gemeinden: tuple[Gebiet, ...] = ()  # eindeutig: genau eine; mehrdeutig: Kandidaten
    art: str = ""  # "plz", "name", "kurzform", "tippfehler"

    @property
    def wert(self) -> tuple[str, str]:
        """Vergleichswert, wenn zwei Aufrufe denselben Ort liefern."""
        return (gebiete.ortsname_normalisieren(self.ortsname), self.plz)

    @property
    def gemeinde(self) -> Optional[Gebiet]:
        return self.gemeinden[0] if self.status == gebiete.ORT_EINDEUTIG and self.gemeinden else None

    def fakt_wert(self) -> Optional[str]:
        """Wert für den Ortsfakt: die PLZ aus dem Text, sonst der Gemeindeschlüssel, wenn eindeutig."""
        if self.plz:
            return self.plz
        g = self.gemeinde
        return g.id if g is not None else None


@dataclass
class Pruefung:
    vorschlaege: list[Vorschlag] = field(default_factory=list)
    verworfen: list[Verworfen] = field(default_factory=list)
    # Alle erkannten Orte mit Zuordnung, auch Wohnort, mehrdeutige und unbekannte (#115).
    # Eindeutige Ortsfakten stehen zusätzlich als Vorschlag in ``vorschlaege``.
    orte: list[Ortsangabe] = field(default_factory=list)

    def ort(self, rolle: str) -> Optional[Ortsangabe]:
        return next((o for o in self.orte if o.id == rolle), None)

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


def _ort_pruefen(rolle: str, eintrag: Any, eingabe: str) -> Union[Ortsangabe, str]:
    """Form und Beleg einer Ortsangabe; Ergebnis ist die (noch nicht zugeordnete) Angabe oder ein GRUND_*.

    Der Name muss im Beleg stehen, der Beleg im Text. Eine PLZ gilt nur als Ziffern im Beleg;
    einen Gemeindeschlüssel nimmt die Prüfung vom Modell nie an.
    """
    if not isinstance(eintrag, dict) or "beleg" not in eintrag or set(eintrag) - {"ortsname", "plz", "beleg"}:
        return GRUND_FORM
    name, plz, beleg = eintrag.get("ortsname") or "", eintrag.get("plz") or "", eintrag["beleg"]
    if not all(isinstance(x, str) for x in (name, plz, beleg)):
        return GRUND_FORM
    name, plz = name.strip(), plz.strip()
    if not name and not plz:
        return GRUND_FORM
    if plz and not gebiete.plz_gueltig(plz):
        return GRUND_WERT
    if not beleg_im_text(beleg, eingabe) or (plz and plz not in beleg):
        return GRUND_BELEG
    if name and not beleg_im_text(name, beleg):
        if not plz:
            return GRUND_BELEG
        name = ""  # die PLZ aus dem Text hat Vorrang
    return Ortsangabe(rolle, name, plz, beleg.strip())


def eintraege_pruefen(kb: Wissensbasis, ausgabe: Any, eingabe: str, erlaubt: dict[str, FaktDefinition],
                      wohnort: bool = False) -> tuple[dict[str, Union[Vorschlag, Ortsangabe]], list[Verworfen]]:
    """Jede Angabe für sich: ID erlaubt, Form, Wert (``parse_wert``), Beleg im Text.

    Ortsfakten und (mit ``wohnort``) der Wohnort ergeben ``Ortsangabe``; die Zuordnung zur
    Gemeinde macht ``orte_zuordnen``. ``nur_wenn`` prüft ``nur_wenn_pruefen`` danach, weil die
    Bedingung auch aus einem anderen Aufruf kommen kann. Falsche äußere Form ist ``LLMUngueltigeAusgabe``.
    """
    if not isinstance(ausgabe, dict) or not isinstance(ausgabe.get("fakten"), dict):
        raise LLMUngueltigeAusgabe("Objekt mit 'fakten' erwartet")
    gueltig: dict[str, Union[Vorschlag, Ortsangabe]] = {}
    verworfen: list[Verworfen] = []
    if wohnort and ausgabe.get(WOHNORT) is not None:
        ort = _ort_pruefen(WOHNORT, ausgabe[WOHNORT], eingabe)
        if isinstance(ort, Ortsangabe):
            gueltig[WOHNORT] = ort
        else:
            verworfen.append(Verworfen(WOHNORT, ort))
    for fid, eintrag in ausgabe["fakten"].items():
        fid = str(fid)
        d = erlaubt.get(fid)
        if d is None:
            grund = GRUND_NICHT_IM_SCHEMA if kb.fakt_definition(fid) is not None else GRUND_UNBEKANNT
            verworfen.append(Verworfen(fid, grund))
            continue
        if d.typ == "ort":
            ort = _ort_pruefen(fid, eintrag, eingabe)
            if isinstance(ort, Ortsangabe):
                gueltig[fid] = ort
            else:
                verworfen.append(Verworfen(fid, ort))
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
        gueltig[fid] = Vorschlag(fid, wert, eintrag["beleg"].strip())
    return gueltig, verworfen


def ort_hinweis(text: str, ortsname: str, andere: Iterable[str] = ()) -> str:
    """Text hinter dem Ortsnamen bis zum Satzende, für Hinweise wie "im Kreis Steinfurt".

    Er endet vor dem nächsten anderen erkannten Ort, damit in "von Neuenkirchen nach
    Steinfurt" der Zielort den Herkunftsort nicht eingrenzt.
    """
    treffer = re.search(rf"(?<!\w){re.escape(ortsname)}(?!\w)", text, re.IGNORECASE) if ortsname else None
    if treffer is None:
        return ""
    rest = re.split(r"[.!?;\n]", text[treffer.end():treffer.end() + 80], maxsplit=1)[0]
    for name in andere:
        if name and name.casefold() != ortsname.casefold():
            stelle = re.search(rf"(?<!\w){re.escape(name)}(?!\w)", rest, re.IGNORECASE)
            if stelle:
                rest = rest[:stelle.start()]
    return rest


def orte_zuordnen(kb: Wissensbasis, gueltig: dict[str, Union[Vorschlag, Ortsangabe]],
                  text: str) -> dict[str, Union[Vorschlag, Ortsangabe]]:
    """Ordnet jede Ortsangabe einer Gemeinde der Wissensbasis zu (``gebiete.ort_suchen``).

    Eine PLZ aus dem Text hat Vorrang vor dem Namen. Das Modell liefert nie einen Schlüssel.
    """
    namen = [o.ortsname for o in gueltig.values() if isinstance(o, Ortsangabe)]
    ergebnis: dict[str, Union[Vorschlag, Ortsangabe]] = {}
    for fid, o in gueltig.items():
        if isinstance(o, Ortsangabe):
            if o.plz:
                treffer = gebiete.gemeinden_fuer_plz(kb, o.plz)
                status = (gebiete.ORT_EINDEUTIG if len(treffer) == 1
                          else gebiete.ORT_MEHRDEUTIG if treffer else gebiete.ORT_UNBEKANNT)
                o = replace(o, status=status, gemeinden=tuple(treffer), art="plz")
            else:
                t = gebiete.ort_suchen(kb, o.ortsname, ort_hinweis(text, o.ortsname, namen))
                o = replace(o, status=t.status, gemeinden=t.gemeinden, art=t.art)
        ergebnis[fid] = o
    return ergebnis


def nur_wenn_pruefen(kb: Wissensbasis, gueltig: dict[str, Union[Vorschlag, Ortsangabe]],
                     bekannt: Optional[dict[str, Any]] = None) -> Pruefung:
    """Verwirft Vorschläge, deren Bedingung bekannt ist und nicht zutrifft.

    Bekannt heißt: in ``bekannt`` (schon bestätigt) oder selbst vorgeschlagen.
    Fehlt die Bedingung ganz, bleibt der Vorschlag; der Nutzer sieht und bestätigt ihn.
    Zugeordnete Ortsangaben kommen nach ``orte``; ein Ortsfakt mit PLZ oder eindeutiger
    Gemeinde zusätzlich als Vorschlag.
    """
    ergebnis = Pruefung()
    werte = {**(bekannt or {}), **{fid: v.wert for fid, v in gueltig.items() if isinstance(v, Vorschlag)}}
    for fid, v in gueltig.items():
        if fid == WOHNORT and isinstance(v, Ortsangabe):
            ergebnis.orte.append(v)
            continue
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
        if isinstance(v, Ortsangabe):
            ergebnis.orte.append(v)
            wert = v.fakt_wert()
            if wert is not None:
                ergebnis.vorschlaege.append(Vorschlag(fid, wert, v.beleg))
            continue
        ergebnis.vorschlaege.append(v)
    return ergebnis


def abschliessen(kb: Wissensbasis, gueltig: dict[str, Union[Vorschlag, Ortsangabe]], verworfen: list[Verworfen],
                 text: str, bekannt: Optional[dict[str, Any]] = None) -> Pruefung:
    """Orte zuordnen, dann ``nur_wenn``; die zuvor verworfenen Angaben stehen vorn."""
    ergebnis = nur_wenn_pruefen(kb, orte_zuordnen(kb, gueltig, text), bekannt)
    ergebnis.verworfen[:0] = verworfen
    return ergebnis


def pruefen(kb: Wissensbasis, ausgabe: Any, eingabe: str, lebenslagen: Iterable[str],
            bekannt: Optional[dict[str, Any]] = None) -> Pruefung:
    """Prüft die Ausgabe des LLM gegen Katalog, Eingabetext und ``nur_wenn`` und ordnet Orte zu.

    ``bekannt``: schon bestätigte Angaben (geparste Werte), für ``nur_wenn``.
    Ist die äußere Form falsch, gilt die ganze Ausgabe als ungültig (``LLMUngueltigeAusgabe``,
    der Aufrufer fällt dann aufs Formular zurück).
    """
    gueltig, verworfen = eintraege_pruefen(kb, ausgabe, eingabe, erlaubte_fakten(kb, lebenslagen), wohnort=True)
    return abschliessen(kb, gueltig, verworfen, eingabe, bekannt)


__all__ = [
    "GRUND_BELEG", "GRUND_FORM", "GRUND_NICHT_IM_SCHEMA", "GRUND_NUR_WENN", "GRUND_UNBEKANNT", "GRUND_WERT",
    "GRUND_WIDERSPRUCH", "WOHNORT", "Ortsangabe", "Pruefung", "Verworfen", "Vorschlag", "abschliessen",
    "beleg_im_text", "eintraege_pruefen", "erlaubte_fakten", "fakt_schema", "frage_text", "nur_wenn_pruefen",
    "ort_hinweis", "ort_schema", "orte_zuordnen", "pruefen", "schema_aus", "schema_fuer",
]
