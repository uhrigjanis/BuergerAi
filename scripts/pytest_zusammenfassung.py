"""Fasst die pytest-Ausgabe als Markdown zusammen (für $GITHUB_STEP_SUMMARY in der CI).

Aufruf: python scripts/pytest_zusammenfassung.py pytest.log "Python 3.13" >> "$GITHUB_STEP_SUMMARY"

Erwartet die Ausgabe von ``pytest -ra --durations=10``: Ergebniszeile, Abschnitt
„short test summary info“ (Fehlschläge) und „slowest 10 durations“.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TRENNER = re.compile(r"^=+ (.*?) =+$")
ERGEBNIS = re.compile(r"\b\d+ (passed|failed|error|errors|skipped)\b.* in [\d.]+s")


def abschnitt(zeilen: list[str], titel: str) -> list[str]:
    """Zeilen zwischen der Trennzeile mit diesem Titel und der nächsten Trennzeile."""
    drin, inhalt = False, []
    for zeile in zeilen:
        treffer = TRENNER.match(zeile)
        if treffer:
            if drin:
                break
            drin = titel in treffer.group(1)
            continue
        if drin and ERGEBNIS.search(zeile):
            break  # mit -q steht die Ergebniszeile ohne Trenner direkt danach
        if drin and zeile.strip():
            inhalt.append(zeile)
    return inhalt


def ergebniszeile(zeilen: list[str]) -> str:
    for zeile in reversed(zeilen):
        treffer = TRENNER.match(zeile)
        text = treffer.group(1) if treffer else zeile.strip()
        if ERGEBNIS.search(text):
            return text
    return "kein Ergebnis gefunden – pytest ist vermutlich vorher abgebrochen"


def zusammenfassung(log: str, titel: str) -> str:
    zeilen = log.splitlines()
    ergebnis = ergebniszeile(zeilen)
    rot = "failed" in ergebnis or "error" in ergebnis or "kein Ergebnis" in ergebnis
    teile = [f"### Tests ({titel}): {'❌' if rot else '✅'} {ergebnis}", ""]
    fehler = [z for z in abschnitt(zeilen, "short test summary info") if z.startswith(("FAILED", "ERROR"))]
    if fehler:
        teile += ["**Fehlgeschlagen:**", "", "```", *fehler, "```", ""]
    langsam = abschnitt(zeilen, "slowest")
    if langsam:
        teile += ["<details><summary>Langsamste Tests</summary>", "", "```", *langsam, "```", "", "</details>", ""]
    return "\n".join(teile)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    titel = argv[1] if len(argv) > 1 else "pytest"
    print(zusammenfassung(Path(argv[0]).read_text(encoding="utf-8", errors="replace"), titel))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
