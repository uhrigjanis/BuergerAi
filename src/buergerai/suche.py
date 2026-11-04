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
    # Füll- und Zeitwörter, die in Beschreibungen und Beispielen nur zufällig vorkommen
    "wird", "werden", "wurde", "gehen", "geht", "will", "wollen", "soll", "sollen", "müssen", "jetzt", "schon", "noch",
    "alles", "alle", "erledigen", "tun", "machen", "steht", "stehen", "uns", "mir", "mich", "sie",
    "ihr", "ihre", "bei", "seit", "letzte", "letzten", "nächste", "nächsten", "woche", "monat",
    "jahr", "heute", "morgen", "gerade", "bald", "dort", "hier", "aber", "auch", "nicht", "kein",
    "keine", "sehr", "viel", "mehr", "einen", "einem", "einer", "den", "dem", "des",
}
# Ein Wort, das im Vokabular so vieler Lebenslagen steht, unterscheidet sie nicht
ALLERWELTSWORT = 3
SYNONYM = 3  # Punkte für ein Synonym im Text


def _woerter(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zäöüß]+", text.lower()) if len(w) > 2 and w not in STOPPWOERTER}


def _passt(w: str, v: str) -> bool:
    """Gleiches Wort oder gleicher Wortanfang ("Schwangerschaft" passt zu "schwanger")."""
    return v == w or (len(v) > 3 and (v.startswith(w) or w.startswith(v)))


def _synonym_im_text(synonym: str, klein: str, alle: set[str]) -> bool:
    """Ein Synonym trifft als Ganzes oder, bei mehreren Wörtern, mit allen Wörtern in beliebiger
    Reihenfolge ("Wir bekommen im Mai ein Kind" trifft "Kind bekommen")."""
    s = synonym.lower()
    # am Wortanfang, damit "Ehe" nicht in "gehen" und "arm" nicht in "warm" trifft
    if re.search(r"(?<![a-zäöüß])" + re.escape(s), klein):
        return True
    teile = re.findall(r"[a-zäöüß]+", s)
    return len(teile) > 1 and all(any(_passt(w, t) for w in alle) for t in teile)


def lebenslagen_suchen(kb: Wissensbasis, text: str) -> list[tuple[Lebenslage, int]]:
    """Lebenslagen, die zum Text passen, mit Punkten (höher = besser), beste zuerst.

    Ein Synonym, das am Wortanfang im Text vorkommt, zählt 3 Punkte (bei mehreren Wörtern in
    beliebiger Reihenfolge). Jedes Wort aus Name, Beschreibung, Synonymen oder Beispielen, das auch im
    Text steht, zählt 1 Punkt; Wortanfänge zählen mit. Wörter, die bei mindestens
    ``ALLERWELTSWORT`` Lebenslagen vorkommen (etwa "Kind"), sagen nichts über die Lage und
    zählen nicht. Es bleiben Treffer mit mindestens der Hälfte der Punkte des besten, mit einem
    Synonym schon ab einem Drittel (zweite Lage im selben Text). Die übrigen führen nur zu
    unnötigen Fragen.
    """
    klein = text.lower()
    alle = set(re.findall(r"[a-zäöüß]+", klein))
    woerter = _woerter(text)
    vokabular = {ll.id: _woerter(" ".join((ll.name, ll.beschreibung, *ll.synonyme, *ll.beispiele)))
                 for ll in kb.lebenslagen.values()}
    treffer_je_wort = {w: {lid for lid, vok in vokabular.items() if any(_passt(w, v) for v in vok)} for w in woerter}
    ergebnis: list[tuple[Lebenslage, int]] = []
    for ll in kb.lebenslagen.values():
        punkte = sum(SYNONYM for s in ll.synonyme if _synonym_im_text(s, klein, alle))
        punkte += sum(1 for w, lids in treffer_je_wort.items() if ll.id in lids and len(lids) < ALLERWELTSWORT)
        if punkte:
            ergebnis.append((ll, punkte))
    if not ergebnis:
        return []
    beste = max(p for _, p in ergebnis)

    def stark_genug(p: int) -> bool:
        return 2 * p >= beste or (p >= SYNONYM and 3 * p >= beste)

    return sorted(((ll, p) for ll, p in ergebnis if stark_genug(p)), key=lambda t: (-t[1], t[0].id))
