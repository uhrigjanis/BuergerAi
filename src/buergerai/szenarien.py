"""Szenarien: gespeicherte Testprofile in ``szenarien/*.json``.

Sie dienen gleichzeitig dem manuellen Testen im Terminal und als
Regressionstests (Feld ``erwartet``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

from .fakten import EingabeFehler, parse_wert
from .planer import Anfrage
from .wissensbasis import Wissensbasis

SZENARIO_VERZEICHNIS = Path(__file__).resolve().parents[2] / "szenarien"


@dataclass
class Szenario:
    id: str
    name: str
    beschreibung: str
    anfrage: Anfrage
    erwartet: dict[str, str] = field(default_factory=dict)
    erwartet_fehlend: Optional[list[str]] = None
    erwartet_stellen: dict[str, str] = field(default_factory=dict)  # Leistung -> Teil des Namens der Stelle
    anforderungen: list[str] = field(default_factory=list)
    pfad: Optional[Path] = None


def fakten_parsen(kb: Wissensbasis, roh: dict[str, Any]) -> dict[str, Any]:
    fakten: dict[str, Any] = {}
    for fid, wert in roh.items():
        definition = kb.fakt_definition(fid)
        if definition is None:
            raise EingabeFehler(f"Unbekannter Fakt {fid!r} (siehe 'buergerai fakten')")
        if definition.abgeleitet:
            raise EingabeFehler(f"Fakt {fid!r} wird automatisch abgeleitet und kann nicht gesetzt werden")
        fakten[fid] = parse_wert(definition, wert)
    return fakten


def laden(kb: Wissensbasis, pfad: Path) -> Szenario:
    roh = json.loads(pfad.read_text(encoding="utf-8"))
    anfrage = Anfrage(
        fakten=fakten_parsen(kb, roh.get("fakten", {})),
        plz=roh.get("plz"),
        gemeinde=roh.get("gemeinde"),
        land=roh.get("land"),
        lebenslagen=list(roh.get("lebenslagen") or [roh.get("ereignis", "geburt")]),
        stichtag=date.fromisoformat(roh["stichtag"]) if roh.get("stichtag") else date.today(),
    )
    return Szenario(
        id=pfad.stem,
        name=roh.get("name", pfad.stem),
        beschreibung=roh.get("beschreibung", ""),
        anfrage=anfrage,
        erwartet=roh.get("erwartet", {}),
        erwartet_fehlend=roh.get("erwartet_fehlend"),
        erwartet_stellen=roh.get("erwartet_stellen", {}),
        anforderungen=roh.get("anforderungen", []),
        pfad=pfad,
    )


def abweichungen(s: Szenario, bericht: Any) -> list[str]:
    """Unterschiede zwischen Erwartungen eines Szenarios und dem Bericht (leer = alles wie erwartet)."""
    ist = bericht.ergebnisse()
    fehler = [f"{l}: erwartet {w}, ist {ist.get(l, 'nicht gelistet')}" for l, w in s.erwartet.items() if ist.get(l) != w]
    stellen = {e.leistung.id: e.zustaendigkeit.name for e in bericht.eintraege}
    fehler += [
        f"{l}: zuständige Stelle soll {teil!r} enthalten, ist {stellen.get(l, 'nicht gelistet')!r}"
        for l, teil in s.erwartet_stellen.items()
        if teil not in stellen.get(l, "")
    ]
    if s.erwartet_fehlend is not None and bericht.fehlend != s.erwartet_fehlend:
        fehler.append(f"offene Angaben: erwartet {s.erwartet_fehlend}, ist {bericht.fehlend}")
    return fehler


def alle(kb: Wissensbasis, verzeichnis: Optional[Path] = None) -> list[Szenario]:
    verzeichnis = verzeichnis or SZENARIO_VERZEICHNIS
    return [laden(kb, p) for p in sorted(verzeichnis.glob("*.json"))]


def finden(kb: Wissensbasis, name: str) -> Szenario:
    pfad = Path(name)
    if pfad.suffix == ".json" and pfad.exists():
        return laden(kb, pfad)
    kandidat = SZENARIO_VERZEICHNIS / f"{name}.json"
    if kandidat.exists():
        return laden(kb, kandidat)
    verfuegbar = ", ".join(p.stem for p in sorted(SZENARIO_VERZEICHNIS.glob("*.json")))
    raise FileNotFoundError(f"Szenario {name!r} nicht gefunden. Verfügbar: {verfuegbar}")


def speichern(pfad: Path, anfrage: Anfrage, name: str, beschreibung: str = "") -> None:
    def wert(w: Any) -> Any:
        if isinstance(w, date):
            return w.isoformat()
        if not isinstance(w, (bool, int, float, str)):
            return "unbekannt"
        return w

    daten: dict[str, Any] = {"name": name, "beschreibung": beschreibung}
    for k in ("plz", "gemeinde", "land"):
        if getattr(anfrage, k):
            daten[k] = getattr(anfrage, k)
    daten["stichtag"] = anfrage.stichtag.isoformat()
    daten["lebenslagen"] = list(anfrage.lebenslagen)
    daten["fakten"] = {k: wert(v) for k, v in anfrage.fakten.items()}
    pfad.write_text(json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
