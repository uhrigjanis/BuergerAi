"""Einfache Stichwortsuche nach Lebenslagen (ohne LLM).

Grundlage sind Name, Beschreibung, Synonyme und Beispielsätze der Lebenslagen
in den Fachmodulen (ADR 0008). Die Suche ist der Einstieg ohne LLM und bleibt
die Notbremse, wenn in Phase 3 der LLM-Router nicht verfügbar ist.
"""

from __future__ import annotations

import re

from .modell import Lebenslage
from .wissensbasis import Wissensbasis

# Wörter, die in fast jeder Anfrage vorkommen und nichts über die Lebenslage sagen
STOPPWOERTER = {
    "ich", "wir", "mein", "meine", "unser", "unsere", "und", "oder", "der", "die", "das", "ein", "eine",
    "was", "wie", "wo", "muss", "kann", "habe", "haben", "bin", "sind", "ist", "für", "fuer", "mit",
    "von", "zu", "im", "in", "auf", "es", "gibt", "welche", "bekommen", "beantragen", "nach", "vor",
}


def _woerter(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zäöüß]+", text.lower()) if len(w) > 2 and w not in STOPPWOERTER}


def lebenslagen_suchen(kb: Wissensbasis, text: str) -> list[tuple[Lebenslage, int]]:
    """Lebenslagen, die zum Text passen, mit Punkten (höher = besser), beste zuerst.

    Ein Synonym, das als Ganzes im Text vorkommt, zählt 3 Punkte; jedes Wort aus
    Name, Beschreibung, Synonymen oder Beispielen, das auch im Text steht, 1 Punkt.
    Wortanfänge zählen mit ("Schwangerschaft" passt zu "schwanger").
    """
    klein = text.lower()
    woerter = _woerter(text)
    ergebnis: list[tuple[Lebenslage, int]] = []
    for ll in kb.lebenslagen.values():
        punkte = sum(3 for s in ll.synonyme if s.lower() in klein)
        vokabular = _woerter(" ".join((ll.name, ll.beschreibung, *ll.synonyme, *ll.beispiele)))
        for w in woerter:
            if any(v == w or v.startswith(w) or w.startswith(v) for v in vokabular if len(v) > 3 or v == w):
                punkte += 1
        if punkte:
            ergebnis.append((ll, punkte))
    return sorted(ergebnis, key=lambda t: (-t[1], t[0].id))
