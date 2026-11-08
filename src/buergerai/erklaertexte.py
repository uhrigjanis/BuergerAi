"""Erklärtexte je Leistung und Glossar (#113): Textregeln, Übersicht und Abnahme.

Erklärtexte stehen in ``data/fachmodule/<id>/erklaerungen.json``, das Glossar in
``data/kern/glossar.json``. Beide Dateien sind maschinell formatiert
(``json.dumps(..., indent=2, ensure_ascii=False)``), damit die Abnahme sie
gefahrlos neu schreiben kann.

Textregeln (``text_pruefen``), geprüft beim Laden der Wissensbasis:

- keine Ziffern und keine Mengen wie „drei Wochen“: Beträge, Fristen und Grenzen
  kommen strukturiert aus Leistung und Variante, so veraltet kein Text unbemerkt;
- keine Beträge („Euro“, „Prozent“), keine Paragraphen (die Rechtsgrundlage steht in den Quellen);
- keine Links und Adressen (Links setzt das Programm);
- keine Zusagen („sicher“, „Sie bekommen …“): ob ein Anspruch besteht, sagt allein die Engine.

``verifiziert`` setzt nur ein Mensch über ``buergerai erklaerungen --abnehmen`` (ANF-QS-02).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:  # pragma: no cover
    from .wissensbasis import Wissensbasis

MAX_LAENGE = {"was": 450, "danach": 400, "achtung": 350, "glossar": 320}
MIN_LAENGE = 40
DATEI_ERKLAERUNGEN = "erklaerungen.json"
DATEI_GLOSSAR = "glossar.json"

_ZAHLWORT = (r"(?:ein|eine|einen|einem|einer|eines|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|elf|zwölf|"
             r"zwanzig|dreißig|vierzig|fünfzig|hundert|tausend|halbe?n?|anderthalb|"
             r"erste[nmrs]?|zweite[nmrs]?|dritte[nmrs]?|vierte[nmrs]?|fünfte[nmrs]?|sechste[nmrs]?)")
_EINHEIT = (r"(?:tag|tage|tagen|tages|arbeitstage?n?|kalendertage?n?|woche|wochen|monat|monate|monaten|monats|"
            r"jahr|jahre|jahren|jahres|lebensjahr\w*|lebensmonat\w*|stunden?|euro|prozent)")
REGELN: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("zahl", re.compile(r"\d")),
    ("menge", re.compile(rf"\b{_ZAHLWORT}\s+{_EINHEIT}\b", re.IGNORECASE)),
    ("betrag", re.compile(r"€|%|\b(euro|prozent)\b", re.IGNORECASE)),
    ("paragraph", re.compile(r"§|\bArt\.\s")),
    ("link", re.compile(r"https?://|www\.|\S+@\S+\.\w+|\b[\w-]+\.(?:de|com|org|eu|net|info)\b", re.IGNORECASE)),
    ("zusage", re.compile(r"\b(garantiert|ganz sicher|sicher|auf jeden fall|definitiv|mit sicherheit|zweifellos|"
                          r"in jedem fall)\b", re.IGNORECASE)),
    # wie die Nachprüfung der Antworttexte (llm/formulierung.py): ohne Unterschied von Groß- und Kleinschreibung
    ("zusage", re.compile(r"\bSie (bekommen|erhalten)\b|\bSie (haben|hätten) (\w+ )?Anspruch\b|"
                          r"\b(steht|stehen) Ihnen\b", re.IGNORECASE)),
)


def text_pruefen(text: Any, art: str) -> list[str]:
    """Verstöße eines Erklär- oder Glossartextes als kurze Codes (leer = in Ordnung)."""
    if not isinstance(text, str) or not text.strip():
        return ["leer"]
    fehler = [f"{code}: {m.group(0)!r}" for code, muster in REGELN for m in [muster.search(text)] if m]
    if len(text) > MAX_LAENGE[art]:
        fehler.append(f"zu lang ({len(text)} > {MAX_LAENGE[art]} Zeichen)")
    if art in ("was", "glossar") and len(text) < MIN_LAENGE:
        fehler.append(f"zu kurz ({len(text)} < {MIN_LAENGE} Zeichen)")
    if text != " ".join(text.split()):
        fehler.append("Leerzeichen am Rand oder doppelt")
    return fehler


def formatiert(inhalt: Any) -> str:
    """Kanonische Form der Dateien für Erklärtexte und Glossar."""
    return json.dumps(inhalt, ensure_ascii=False, indent=2) + "\n"


# ------------------------------------------------------------------ Übersicht
@dataclass(frozen=True)
class Eintrag:
    art: str  # "erklaerung" oder "glossar"
    id: str
    titel: str
    pruefstatus: str
    datei: Path


def eintraege(kb: "Wissensbasis") -> list[Eintrag]:
    """Alle Erklärtexte und Glossarbegriffe mit Prüfstatus, nach Datei sortiert."""
    ergebnis = [Eintrag("erklaerung", e.leistung_id, kb.leistungen[e.leistung_id].name, e.pruefstatus.value,
                        _datei(kb, e.modul, DATEI_ERKLAERUNGEN))
                for e in kb.erklaerungen.values() if e.leistung_id in kb.leistungen]
    ergebnis += [Eintrag("glossar", g.id, g.begriff, g.pruefstatus.value, _datei(kb, "kern", DATEI_GLOSSAR))
                 for g in kb.glossar.values()]
    return sorted(ergebnis, key=lambda x: (str(x.datei), x.id))


def _datei(kb: "Wissensbasis", modul: Optional[str], name: str) -> Path:
    for d in kb.dateien:
        if d.name == name and (d.parent.name == modul):
            return d
    raise FileNotFoundError(f"{name} für {modul} nicht gefunden")


def ohne_erklaerung(kb: "Wissensbasis") -> list[str]:
    return sorted(lid for lid in kb.leistungen if lid not in kb.erklaerungen)


def unbenutzte_begriffe(kb: "Wissensbasis") -> list[str]:
    benutzt = {b for e in kb.erklaerungen.values() for b in e.begriffe}
    return sorted(g for g in kb.glossar if g not in benutzt)


# ------------------------------------------------------------------ Abnahme
class AbnahmeFehler(ValueError):
    pass


def _finden(kb: "Wissensbasis", eintrag_id: str) -> tuple[Path, str, str]:
    """Datei, Sammlung und Schlüsselfeld für eine Leistungs-ID (Erklärtext) oder Glossar-ID."""
    if eintrag_id in kb.erklaerungen:
        e = kb.erklaerungen[eintrag_id]
        return _datei(kb, e.modul, DATEI_ERKLAERUNGEN), "erklaerungen", "leistung_id"
    if eintrag_id in kb.glossar:
        return _datei(kb, "kern", DATEI_GLOSSAR), "glossar", "id"
    raise AbnahmeFehler(f"Kein Erklärtext und kein Glossarbegriff mit der ID {eintrag_id}")


def status_setzen(kb: "Wissensbasis", eintrag_id: str, pruefstatus: str, von: Optional[str] = None,
                  am: Optional[date] = None) -> Path:
    """Setzt den Prüfstatus eines Erklärtextes oder Glossarbegriffs und schreibt die Datei neu.

    ``verifiziert`` braucht ``von`` (ein Mensch, ANF-QS-02). Andere Status löschen
    ``geprueft_am`` und ``geprueft_von``.
    """
    if pruefstatus == "verifiziert" and not (von and von.strip()):
        raise AbnahmeFehler("Für 'verifiziert' bitte mit --von angeben, wer den Text geprüft hat")
    datei, sammlung, feld = _finden(kb, eintrag_id)
    text = datei.read_text(encoding="utf-8")
    inhalt = json.loads(text)
    if formatiert(inhalt) != text:
        raise AbnahmeFehler(f"{datei} ist nicht maschinell formatiert; bitte zuerst 'buergerai erklaerungen --formatieren'")
    for eintrag in inhalt[sammlung]:
        if eintrag.get(feld) == eintrag_id:
            eintrag["pruefstatus"] = pruefstatus
            if pruefstatus == "verifiziert":
                eintrag["geprueft_am"] = (am or date.today()).isoformat()
                eintrag["geprueft_von"] = von.strip() if von else None
            else:
                eintrag.pop("geprueft_am", None)
                eintrag.pop("geprueft_von", None)
            break
    datei.write_text(formatiert(inhalt), encoding="utf-8")
    return datei


def formatieren(kb: "Wissensbasis") -> list[Path]:
    """Bringt alle Dateien mit Erklärtexten und das Glossar in die kanonische Form."""
    geaendert = []
    for d in kb.dateien:
        if d.name in (DATEI_ERKLAERUNGEN, DATEI_GLOSSAR):
            text = d.read_text(encoding="utf-8")
            neu = formatiert(json.loads(text))
            if neu != text:
                d.write_text(neu, encoding="utf-8")
                geaendert.append(d)
    return geaendert
