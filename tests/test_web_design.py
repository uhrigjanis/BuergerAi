"""Gestaltung nach docs/design/ClaudeDesign.md (#99): Farben nur als Tokens, Kontrast nach WCAG AA.

Statisch geprüft an style.css, ohne Browser. Der Browser-Rauchtest liegt in scripts/web_rauchtest.py.
"""

import re
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "src" / "buergerai" / "web" / "static"
CSS = (STATIC / "style.css").read_text(encoding="utf-8")

# Die sechs Tokens der Richtlinie (Abschnitt 2), hell und dunkel
RICHTLINIE = {
    "hell": {"--bg-primary": "#F9FAFB", "--bg-surface": "#FFFFFF", "--text-main": "#111827",
             "--text-muted": "#6B7280", "--accent": "#6366F1", "--border-subtle": "#E5E7EB"},
    "dunkel": {"--bg-primary": "#0B0F19", "--bg-surface": "#161B26", "--text-main": "#F9FAFB",
               "--text-muted": "#9CA3AF", "--accent": "#818CF8", "--border-subtle": "#222938"},
}
FARBE = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(", re.I)
BENANNT = re.compile(r":\s*(?:white|black|red|green|blue|yellow|gray|grey|orange)\b", re.I)


def ohne_kommentare(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def root_bloecke(css):
    """Inhalt aller `:root { … }`-Blöcke (auch in @media), in Reihenfolge."""
    return re.findall(r":root\s*\{([^{}]*)\}", ohne_kommentare(css))


def ohne_block(css, kopf):
    """Entfernt alle Blöcke, die mit `kopf {` beginnen, samt verschachtelter Klammern."""
    while (start := css.find(kopf)) >= 0:
        tiefe, i = 0, css.index("{", start)
        while True:
            tiefe += {"{": 1, "}": -1}.get(css[i], 0)
            i += 1
            if tiefe == 0:
                break
        css = css[:start] + css[i:]
    return css


def tokens(block):
    return {k: v.strip() for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", block)}


def modi():
    hell, dunkel_zusatz = root_bloecke(CSS)[:2]
    hell_t = tokens(hell)
    return {"hell": hell_t, "dunkel": {**hell_t, **tokens(dunkel_zusatz)}}


def luminanz(hexwert):
    h = hexwert.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    kanaele = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in kanaele]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def kontrast(a, b):
    la, lb = sorted((luminanz(a), luminanz(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


@pytest.mark.anforderung("ANF-WEB-15")
def test_tokens_der_richtlinie_hell_und_dunkel():
    m = modi()
    assert "prefers-color-scheme: dark" in CSS
    for modus, erwartet in RICHTLINIE.items():
        for name, wert in erwartet.items():
            assert m[modus][name].upper() == wert, (modus, name)


@pytest.mark.anforderung("ANF-WEB-15")
def test_farben_nur_in_den_tokens():
    """Außerhalb der :root-Blöcke keine Farbwerte, nur var(--…)."""
    rest = re.sub(r":root\s*\{[^{}]*\}", "", ohne_kommentare(CSS))
    assert FARBE.findall(rest) == []
    assert BENANNT.findall(rest) == []
    # Alle verwendeten Tokens sind definiert
    definiert = set(modi()["hell"])
    benutzt = set(re.findall(r"var\((--[\w-]+)\)", CSS))
    assert benutzt <= definiert, benutzt - definiert


@pytest.mark.anforderung("ANF-WEB-15")
@pytest.mark.parametrize("modus", ["hell", "dunkel"])
def test_kontrast_wcag_aa(modus):
    """Text ≥ 4,5 : 1 auf beiden Flächen; Akzent als Indikator (Fokus, Fortschritt) ≥ 3 : 1."""
    t = modi()[modus]
    flaechen = [t["--bg-primary"], t["--bg-surface"]]
    for text in ("--text-main", "--text-muted", "--accent-strong"):
        for f in flaechen:
            assert kontrast(t[text], f) >= 4.5, (modus, text, f, round(kontrast(t[text], f), 2))
    assert kontrast(t["--on-accent"], t["--accent-strong"]) >= 4.5
    for f in flaechen:
        assert kontrast(t["--accent"], f) >= 3, (modus, f)


@pytest.mark.anforderung("ANF-WEB-15")
def test_eine_spalte_bewegung_und_lesbarkeit():
    css = ohne_kommentare(CSS)
    assert "max-width: 48rem" in css  # max-w-3xl
    assert re.search(r"body\s*\{[^}]*font:\s*1rem/1\.625", css)  # leading-relaxed
    # Bewegung nur, wenn der Nutzer sie nicht abgeschaltet hat
    ohne_bewegung = ohne_block(css, "@media (prefers-reduced-motion: no-preference)")
    assert "animation" not in ohne_bewegung and "transition" not in ohne_bewegung
    assert "scale(.98)" in css
    # Eingabefelder: Akzentrand statt Outline; Knöpfe behalten einen sichtbaren Fokusring (WCAG 2.4.7)
    assert re.search(r"input:focus[^{]*\{[^}]*outline: 0[^}]*border-color: var\(--accent\)", css)
    assert re.search(r":focus-visible\s*\{\s*outline: 2px solid var\(--accent\)", css)
