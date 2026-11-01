"""LLM-Adapter (Phase 3, ADR 0009, #74).

Der Rest des Codes nutzt nur diese Schnittstelle::

    from buergerai.llm import llm_aus_umgebung, mit_fallback

    llm = llm_aus_umgebung()            # None, wenn die LLM-Schicht aus ist
    ergebnis = mit_fallback(llm,
                            lambda m: m.strukturiert(system, text, schema, aufgabe="router"),
                            lambda: stichwortsuche(text))

Anbieterpakete werden nur hier und nur innerhalb von Funktionen geladen (ANF-LLM-01).
"""

from .basis import (
    LLM,
    Ergebnis,
    LLMAblehnung,
    LLMDienstfehler,
    LLMFehler,
    LLMKonfigurationsfehler,
    LLMRateLimit,
    LLMTimeout,
    LLMUngueltigeAusgabe,
    mit_fallback,
)
from .fake import FakeLLM
from .konfiguration import Konfiguration, aus_umgebung, env_datei_finden, erzeugen, llm_aus_umgebung

__all__ = [
    "LLM", "Ergebnis", "FakeLLM", "Konfiguration", "LLMAblehnung", "LLMDienstfehler", "LLMFehler",
    "LLMKonfigurationsfehler", "LLMRateLimit", "LLMTimeout", "LLMUngueltigeAusgabe", "aus_umgebung",
    "env_datei_finden", "erzeugen", "llm_aus_umgebung", "mit_fallback",
]
