"""Import der Gebiete (Kreise, Gemeinden, PLZ) für ganz Deutschland.

Erzeugt ``data/generiert/gebiete.json`` aus frei verfügbaren Quellen:

- **PLZ und Gemeinden:** OpenPLZ-Straßenverzeichnis (``streets.csv`` bzw.
  ``streets.updated.csv`` aus github.com/openpotato/openplzapi.data, ODbL).
  Jede Zeile ist eine Straße mit PLZ, Ort und 8-stelligem Gemeindeschlüssel
  (AGS). Daraus ergibt sich die n:m-Zuordnung PLZ ↔ Gemeinde.
- **Kreise:** entweder die Kreisliste des Statistischen Bundesamts
  (CSV mit ``AGS;type;name``, z. B. aus dem Paket ``landkreise-deutschland``)
  oder das amtliche Gemeindeverzeichnis **GV100AD** (Destatis). Aus dem
  GV100AD kommen zusätzlich die Gemeindeverbände (Verwaltungsgemeinschaften,
  Ämter, Verbandsgemeinden) und Gemeinden ohne Straßen.

Länder und Bund werden weiter von Hand gepflegt (``data/bund/gebiete.json``).
Der Import ist wiederholbar: Vor dem Schreiben wird ein Diff zur vorhandenen
Datei ausgegeben (neue, entfallene, umbenannte Gebiete, geänderte PLZ).
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Optional

ZIEL_STANDARD = Path(__file__).resolve().parents[2] / "data" / "generiert" / "gebiete.json"

QUELLE_PLZ = "openplz_strassen"
QUELLE_KREISE = "destatis_kreise"
QUELLE_GV100 = "destatis_gv100ad"

# Textkennzeichen der Kreise im GV100AD (Satzart 40)
GV100_KREISART = {"41": "Kreisfreie Stadt", "42": "Stadtkreis", "43": "Kreis", "44": "Landkreis", "45": "Regionalverband"}

# Wörter, bei denen der Kreisname schon sagt, was er ist ("Rhein-Erft-Kreis", "Region Hannover")
_SELBSTERKLAEREND = ("kreis", "region", "regionalverband")


class ImportFehler(ValueError):
    pass


@dataclass
class Kreis:
    id: str
    name: str  # amtliche Bezeichnung, z. B. "München, Landeshauptstadt"
    art: str  # Landkreis | Kreis | Kreisfreie Stadt | Stadtkreis | Regionalverband

    @property
    def anzeigename(self) -> str:
        """Lesbarer Name für Oberfläche und Zuständigkeiten, z. B. "Landkreis Freising"."""
        kurz = self.name.split(",")[0].strip()
        if any(w in kurz.lower() for w in _SELBSTERKLAEREND):
            return kurz
        return f"{self.art} {kurz}"


@dataclass
class Gemeinde:
    id: str
    name: str
    plz: set[str] = field(default_factory=set)
    verband: Optional[tuple[str, str]] = None  # (Schlüssel, Name)


@dataclass
class Importdaten:
    kreise: dict[str, Kreis]
    gemeinden: dict[str, Gemeinde]
    hinweise: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- Einlesen
def plz_lesen(pfad: Path) -> dict[str, Gemeinde]:
    """OpenPLZ-Straßenverzeichnis -> Gemeinden mit allen PLZ.

    Der Gemeindename ist der häufigste ``Locality``-Wert je AGS.
    """
    namen: dict[str, Counter[str]] = defaultdict(Counter)
    plz: dict[str, set[str]] = defaultdict(set)
    with pfad.open(encoding="utf-8", newline="") as datei:
        leser = csv.DictReader(datei)
        fehlend = {"PostalCode", "Locality", "RegionalKey"} - set(leser.fieldnames or ())
        if fehlend:
            raise ImportFehler(f"{pfad}: Spalten fehlen: {', '.join(sorted(fehlend))}")
        for zeile in leser:
            ags, p = zeile["RegionalKey"].strip(), zeile["PostalCode"].strip()
            if not (len(ags) == 8 and ags.isdigit()):
                raise ImportFehler(f"{pfad}: ungültiger Gemeindeschlüssel {ags!r}")
            if not (len(p) == 5 and p.isdigit()):
                raise ImportFehler(f"{pfad}: ungültige PLZ {p!r} bei {ags}")
            namen[ags][zeile["Locality"].strip()] += 1
            plz[ags].add(p)
    return {ags: Gemeinde(ags, namen[ags].most_common(1)[0][0], plz[ags]) for ags in namen}


def kreisliste_lesen(pfad: Path) -> dict[str, Kreis]:
    """Kreisliste von Destatis als CSV (Trennzeichen ``;``) mit Spalten AGS, type, name."""
    with pfad.open(encoding="utf-8-sig", newline="") as datei:
        leser = csv.DictReader(datei, delimiter=";")
        fehlend = {"AGS", "type", "name"} - set(leser.fieldnames or ())
        if fehlend:
            raise ImportFehler(f"{pfad}: Spalten fehlen: {', '.join(sorted(fehlend))}")
        kreise = {}
        for zeile in leser:
            kid = zeile["AGS"].strip().zfill(5)
            if not (len(kid) == 5 and kid.isdigit()):
                raise ImportFehler(f"{pfad}: ungültiger Kreisschlüssel {zeile['AGS']!r}")
            kreise[kid] = Kreis(kid, zeile["name"].strip(), zeile["type"].strip())
    return kreise


def gv100ad_lesen(pfad: Path) -> tuple[str, dict[str, Kreis], dict[str, Gemeinde]]:
    """Amtliches Gemeindeverzeichnis GV100AD (feste Satzlänge, ISO-8859-1).

    Gelesen werden Satzart 40 (Kreise), 50 (Gemeindeverbände) und 60
    (Gemeinden). Liefert (Gebietsstand, Kreise, Gemeinden).
    """
    kreise: dict[str, Kreis] = {}
    gemeinden: dict[str, Gemeinde] = {}
    verbaende: dict[str, str] = {}
    gemeinde_verband: dict[str, str] = {}
    stand = ""
    for nr, zeile in enumerate(pfad.read_text(encoding="latin-1").splitlines(), 1):
        if not zeile.strip():
            continue
        satzart = zeile[0:2]
        if not stand and len(zeile) >= 10:
            stand = f"{zeile[2:6]}-{zeile[6:8]}-{zeile[8:10]}"
        rs = zeile[10:18]
        name = zeile[22:72].strip()
        if satzart == "40":
            art = GV100_KREISART.get(zeile[122:124])
            if art is None:
                raise ImportFehler(f"{pfad}:{nr}: unbekanntes Kreis-Textkennzeichen {zeile[122:124]!r}")
            kreise[rs[:5]] = Kreis(rs[:5], name, art)
        elif satzart == "50":
            verbaende[rs[:5] + zeile[18:22]] = name
        elif satzart == "60":
            ags = rs
            if not (len(ags) == 8 and ags.isdigit()):
                raise ImportFehler(f"{pfad}:{nr}: ungültiger Gemeindeschlüssel {ags!r}")
            gemeinden[ags] = Gemeinde(ags, name)
            gemeinde_verband[ags] = rs[:5] + zeile[18:22]
    if not kreise or not gemeinden:
        raise ImportFehler(f"{pfad}: keine Kreise oder Gemeinden gefunden – ist das eine GV100AD-Datei?")
    for ags, vid in gemeinde_verband.items():
        if vid in verbaende:
            gemeinden[ags].verband = (vid, verbaende[vid])
    return stand, kreise, gemeinden


def zusammenfuehren(
    plz_gemeinden: dict[str, Gemeinde],
    kreise: dict[str, Kreis],
    amtliche_gemeinden: Optional[dict[str, Gemeinde]] = None,
) -> Importdaten:
    """Führt PLZ-Daten mit Kreisen (und optional amtlichen Gemeinden) zusammen.

    - Gemeinden kommen aus beiden Quellen; die PLZ nur aus den Straßendaten.
    - Kreise ohne Gemeinde werden weggelassen (z. B. nach Eingliederung).
    - Gemeinden in unbekannten Kreisen sind ein Fehler: dann ist die Kreisliste veraltet.
    """
    hinweise: list[str] = []
    gemeinden: dict[str, Gemeinde] = {}
    for ags, g in plz_gemeinden.items():
        gemeinden[ags] = Gemeinde(ags, g.name, set(g.plz))
    if amtliche_gemeinden is not None:
        nur_strassen = sorted(set(plz_gemeinden) - set(amtliche_gemeinden))
        if nur_strassen:
            raise ImportFehler(
                f"{len(nur_strassen)} Gemeindeschlüssel aus den PLZ-Daten fehlen im Gemeindeverzeichnis "
                f"(z. B. {', '.join(nur_strassen[:5])}). Passen die Stände zusammen?"
            )
        for ags, g in amtliche_gemeinden.items():
            if ags in gemeinden:
                gemeinden[ags].verband = g.verband
            else:
                gemeinden[ags] = Gemeinde(ags, g.name.split(",")[0].strip(), set(), g.verband)
        ohne_plz = len(set(amtliche_gemeinden) - set(plz_gemeinden))
        if ohne_plz:
            hinweise.append(f"{ohne_plz} Gemeinden ohne Straßen in den PLZ-Daten (ohne PLZ übernommen)")
    unbekannt = sorted({ags[:5] for ags in gemeinden} - set(kreise))
    if unbekannt:
        raise ImportFehler(f"Kreise fehlen in der Kreisliste: {', '.join(unbekannt)}. Ist die Kreisliste veraltet?")
    leer = sorted(set(kreise) - {ags[:5] for ags in gemeinden})
    if leer:
        hinweise.append(f"Kreise ohne Gemeinden weggelassen: {', '.join(leer)}")
    benutzt = {k: v for k, v in kreise.items() if k not in leer}
    return Importdaten(benutzt, gemeinden, hinweise)


# ---------------------------------------------------------------- Ausgabe
def gebiete_json(daten: Importdaten) -> list[dict[str, Any]]:
    gebiete: list[dict[str, Any]] = []
    for k in sorted(daten.kreise.values(), key=lambda k: k.id):
        gebiete.append(
            {"id": k.id, "name": k.anzeigename, "ebene": "kreis", "parent_id": k.id[:2], "art": k.art}
        )
    for g in sorted(daten.gemeinden.values(), key=lambda g: g.id):
        eintrag: dict[str, Any] = {"id": g.id, "name": g.name, "ebene": "gemeinde", "parent_id": g.id[:5]}
        if g.plz:
            eintrag["plz"] = sorted(g.plz)
        if g.verband:
            eintrag["verband"] = {"id": g.verband[0], "name": g.verband[1]}
        gebiete.append(eintrag)
    return gebiete


def quellen_json(kreisquelle: str, plz_version: str, kreis_version: str) -> list[dict[str, Any]]:
    quellen = [
        {
            "id": QUELLE_PLZ,
            "titel": f"OpenPLZ API Data – Straßenverzeichnis Deutschland (Stand {plz_version})",
            "url": "https://github.com/openpotato/openplzapi.data",
            "typ": "sekundaer",
            "herausgeber": "OpenPotato / OpenStreetMap-Mitwirkende",
            "pruefstatus": "ungeprueft",
            "notiz": "Lizenz: ODbL 1.0 (© OpenStreetMap-Mitwirkende). PLZ und Gemeindezuordnung werden geometrisch "
            "aus OSM bestimmt und sind nicht amtlich; Postfach- und Großkunden-PLZ fehlen.",
        }
    ]
    if kreisquelle == QUELLE_GV100:
        quellen.append(
            {
                "id": QUELLE_GV100,
                "titel": f"Gemeindeverzeichnis GV100AD des Statistischen Bundesamts (Gebietsstand {kreis_version})",
                "url": "https://www.destatis.de/DE/Themen/Laender-Regionen/Regionales/Gemeindeverzeichnis/_inhalt.html",
                "typ": "behoerde",
                "herausgeber": "Statistisches Bundesamt",
                "pruefstatus": "ungeprueft",
                "notiz": "Lizenz: Datenlizenz Deutschland – Namensnennung 2.0 (© Statistisches Bundesamt).",
            }
        )
    else:
        quellen.append(
            {
                "id": QUELLE_KREISE,
                "titel": f"Kreisfreie Städte und Landkreise (GV-ISys, Stand {kreis_version})",
                "url": "https://www.destatis.de/DE/Themen/Laender-Regionen/Regionales/Gemeindeverzeichnis/Administrativ/04-kreise.html",
                "typ": "behoerde",
                "herausgeber": "Statistisches Bundesamt",
                "pruefstatus": "ungeprueft",
                "notiz": "Lizenz: CC BY 4.0 (© Statistisches Bundesamt). Übernommen über das npm-Paket "
                "'landkreise-deutschland'. Kreise ohne Gemeinden in den PLZ-Daten (Eingliederungen) werden weggelassen.",
            }
        )
    return quellen


def datei_erzeugen(
    daten: Importdaten,
    kreisquelle: str,
    plz_version: str,
    kreis_version: str,
    importdatum: Optional[date] = None,
) -> dict[str, Any]:
    gebiete = gebiete_json(daten)
    kreis_quellen = [kreisquelle]
    gemeinde_quellen = [QUELLE_PLZ] + ([QUELLE_GV100] if kreisquelle == QUELLE_GV100 else [])
    for g in gebiete:
        g["quellen"] = kreis_quellen if g["ebene"] == "kreis" else gemeinde_quellen
    return {
        "_hinweis": "Automatisch erzeugt mit 'buergerai gebiete-import'. Nicht von Hand ändern – "
        "Korrekturen gehören in die Quelldaten oder in handgepflegte Dateien.",
        "_import": {
            "importiert_am": (importdatum or date.today()).isoformat(),
            "quellen": {QUELLE_PLZ: plz_version, kreisquelle: kreis_version},
            "anzahl": {
                "kreise": len(daten.kreise),
                "gemeinden": len(daten.gemeinden),
                "plz": len({p for g in daten.gemeinden.values() for p in g.plz}),
            },
            "hinweise": daten.hinweise,
        },
        "quellen": quellen_json(kreisquelle, plz_version, kreis_version),
        "gebiete": gebiete,
    }


def als_text(inhalt: dict[str, Any]) -> str:
    """JSON mit einem Gebiet je Zeile: kompakt, aber im Git-Diff gut lesbar."""
    kopf = {k: v for k, v in inhalt.items() if k != "gebiete"}
    text = json.dumps(kopf, ensure_ascii=False, indent=2)
    zeilen = ",\n".join("    " + json.dumps(g, ensure_ascii=False) for g in inhalt["gebiete"])
    return text[:-2] + ',\n  "gebiete": [\n' + zeilen + "\n  ]\n}\n"


# ---------------------------------------------------------------- Diff
@dataclass
class Diff:
    neu: list[str] = field(default_factory=list)
    entfallen: list[str] = field(default_factory=list)
    umbenannt: list[tuple[str, str, str]] = field(default_factory=list)
    verschoben: list[tuple[str, str, str]] = field(default_factory=list)
    plz_neu: list[tuple[str, str]] = field(default_factory=list)
    plz_entfallen: list[tuple[str, str]] = field(default_factory=list)

    @property
    def leer(self) -> bool:
        return not any(vars(self).values())

    def zeilen(self, beispiele: int = 10) -> list[str]:
        if self.leer:
            return ["Keine Änderungen an Gebieten und PLZ."]
        aus: list[str] = []

        def block(titel: str, eintraege: list[Any], fmt: Any) -> None:
            if not eintraege:
                return
            aus.append(f"{titel}: {len(eintraege)}")
            aus.extend("  " + fmt(e) for e in eintraege[:beispiele])
            if len(eintraege) > beispiele:
                aus.append(f"  … und {len(eintraege) - beispiele} weitere")

        block("Neue Gebiete", self.neu, str)
        block("Entfallene Gebiete", self.entfallen, str)
        block("Umbenannt", self.umbenannt, lambda e: f"{e[0]}: {e[1]} → {e[2]}")
        block("Anderer übergeordneter Kreis", self.verschoben, lambda e: f"{e[0]}: {e[1]} → {e[2]}")
        block("PLZ hinzugekommen", self.plz_neu, lambda e: f"{e[0]} {e[1]}")
        block("PLZ entfallen", self.plz_entfallen, lambda e: f"{e[0]} {e[1]}")
        return aus


def vergleichen(alt: Iterable[dict[str, Any]], neu: Iterable[dict[str, Any]]) -> Diff:
    a = {g["id"]: g for g in alt}
    n = {g["id"]: g for g in neu}
    d = Diff()
    d.neu = [f"{i} {n[i]['name']}" for i in sorted(set(n) - set(a))]
    d.entfallen = [f"{i} {a[i]['name']}" for i in sorted(set(a) - set(n))]
    for i in sorted(set(a) & set(n)):
        if a[i]["name"] != n[i]["name"]:
            d.umbenannt.append((i, a[i]["name"], n[i]["name"]))
        if a[i].get("parent_id") != n[i].get("parent_id"):
            d.verschoben.append((i, str(a[i].get("parent_id")), str(n[i].get("parent_id"))))
        pa, pn = set(a[i].get("plz", ())), set(n[i].get("plz", ()))
        d.plz_neu += [(p, i) for p in sorted(pn - pa)]
        d.plz_entfallen += [(p, i) for p in sorted(pa - pn)]
    return d


def vorhandene_gebiete(pfad: Path) -> list[dict[str, Any]]:
    if not pfad.exists():
        return []
    return json.loads(pfad.read_text(encoding="utf-8")).get("gebiete", [])
