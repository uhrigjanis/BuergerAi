"""HTML und JS passen zusammen (ANF-WEB-16).

Statisch geprüft an index.html und den ES-Modulen, ohne Browser. Fängt Fehler, die pytest
sonst nicht sieht, etwa wenn ein Merge Teile von index.html verwirft (PR #110).
"""

import re
from collections import Counter
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "src" / "buergerai" / "web" / "static"
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
JS = {p.name: p.read_text(encoding="utf-8") for p in sorted(STATIC.glob("*.js"))}

HTML_IDS = re.findall(r'\bid="([^"]+)"', HTML)
# IDs, die das JS selbst erzeugt: el("…", { id: "x" }) oder x.id = "y"
JS_IDS = {i for text in JS.values() for i in re.findall(r'\bid:\s*"([\w-]+)"|\.id\s*=\s*"([\w-]+)"', text) for i in i if i}
# Gesucht per $("#x"), $("#x …"), querySelector("#x") oder getElementById("x")
GESUCHT = re.compile(r'(?:\$|querySelector(?:All)?)\(\s*["\'`]#([\w-]+)|getElementById\(\s*["\'`]([\w-]+)')


def gesucht():
    return {(name, a or b) for name, text in JS.items() for a, b in GESUCHT.findall(text)}


@pytest.mark.anforderung("ANF-WEB-16")
def test_keine_id_doppelt():
    doppelt = sorted(i for i, n in Counter(HTML_IDS).items() if n > 1)
    assert doppelt == [], f"IDs mehrfach in index.html: {doppelt}"
    assert not (set(HTML_IDS) & JS_IDS), "ID steht in index.html und wird zusätzlich im JS erzeugt"


@pytest.mark.anforderung("ANF-WEB-16")
def test_jede_gesuchte_id_existiert():
    vorhanden = set(HTML_IDS) | JS_IDS
    fehlt = sorted(f"{name}: #{i}" for name, i in gesucht() if i not in vorhanden)
    assert fehlt == [], f"Das JS sucht IDs, die es nicht gibt: {fehlt}"
    assert len(gesucht()) > 30  # der Suchausdruck greift


@pytest.mark.anforderung("ANF-WEB-16")
def test_html_verweise_zeigen_auf_ids():
    """for, aria-labelledby, aria-describedby, aria-controls und href="#…" zeigen auf vorhandene IDs."""
    vorhanden = set(HTML_IDS) | JS_IDS
    ziele = re.findall(r'\b(?:for|aria-controls)="([^"]+)"', HTML)
    ziele += [z for liste in re.findall(r'\baria-(?:labelledby|describedby)="([^"]+)"', HTML) for z in liste.split()]
    ziele += re.findall(r'\bhref="#([^"]+)"', HTML)
    fehlt = sorted(set(ziele) - vorhanden)
    assert fehlt == [], f"Verweise ohne Ziel in index.html: {fehlt}"
