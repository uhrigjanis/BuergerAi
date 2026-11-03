"""Formulierung: Antworttext aus dem Bericht (#78, ADR 0009 §1 und §8).

Das LLM schreibt je Leistung einen kurzen, verständlichen Text und eine Einleitung.
Alles andere setzt der Code: Name und Ergebnis der Leistung, Quellenlinks, offene
Fragen und den Hinweis „keine Rechtsberatung“.

Eingabe ist nur der Bericht (``modell_daten``), nie der Freitext des Nutzers.
Eine Prompt-Injection im Freitext erreicht den Antworttext deshalb nicht.

Jede Ausgabe wird deterministisch nachgeprüft (``pruefen``). Schlägt die Prüfung
fehl, ist kein LLM konfiguriert oder gibt es einen ``LLMFehler``, gilt der
Vorlagentext (``vorlage``). Er besteht dieselbe Prüfung für alle Szenarien.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from ..planer import Bericht, Eintrag
from ..regeln import Wert
from ..wissensbasis import Wissensbasis
from .basis import LLM, LLMFehler, log
from .schutz import MAX_TOKENS

HINWEIS = "Unverbindliche Orientierung, keine Rechtsberatung. Verbindlich entscheidet die zuständige Stelle."
ERGEBNIS_TEXT = {"ja": "Steht Ihnen voraussichtlich zu", "unklar": "Noch unklar", "nein": "Voraussichtlich nicht"}
ART_TEXT = {"spaetestens": "spätestens", "fruehestens": "frühestens ab", "empfohlen": "empfohlen bis"}
MAX_EINLEITUNG = 500
MAX_ABSCHNITT = 700

SYSTEM = """Du erklärst das Ergebnis einer Behörden-Checkliste in einfachem Deutsch.
Du bekommst den Bericht als JSON. Er ist vollständig und richtig. Du entscheidest nichts.

Regeln:
- Schreibe für jede Leistung im Bericht genau einen Eintrag mit ihrer id, keine weiteren.
- 2 bis 4 kurze Sätze je Leistung: was es ist, was die Person jetzt tun sollte, bis wann.
- Das Ergebnis (ja, nein, unklar) übernimmst du. Mache keine Zusagen wie "sicher" oder "garantiert".
  Bei "nein" und "unklar" schreibe nie, dass die Person die Leistung bekommt.
- Bei "unklar": sage, welche Angaben fehlen (fehlende_angaben).
- Beträge, Daten und Fristen nur genau so, wie sie im Bericht stehen. Keine anderen Zahlen.
- Keine Links, E-Mail-Adressen oder Telefonnummern; die Quellen setzt das Programm.
- Nenne keine Leistung, die nicht im Bericht steht.
- einleitung: 1 bis 2 Sätze Überblick, ohne einzelne Beträge.
- Kein Hinweis auf Rechtsberatung, den fügt das Programm an."""


# ------------------------------------------------------------------ Daten
def _datum(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def _fristen(e: Eintrag) -> list[str]:
    if e.ergebnis is Wert.NEIN:
        return []
    texte = []
    for bf in e.fristen:
        if bf.datum is None:
            texte.append(bf.frist.text)
        else:
            vor = "voraussichtlich " if bf.voraussichtlich else ""
            texte.append(f"{vor}{ART_TEXT[bf.frist.art]} {_datum(bf.datum)}: {bf.frist.text}")
    return texte


def modell_daten(kb: Wissensbasis, bericht: Bericht) -> dict[str, Any]:
    """Der Bericht in kompakter Form: das Einzige, was das Modell sieht (kein Freitext, ADR 0009 §3)."""
    from ..ausgabe import anspruch_text, frage_zu

    leistungen = []
    for e in bericht.eintraege:
        hinweise = ([anspruch_text(e.leistung)] if anspruch_text(e.leistung) else []) + list(e.variante.hinweise)
        leistungen.append({
            "id": e.leistung.id,
            "name": e.leistung.name,
            "kurz": e.leistung.kurz,
            "ergebnis": e.ergebnis.value,
            "betrag": e.betrag.text if e.betrag and e.ergebnis is not Wert.NEIN else None,
            "fristen": _fristen(e),
            "zustaendig": e.zustaendigkeit.name,
            "fehlende_angaben": [frage_zu(kb, fid) for fid in e.fehlend],
            "hinweise": hinweise,
        })
    return {
        "stichtag": _datum(bericht.anfrage.stichtag),
        "lebenslagen": [kb.lebenslagen[ll].name for ll in bericht.anfrage.lebenslagen if ll in kb.lebenslagen],
        "anzahl": {"gesamt": len(bericht.eintraege),
                   **{w.value: sum(1 for e in bericht.eintraege if e.ergebnis is w) for w in Wert}},
        "leistungen": leistungen,
    }


def schema(daten: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "einleitung": {"type": "string"},
            "leistungen": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "enum": [l["id"] for l in daten["leistungen"]]},
                        "text": {"type": "string"},
                    },
                    "required": ["id", "text"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["einleitung", "leistungen"],
        "additionalProperties": False,
    }


# ------------------------------------------------------------------ Ergebnis
@dataclass
class Abschnitt:
    id: str
    name: str
    ergebnis: str
    text: str
    quellen: list[dict[str, Optional[str]]] = field(default_factory=list)


@dataclass
class Antwort:
    einleitung: str
    abschnitte: list[Abschnitt]
    offene_fragen: list[str]
    hinweis: str = HINWEIS
    quelle: str = "vorlage"  # "llm" oder "vorlage"
    fehler: Optional[str] = None  # Fehlerart des LLM, "aus", "pruefung"
    gruende: list[str] = field(default_factory=list)  # warum die Prüfung fehlschlug (nur Codes und IDs)

    def als_text(self) -> str:
        zeilen = [self.einleitung, ""]
        for a in self.abschnitte:
            zeilen += [f"{a.name} – {ERGEBNIS_TEXT[a.ergebnis]}", a.text]
            zeilen += [f"Quelle: {q['titel']}" + (f" ({q['url']})" if q.get("url") else "") for q in a.quellen]
            zeilen.append("")
        if self.offene_fragen:
            zeilen.append("Offene Fragen:")
            zeilen += [f"- {f}" for f in self.offene_fragen]
            zeilen.append("")
        zeilen.append(self.hinweis)
        return "\n".join(zeilen)

    def als_json(self) -> dict[str, Any]:
        return {
            "quelle": self.quelle, "fehler": self.fehler, "einleitung": self.einleitung,
            "abschnitte": [{"id": a.id, "name": a.name, "ergebnis": a.ergebnis,
                            "ergebnis_text": ERGEBNIS_TEXT[a.ergebnis], "text": a.text, "quellen": a.quellen}
                           for a in self.abschnitte],
            "offene_fragen": self.offene_fragen, "hinweis": self.hinweis,
        }


def _zusammensetzen(kb: Wissensbasis, bericht: Bericht, einleitung: str, texte: dict[str, str]) -> Antwort:
    """Name, Ergebnis, Quellen, offene Fragen und Hinweis setzt immer der Code."""
    from ..ausgabe import frage_zu

    abschnitte = [
        Abschnitt(e.leistung.id, e.leistung.name, e.ergebnis.value, texte[e.leistung.id],
                  [{"titel": q.titel, "url": q.url} for q in e.quellen])
        for e in bericht.eintraege
    ]
    return Antwort(einleitung, abschnitte, [frage_zu(kb, fid) for fid in bericht.fehlend])


# ------------------------------------------------------------------ Vorlage
def _vorlage_text(l: dict[str, Any]) -> str:
    saetze = [l["kurz"].rstrip(".") + "."]
    if l["ergebnis"] == "nein":
        saetze.append("Nach Ihren Angaben besteht voraussichtlich kein Anspruch.")
    else:
        if l["betrag"]:
            saetze.append(f"Betrag: {l['betrag'].rstrip('.')}.")
        saetze += [f"Frist: {f.rstrip('.')}." for f in l["fristen"]]
        if l["fehlende_angaben"]:
            saetze.append("Dafür fehlt noch: " + "; ".join(f.rstrip("?") for f in l["fehlende_angaben"]) + ".")
        saetze.append(f"Zuständig: {l['zustaendig']}.")
    saetze += [h.rstrip(".") + "." for h in l["hinweise"]]
    return " ".join(saetze)


def vorlage(kb: Wissensbasis, bericht: Bericht, daten: Optional[dict[str, Any]] = None) -> Antwort:
    """Antwort ohne LLM, nur aus dem Bericht."""
    daten = daten or modell_daten(kb, bericht)
    n = daten["anzahl"]
    if daten["leistungen"]:
        einleitung = (f"Wir haben {n['gesamt']} Leistungen geprüft: {n['ja']} voraussichtlich ja, "
                      f"{n['unklar']} noch unklar, {n['nein']} voraussichtlich nicht.")
    else:
        einleitung = "Zu Ihren Angaben haben wir keine passende Leistung gefunden."
    return _zusammensetzen(kb, bericht, einleitung, {l["id"]: _vorlage_text(l) for l in daten["leistungen"]})


# ------------------------------------------------------------------ Nachprüfung
MONATE = {m: i for i, m in enumerate(("januar", "februar", "märz", "april", "mai", "juni", "juli", "august",
                                      "september", "oktober", "november", "dezember"), 1)}
MONATE["maerz"] = 3
_DATUM_ZAHLEN = re.compile(r"\b(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{4})\b")
_DATUM_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DATUM_WORT = re.compile(r"\b(\d{1,2})\.\s*(" + "|".join(MONATE) + r")\b(?:\s+(\d{4}))?", re.IGNORECASE)
_ZAHL = re.compile(r"\d+(?:[.   ]\d{3})*(?:,\d+)?")
_LINK = re.compile(r"https?://|www\.|\S+@\S+\.\w+|\b[\w-]+\.(?:de|com|org|eu|net)\b", re.IGNORECASE)
_ZUSAGE = re.compile(r"\b(garantiert|ganz sicher|sicher|auf jeden fall|definitiv|mit sicherheit|zweifellos|"
                     r"in jedem fall|100\s?%)\b", re.IGNORECASE)
# Bei "nein" und "unklar" darf der Text keinen Anspruch zusagen
_BEJAHUNG = re.compile(r"\bSie (haben|hätten) (einen |voraussichtlich |wahrscheinlich |auch )?Anspruch\b|"
                       r"\b(steht|stehen) Ihnen (voraussichtlich |auch )?(\w+ )?zu\b|"
                       r"\bSie (bekommen|erhalten)\b(?!\s+(kein|keine|keinen|nicht|nur dann|erst))",
                       re.IGNORECASE)
_VERNEINUNG = re.compile(r"\bkein(en)? Anspruch\b|\bsteht Ihnen (voraussichtlich )?nicht zu\b", re.IGNORECASE)


def _zahl(roh: str) -> str:
    sauber = re.sub(r"[.   ]", "", roh).replace(",", ".")
    try:
        return format(Decimal(sauber).normalize(), "f")
    except InvalidOperation:
        return sauber


def _atome(text: str) -> tuple[set[tuple[int, int, Optional[int]]], set[str]]:
    """Daten (Tag, Monat, Jahr) und übrige Zahlen eines Textes."""
    daten: set[tuple[int, int, Optional[int]]] = set()

    def datum(m: re.Match[str], tag: int, monat: int, jahr: Optional[int]) -> str:
        daten.add((tag, monat, jahr))
        return " "

    rest = _DATUM_ISO.sub(lambda m: datum(m, int(m[3]), int(m[2]), int(m[1])), text)
    rest = _DATUM_ZAHLEN.sub(lambda m: datum(m, int(m[1]), int(m[2]), int(m[3])), rest)
    rest = _DATUM_WORT.sub(lambda m: datum(m, int(m[1]), MONATE[m[2].lower()], int(m[3]) if m[3] else None), rest)
    return daten, {_zahl(z) for z in _ZAHL.findall(rest)}


def _erlaubt(*texte: Any) -> tuple[set[tuple[int, int, Optional[int]]], set[str]]:
    roh = json.dumps(texte, ensure_ascii=False)
    daten, zahlen = _atome(roh)
    zahlen |= {str(j) for _, _, j in daten if j}
    return daten, zahlen


def _zahlen_pruefen(text: str, erlaubt: tuple[set[Any], set[str]]) -> Optional[str]:
    daten, zahlen = _atome(text)
    erlaubte_daten, erlaubte_zahlen = erlaubt
    for tag, monat, jahr in daten:
        if not any(t == tag and m == monat and (jahr is None or j == jahr) for t, m, j in erlaubte_daten):
            return "datum"
    if zahlen - erlaubte_zahlen:
        return "zahl"
    return None


def _fremde_leistung(kb: Wissensbasis, text: str, bekannt: str) -> bool:
    """Nennt der Text eine Leistung aus dem Katalog, die nirgends in den Daten für das Modell vorkommt?"""
    text = text.lower()
    return any(len(n) >= 8 and n in text and n not in bekannt for n in (l.name.lower() for l in kb.leistungen.values()))


def _fremder_link(text: str, bekannt: str) -> bool:
    """Links, Adressen und Domains nur, wenn sie so in den Daten stehen (z. B. „laut hamburg.de“)."""
    return any(m.group(0).lower() not in bekannt for m in _LINK.finditer(text))


def pruefen(kb: Wissensbasis, daten: dict[str, Any], ausgabe: Any,
            laenge: bool = True) -> tuple[list[str], dict[str, str], str]:
    """Nachprüfung der Modellausgabe. Liefert Gründe (leer = bestanden), Texte je Leistung und Einleitung.

    Gründe enthalten nur Codes und Leistungs-IDs, nie Text (ADR 0009 §3). ``laenge=False``
    lässt die Längengrenze weg, die nur für das Modell gilt (die Vorlage darf länger sein).
    """
    if not isinstance(ausgabe, dict) or not isinstance(ausgabe.get("einleitung"), str) \
            or not isinstance(ausgabe.get("leistungen"), list):
        return ["form"], {}, ""
    gruende: list[str] = []
    soll = {l["id"]: l for l in daten["leistungen"]}
    texte: dict[str, str] = {}
    for eintrag in ausgabe["leistungen"]:
        lid = eintrag.get("id") if isinstance(eintrag, dict) else None
        text = eintrag.get("text") if isinstance(eintrag, dict) else None
        if lid not in soll or not isinstance(text, str):
            gruende.append("leistung_fremd")
        elif lid in texte:
            gruende.append(f"leistung_doppelt:{lid}")
        else:
            texte[lid] = " ".join(text.split())
    gruende += [f"leistung_fehlt:{lid}" for lid in soll if lid not in texte]

    bekannt = json.dumps(daten, ensure_ascii=False).lower()
    einleitung = " ".join(ausgabe["einleitung"].split())
    pruefliste = [("einleitung", einleitung, _erlaubt(daten), None, MAX_EINLEITUNG)]
    pruefliste += [(lid, t, _erlaubt(soll[lid]), soll[lid]["ergebnis"], MAX_ABSCHNITT) for lid, t in texte.items()]
    for wo, text, erlaubt, ergebnis, grenze in pruefliste:
        if not text:
            gruende.append(f"leer:{wo}")
            continue
        if laenge and len(text) > grenze:
            gruende.append(f"zu_lang:{wo}")
        fehler = _zahlen_pruefen(text, erlaubt)
        if fehler:
            gruende.append(f"{fehler}:{wo}")
        if _fremder_link(text, bekannt):
            gruende.append(f"link:{wo}")
        if _ZUSAGE.search(text):
            gruende.append(f"zusage:{wo}")
        if ergebnis in ("nein", "unklar") and _BEJAHUNG.search(text):
            gruende.append(f"ergebnis:{wo}")
        if ergebnis == "ja" and _VERNEINUNG.search(text):
            gruende.append(f"ergebnis:{wo}")
        if _fremde_leistung(kb, text, bekannt):
            gruende.append(f"fremde_leistung:{wo}")
    return gruende, texte, einleitung


def vollstaendig(antwort: Antwort, bericht: Bericht) -> list[str]:
    """Prüft die fertige Antwort: jede Leistung genau einmal mit unverändertem Ergebnis, Hinweis vorhanden."""
    gruende = []
    if [(a.id, a.ergebnis) for a in antwort.abschnitte] != [(e.leistung.id, e.ergebnis.value) for e in bericht.eintraege]:
        gruende.append("leistungen")
    if antwort.hinweis != HINWEIS or HINWEIS not in antwort.als_text():
        gruende.append("hinweis")
    return gruende


# ------------------------------------------------------------------ Ablauf
def formulieren(llm: Optional[LLM], kb: Wissensbasis, bericht: Bericht) -> Antwort:
    """Antworttext zum Bericht; bei jedem Problem der Vorlagentext."""
    daten = modell_daten(kb, bericht)
    rueckfall = vorlage(kb, bericht, daten)
    if llm is None:
        return replace(rueckfall, fehler="aus")
    if not daten["leistungen"]:
        return rueckfall
    try:
        ausgabe = llm.strukturiert(SYSTEM, json.dumps(daten, ensure_ascii=False, indent=1), schema(daten),
                                   aufgabe="formulierung", max_tokens=MAX_TOKENS["formulierung"])
    except LLMFehler as exc:
        log.warning("llm fallback aufgabe=formulierung grund=%s modell=%s", exc.art, llm.name)
        return replace(rueckfall, fehler=exc.art)
    gruende, texte, einleitung = pruefen(kb, daten, ausgabe)
    antwort = None
    if not gruende:
        antwort = replace(_zusammensetzen(kb, bericht, einleitung, texte), quelle="llm")
        gruende = vollstaendig(antwort, bericht)
    if gruende:
        log.warning("llm formulierung verworfen modell=%s gruende=%s", llm.name, ",".join(gruende[:10]))
        return replace(rueckfall, fehler="pruefung", gruende=gruende)
    log.info("llm formulierung ok modell=%s leistungen=%d", llm.name, len(texte))
    assert antwort is not None
    return antwort


__all__ = ["HINWEIS", "SYSTEM", "Abschnitt", "Antwort", "formulieren", "modell_daten", "pruefen", "schema",
           "vollstaendig", "vorlage"]
