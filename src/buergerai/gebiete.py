"""Gebietsauflösung: PLZ bzw. Bundesland -> Hierarchie (Gemeinde -> Kreis -> Land -> Bund).

Dazu die Ortssuche nach Namen (``ort_suchen``, #115).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from .modell import Ebene, Gebiet
from .wissensbasis import Wissensbasis


class GebietFehler(ValueError):
    pass


class PlzUnbekannt(GebietFehler):
    """Die PLZ liegt nicht im erfassten Gebiet. Das Bundesland muss angegeben werden."""


class PlzMehrdeutig(GebietFehler):
    def __init__(self, plz: str, gemeinden: list[Gebiet]):
        namen = ", ".join(f"{g.name} ({g.id})" for g in gemeinden)
        super().__init__(f"PLZ {plz} gehört zu mehreren Gemeinden: {namen}. Bitte Gemeinde wählen.")
        self.gemeinden = gemeinden


def plz_gueltig(plz: str) -> bool:
    return len(plz) == 5 and plz.isdigit()


def gemeinden_fuer_plz(kb: Wissensbasis, plz: str) -> list[Gebiet]:
    """Gemeinden zu einer PLZ. Exakte PLZ-Treffer haben Vorrang vor Präfix-Treffern.

    Eine PLZ kann zu mehreren Gemeinden gehören (n:m), bundesweit über 1.400 Mal.
    """
    exakt = kb.plz_index().get(plz)
    if exakt:
        return [kb.gebiete[i] for i in exakt]
    gemeinden = [g for g in kb.gebiete.values() if g.ebene is Ebene.GEMEINDE and g.plz_praefixe]
    return sorted(
        (g for g in gemeinden if any(plz.startswith(p) for p in g.plz_praefixe)), key=lambda g: (g.name, g.id)
    )


def kreis_von(kb: Wissensbasis, gemeinde: Gebiet) -> Optional[Gebiet]:
    """Übergeordneter Kreis einer Gemeinde (zur Unterscheidung gleichnamiger Gemeinden)."""
    parent = kb.gebiete.get(gemeinde.parent_id) if gemeinde.parent_id else None
    return parent if parent is not None and parent.ebene is Ebene.KREIS else None


def hierarchie(kb: Wissensbasis, gebiet_id: str) -> list[Gebiet]:
    """Vom spezifischsten zum allgemeinsten Gebiet."""
    kette: list[Gebiet] = []
    aktuell: Optional[Gebiet] = kb.gebiete.get(gebiet_id)
    if aktuell is None:
        raise GebietFehler(f"Unbekanntes Gebiet {gebiet_id}")
    while aktuell is not None:
        if aktuell in kette:
            raise GebietFehler(f"Zyklus in der Gebietshierarchie bei {aktuell.id}")
        kette.append(aktuell)
        aktuell = kb.gebiete.get(aktuell.parent_id) if aktuell.parent_id else None
    return kette


def land_nach_kuerzel(kb: Wissensbasis, kuerzel: str) -> Gebiet:
    kuerzel = kuerzel.strip().upper()
    for g in kb.gebiete.values():
        if g.ebene is Ebene.LAND and (g.kuerzel == kuerzel or g.id == kuerzel):
            return g
    raise GebietFehler(f"Unbekanntes Bundesland: {kuerzel}")


def laender(kb: Wissensbasis) -> list[Gebiet]:
    return sorted((g for g in kb.gebiete.values() if g.ebene is Ebene.LAND), key=lambda g: g.id)


def aufloesen(
    kb: Wissensbasis,
    plz: Optional[str] = None,
    gemeinde_id: Optional[str] = None,
    land: Optional[str] = None,
) -> list[Gebiet]:
    """Ermittelt die Gebietshierarchie.

    Reihenfolge: explizite Gemeinde > PLZ > Bundesland. Ist die PLZ keiner
    Gemeinde zugeordnet (Postfach-PLZ), wird mit dem angegebenen Bundesland
    weitergemacht (Fallback auf Landes- und Bundesdaten). Ohne Bundesland:
    ``PlzUnbekannt``.
    """
    if gemeinde_id:
        gebiet = kb.gebiete.get(gemeinde_id)
        if gebiet is None or gebiet.ebene is not Ebene.GEMEINDE:
            raise GebietFehler(f"Unbekannte Gemeinde {gemeinde_id}")
        return hierarchie(kb, gebiet.id)
    if plz:
        if not plz_gueltig(plz):
            raise GebietFehler(f"Ungültige PLZ {plz!r}: fünf Ziffern erwartet")
        treffer = gemeinden_fuer_plz(kb, plz)
        if len(treffer) > 1:
            raise PlzMehrdeutig(plz, treffer)
        if len(treffer) == 1:
            return hierarchie(kb, treffer[0].id)
    if land:
        return hierarchie(kb, land_nach_kuerzel(kb, land).id)
    if plz:
        raise PlzUnbekannt(
            f"PLZ {plz} ist keiner Gemeinde zugeordnet (z. B. eine Postfach- oder Großkunden-PLZ). "
            "Bitte die PLZ der Wohnadresse oder das Bundesland angeben."
        )
    raise GebietFehler("Bitte PLZ, Gemeinde oder Bundesland angeben")


def bund(kb: Wissensbasis) -> Gebiet:
    return kb.bund()


def hierarchie_fuer_ort(kb: Wissensbasis, wert: str) -> list[Gebiet]:
    """Hierarchie für einen Fakt vom Typ ``ort`` (PLZ oder Gemeindeschlüssel), z. B. Lage einer Immobilie.

    Anders als beim Wohnort wird nicht nachgefragt: Gehört eine PLZ zu mehreren
    Gemeinden, gilt der gemeinsame Teil der Hierarchien (meist Kreis oder Land).
    Unbekannte Orte ergeben nur den Bund.
    """
    if len(wert) == 8 and wert in kb.gebiete and kb.gebiete[wert].ebene is Ebene.GEMEINDE:
        return hierarchie(kb, wert)
    treffer = gemeinden_fuer_plz(kb, wert) if plz_gueltig(wert) else []
    if not treffer:
        return [bund(kb)]
    ketten = [hierarchie(kb, g.id) for g in treffer]
    gemeinsam = [g for g in ketten[0] if all(g in k for k in ketten[1:])]
    return gemeinsam


# ------------------------------------------------------------------ Ortssuche nach Namen (#115)
#
# Das LLM nennt nur den Ortsnamen, wie er im Text steht. Die Zuordnung zu einer Gemeinde
# macht dieser Code, lokal und ohne Netz (ADR 0009 §7). Eine falsche Zuordnung wiegt
# schwerer als keine: Im Zweifel ist das Ergebnis "mehrdeutig", und der Mensch wählt.

ORT_EINDEUTIG = "eindeutig"
ORT_MEHRDEUTIG = "mehrdeutig"
ORT_UNBEKANNT = "unbekannt"

_UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
# Stellen, an denen ein Name zur Kurzform wird: "Frankfurt am Main" -> "Frankfurt", "Burg (Dithmarschen)" -> "Burg"
_KURZ_TRENNER = re.compile(r"\s*\(|/| (?:am|an der|an|im|in|in der|ob der|bei|auf|vor der|unter) ")
_KREIS_ART = ("kreisfreie stadt ", "landkreis ", "stadtkreis ", "kreis ", "staedteregion ", "regionalverband ",
              "region ")
_KUERZEL_EXTRA = {"NRW": "NW"}
MIN_LAENGE_TIPPFEHLER = 5


@dataclass(frozen=True)
class Ortstreffer:
    """Ergebnis der Ortssuche. ``gemeinden``: bei ``eindeutig`` genau eine, sonst die Kandidaten."""

    status: str  # ORT_EINDEUTIG, ORT_MEHRDEUTIG oder ORT_UNBEKANNT
    gemeinden: tuple[Gebiet, ...] = ()
    art: str = ""  # wie gefunden: "name", "kurzform", "tippfehler" ("" bei unbekannt)
    eingegrenzt: bool = False  # Kandidaten über Kreis, Land oder PLZ im Hinweis eingegrenzt


def ortsname_normalisieren(name: str) -> str:
    """Kleinbuchstaben, Umlaute und ß ausgeschrieben, Satzzeichen weg, "St." als "Sankt"."""
    text = unicodedata.normalize("NFKD", name.casefold().translate(_UMLAUTE))
    text = "".join(z for z in text if not unicodedata.combining(z))
    return " ".join("sankt" if w == "st" else w for w in re.findall(r"[a-z0-9]+", text))


def _kurzformen(name: str) -> set[str]:
    """Kurzformen eines Gemeindenamens, normalisiert: ohne Klammerzusatz, ohne "am …", ohne "Bad"."""
    formen = {ortsname_normalisieren(_KURZ_TRENNER.split(name, maxsplit=1)[0]), ortsname_normalisieren(name)}
    formen |= {f[4:] for f in formen if f.startswith("bad ")}
    formen.discard(ortsname_normalisieren(name))
    return {f for f in formen if len(f) >= 3}


def _ortsnamen_index(kb: Wissensbasis) -> dict[str, tuple[tuple[str, ...], tuple[str, ...]]]:
    """Normalisierter Name -> (IDs mit genau diesem Namen, IDs mit dieser Kurzform)."""

    def bauen() -> dict[str, tuple[tuple[str, ...], tuple[str, ...]]]:
        voll: dict[str, list[str]] = {}
        kurz: dict[str, list[str]] = {}
        for g in kb.gebiete.values():
            if g.ebene is Ebene.GEMEINDE:
                voll.setdefault(ortsname_normalisieren(g.name), []).append(g.id)
                for f in _kurzformen(g.name):
                    kurz.setdefault(f, []).append(g.id)
        return {k: (tuple(voll.get(k, ())), tuple(kurz.get(k, ()))) for k in voll.keys() | kurz.keys()}

    return kb._index("ortsnamen", (len(kb.gebiete),), bauen)


def _ein_fehler(a: str, b: str) -> bool:
    """Unterscheiden sich a und b um genau einen Buchstaben (ersetzt, eingefügt, gelöscht, vertauscht)?"""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
        return len(diff) == 1 or (len(diff) == 2 and diff[1] == diff[0] + 1
                                  and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]])
    kurz, lang = sorted((a, b), key=len)
    i = next((i for i, (x, y) in enumerate(zip(kurz, lang)) if x != y), len(kurz))
    return kurz[i:] == lang[i + 1:]


def _groesse(g: Gebiet) -> tuple[int, str, str]:
    """Reihenfolge der Kandidaten: große Gemeinden (viele PLZ) zuerst, dann Name und Schlüssel."""
    return (-len(g.plz), g.name, g.id)


def land_von(kb: Wissensbasis, gemeinde: Gebiet) -> Optional[Gebiet]:
    return next((g for g in hierarchie(kb, gemeinde.id) if g.ebene is Ebene.LAND), None)


def _kreis_kern(kreis: Gebiet) -> str:
    """"Landkreis Freising" -> "freising", "Kreis Steinfurt" -> "steinfurt"."""
    name = ortsname_normalisieren(kreis.name)
    for art in _KREIS_ART:
        if name.startswith(art):
            return name[len(art):]
    return name


def _eingrenzen(kb: Wissensbasis, kandidaten: list[Gebiet], hinweis: str) -> list[Gebiet]:
    """Kandidaten, zu denen der Hinweis am besten passt (Kreis, Land, PLZ). Passt keiner: alle."""
    if not hinweis.strip() or len(kandidaten) < 2:
        return kandidaten
    woerter = f" {ortsname_normalisieren(hinweis)} "
    kuerzel = set(re.findall(r"\b[A-Z]{2,3}\b", hinweis))
    kuerzel |= {_KUERZEL_EXTRA[k] for k in kuerzel if k in _KUERZEL_EXTRA}
    plz = set(re.findall(r"(?<!\d)\d{5}(?!\d)", hinweis))

    def punkte(g: Gebiet) -> int:
        kreis, land = kreis_von(kb, g), land_von(kb, g)
        return sum((
            kreis is not None and f" {_kreis_kern(kreis)} " in woerter,
            land is not None and (f" {ortsname_normalisieren(land.name)} " in woerter or land.kuerzel in kuerzel),
            bool(plz & set(g.plz)),
        ))

    bewertet = [(punkte(g), g) for g in kandidaten]
    beste = max(p for p, _ in bewertet)
    return [g for p, g in bewertet if p == beste] if beste else kandidaten


def ort_suchen(kb: Wissensbasis, name: str, hinweis: str = "") -> Ortstreffer:
    """Gemeinde zu einem Ortsnamen, ohne Netz und ohne LLM.

    - ``eindeutig``: genau eine Gemeinde trägt den Namen, oder der Hinweis grenzt auf eine ein.
    - ``mehrdeutig``: mehrere Kandidaten, nur eine Kurzform ("Frankfurt", "Tölz") oder ein
      Tippfehler ("Meinten Sie …?"). Der Mensch wählt; nichts wird still übernommen.
    - ``unbekannt``: kein Treffer, z. B. ein Ortsteil ("Schwabing").

    ``hinweis``: Text, in dem Kreis, Land oder PLZ stehen können ("im Kreis Steinfurt").
    Er grenzt nur ein, wenn er zu mindestens einem Kandidaten passt.
    """
    schluessel = ortsname_normalisieren(name)
    if not schluessel:
        return Ortstreffer(ORT_UNBEKANNT)
    index = _ortsnamen_index(kb)
    voll, kurz = index.get(schluessel, ((), ()))
    art = "name" if voll else "kurzform"
    ids = list(dict.fromkeys(voll + kurz))
    if not ids and len(schluessel) >= MIN_LAENGE_TIPPFEHLER:
        art = "tippfehler"
        ids = list(dict.fromkeys(i for k, (v, _) in index.items() if _ein_fehler(schluessel, k) for i in v))
    if not ids:
        return Ortstreffer(ORT_UNBEKANNT)
    kandidaten = sorted((kb.gebiete[i] for i in ids), key=_groesse)
    eingegrenzt = _eingrenzen(kb, kandidaten, hinweis)
    if len(eingegrenzt) < len(kandidaten):
        eindeutig = len(eingegrenzt) == 1 and art != "tippfehler"
        return Ortstreffer(ORT_EINDEUTIG if eindeutig else ORT_MEHRDEUTIG, tuple(eingegrenzt), art, True)
    eindeutig = len(kandidaten) == 1 and art == "name"
    return Ortstreffer(ORT_EINDEUTIG if eindeutig else ORT_MEHRDEUTIG, tuple(kandidaten), art)
