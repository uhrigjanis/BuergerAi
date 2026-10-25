"""Gebietsauflösung: PLZ bzw. Bundesland -> Hierarchie (Gemeinde -> Kreis -> Land -> Bund)."""

from __future__ import annotations

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
