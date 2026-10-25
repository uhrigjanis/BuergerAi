"""Anforderungen mit IDs und die Testmatrix (Anforderung -> Tests).

Quelle der Wahrheit: ``docs/anforderungen.json``. Tests verweisen per
``@pytest.mark.anforderung("ANF-...")`` darauf, Szenarien über das Feld
``anforderungen``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[2]
ANFORDERUNGEN_DATEI = WURZEL / "docs" / "anforderungen.json"
TEST_VERZEICHNIS = WURZEL / "tests"
SZENARIO_VERZEICHNIS = WURZEL / "szenarien"

_MARKER = re.compile(r"@pytest\.mark\.anforderung\(([^)]*)\)")
_ID = re.compile(r"['\"](ANF-[A-Z0-9-]+)['\"]")
_TEST = re.compile(r"^\s*def (test_\w+)", re.M)


@dataclass
class Anforderung:
    id: str
    titel: str
    bereich: str
    tests: list[str] = field(default_factory=list)


def laden() -> list[Anforderung]:
    roh = json.loads(ANFORDERUNGEN_DATEI.read_text(encoding="utf-8"))
    return [Anforderung(a["id"], a["titel"], a["bereich"]) for a in roh["anforderungen"]]


def testmatrix() -> list[Anforderung]:
    """Ordnet jeder Anforderung die Tests und Szenarien zu, die sie abdecken."""
    anforderungen = laden()
    nach_id = {a.id: a for a in anforderungen}
    for datei in sorted(TEST_VERZEICHNIS.rglob("test_*.py")):
        zeilen = datei.read_text(encoding="utf-8").splitlines()
        offene: list[str] = []
        for zeile in zeilen:
            m = _MARKER.search(zeile)
            if m:
                offene.extend(_ID.findall(m.group(1)))
                continue
            t = _TEST.match(zeile)
            if t and offene:
                for aid in offene:
                    if aid in nach_id:
                        nach_id[aid].tests.append(f"{datei.relative_to(WURZEL)}::{t.group(1)}")
                offene = []
    for datei in sorted(SZENARIO_VERZEICHNIS.glob("*.json")):
        for aid in json.loads(datei.read_text(encoding="utf-8")).get("anforderungen", []):
            if aid in nach_id:
                nach_id[aid].tests.append(f"szenario:{datei.stem}")
    return anforderungen


def unbekannte_verweise() -> list[str]:
    """Marker oder Szenarien, die auf nicht existierende Anforderungen zeigen."""
    ids = {a.id for a in laden()}
    falsch: list[str] = []
    for datei in sorted(TEST_VERZEICHNIS.rglob("test_*.py")):
        for m in _MARKER.finditer(datei.read_text(encoding="utf-8")):
            falsch.extend(f"{datei.name}: {aid}" for aid in _ID.findall(m.group(1)) if aid not in ids)
    for datei in sorted(SZENARIO_VERZEICHNIS.glob("*.json")):
        for aid in json.loads(datei.read_text(encoding="utf-8")).get("anforderungen", []):
            if aid not in ids:
                falsch.append(f"{datei.name}: {aid}")
    return falsch
