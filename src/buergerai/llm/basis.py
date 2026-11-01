"""Gemeinsame Schnittstelle der LLM-Anbieter (ADR 0009, #74).

Der Rest des Codes kennt nur ``LLM`` und ``LLMFehler``. Welcher Anbieter dahinter
steckt, entscheidet die Konfiguration. Jeder Fehler ist ein ``LLMFehler``; der
Aufrufer fällt dann auf Stichwortsuche bzw. Formular zurück (``mit_fallback``).

Datenschutz (ADR 0009 §3): Weder Fehlermeldungen noch Logs enthalten Freitexte,
Prompts, Antworten oder Schlüssel. Protokolliert werden nur Aufgabe, Modell,
Dauer, Tokenzahlen und Ergebnis.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, Generic, Optional, Protocol, TypeVar

log = logging.getLogger("buergerai.llm")


class LLMFehler(Exception):
    """Der LLM-Aufruf hat kein verwertbares Ergebnis geliefert. Meldungen enthalten keine Freitexte."""

    art = "fehler"


class LLMTimeout(LLMFehler):
    art = "timeout"


class LLMRateLimit(LLMFehler):
    art = "rate_limit"


class LLMAblehnung(LLMFehler):
    art = "ablehnung"


class LLMUngueltigeAusgabe(LLMFehler):
    art = "ungueltig"


class LLMDienstfehler(LLMFehler):
    """Netzwerk- oder Serverfehler, auch nach Wiederholungen."""

    art = "dienst"


class LLMKonfigurationsfehler(LLMFehler):
    """Anbieter unbekannt, Schlüssel fehlt oder wird abgelehnt."""

    art = "konfiguration"


FEHLERARTEN: dict[str, type[LLMFehler]] = {
    k.art: k for k in (LLMTimeout, LLMRateLimit, LLMAblehnung, LLMUngueltigeAusgabe, LLMDienstfehler,
                       LLMKonfigurationsfehler)
}


class LLM(Protocol):
    """Was jeder Anbieter können muss. ``aufgabe`` (z. B. "router") steht in Logs und Fake-Antworten."""

    name: str

    def strukturiert(self, system: str, eingabe: str, schema: dict[str, Any], *, aufgabe: str,
                     max_tokens: int = 1024) -> dict[str, Any]:
        """Antwort als JSON-Objekt nach ``schema``. Die genaue Prüfung der Werte macht der Aufrufer (#75)."""
        ...

    def text(self, system: str, eingabe: str, *, aufgabe: str, max_tokens: int = 1024) -> str:
        ...


def json_objekt(roh: Optional[str]) -> dict[str, Any]:
    """Wandelt die Modellantwort in ein JSON-Objekt; der Inhalt landet nie in der Fehlermeldung."""
    if not roh or not roh.strip():
        raise LLMUngueltigeAusgabe("leere Antwort")
    try:
        daten = json.loads(roh)
    except json.JSONDecodeError as exc:
        raise LLMUngueltigeAusgabe(f"kein gültiges JSON (Zeile {exc.lineno}, Spalte {exc.colno})") from None
    if not isinstance(daten, dict):
        raise LLMUngueltigeAusgabe(f"JSON-Objekt erwartet, war {type(daten).__name__}")
    return daten


def grob_pruefen(daten: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    """Pflichtfelder vorhanden und keine fremden Felder, wenn das Schema sie verbietet.

    Typen und erlaubte Werte prüft die Validierung aus #75.
    """
    fehlend = [k for k in schema.get("required", []) if k not in daten]
    if fehlend:
        raise LLMUngueltigeAusgabe("Pflichtfelder fehlen: " + ", ".join(fehlend))
    if schema.get("additionalProperties") is False:
        fremd = sorted(set(daten) - set(schema.get("properties", {})))
        if fremd:
            raise LLMUngueltigeAusgabe(f"{len(fremd)} Felder außerhalb des Schemas")
    return daten


def protokollieren(llm: str, aufgabe: str, dauer: float, ergebnis: str,
                   eingabe_tokens: Optional[int] = None, ausgabe_tokens: Optional[int] = None) -> None:
    """Ein Logeintrag je Aufruf, ohne personenbezogene Daten (ADR 0009 §3)."""
    log.info("llm aufgabe=%s modell=%s dauer_ms=%d ergebnis=%s tokens_ein=%s tokens_aus=%s",
             aufgabe, llm, round(dauer * 1000), ergebnis,
             "-" if eingabe_tokens is None else eingabe_tokens,
             "-" if ausgabe_tokens is None else ausgabe_tokens)


T = TypeVar("T")


@dataclass
class Ergebnis(Generic[T]):
    wert: T
    quelle: str  # "llm" oder "fallback"
    fehler: Optional[str] = None  # Fehlerart, "aus" wenn kein LLM konfiguriert ist


def mit_fallback(llm: Optional[LLM], aufruf: Callable[[LLM], T], fallback: Callable[[], T]) -> Ergebnis[T]:
    """Ruft das LLM auf; ohne LLM oder bei jedem ``LLMFehler`` gilt der Fallback.

    Andere Ausnahmen sind Programmfehler und werden nicht verschluckt.
    """
    if llm is None:
        return Ergebnis(fallback(), "fallback", "aus")
    try:
        return Ergebnis(aufruf(llm), "llm")
    except LLMFehler as exc:
        log.warning("llm fallback grund=%s modell=%s", exc.art, llm.name)
        return Ergebnis(fallback(), "fallback", exc.art)
