"""Fake-Modell für Tests und CI: vorbereitete Antworten, kein Netz, kein Schlüssel (#74).

Antworten stehen als Liste, im Code oder in einer JSON-Datei::

    [
      {"aufgabe": "router", "enthaelt": "schwanger", "antwort": {"lebenslagen": ["geburt"]}},
      {"aufgabe": "router", "fehler": "timeout"},
      {"aufgabe": "antwort", "antwort": "Sie können Elterngeld beantragen."}
    ]

Es gilt der erste Eintrag, dessen ``aufgabe`` passt (fehlt sie: jede Aufgabe) und
dessen ``enthaelt`` in der Eingabe vorkommt (fehlt es: jede Eingabe). ``fehler``
löst den passenden ``LLMFehler`` aus (timeout, rate_limit, ablehnung, ungueltig,
dienst, konfiguration). Alle Aufrufe stehen in ``aufrufe``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional, Union

from .basis import FEHLERARTEN, LLMKonfigurationsfehler, LLMUngueltigeAusgabe, grob_pruefen, json_objekt, protokollieren


class FakeLLM:
    def __init__(self, antworten: Optional[list[dict[str, Any]]] = None, name: str = "fake"):
        self.name = name
        self.antworten = list(antworten or [])
        for a in self.antworten:
            if "fehler" in a and a["fehler"] not in FEHLERARTEN:
                raise LLMKonfigurationsfehler(f"FakeLLM: Fehlerart {a['fehler']!r} unbekannt")
            if "fehler" not in a and "antwort" not in a:
                raise LLMKonfigurationsfehler("FakeLLM: jeder Eintrag braucht 'antwort' oder 'fehler'")
        self.aufrufe: list[dict[str, Any]] = []

    @classmethod
    def aus_datei(cls, pfad: Union[str, Path]) -> "FakeLLM":
        try:
            roh = json.loads(Path(pfad).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LLMKonfigurationsfehler(f"FakeLLM: Datei {pfad} nicht lesbar ({type(exc).__name__})") from None
        return cls(roh["antworten"] if isinstance(roh, dict) else roh, name=f"fake/{Path(pfad).stem}")

    def _antwort(self, aufgabe: str, eingabe: str) -> Any:
        start = time.monotonic()
        for a in self.antworten:
            if a.get("aufgabe", aufgabe) == aufgabe and a.get("enthaelt", "") in eingabe:
                if "fehler" in a:
                    protokollieren(self.name, aufgabe, time.monotonic() - start, a["fehler"])
                    raise FEHLERARTEN[a["fehler"]]("FakeLLM: vorbereiteter Fehler")
                protokollieren(self.name, aufgabe, time.monotonic() - start, "ok")
                return a["antwort"]
        protokollieren(self.name, aufgabe, time.monotonic() - start, "ungueltig")
        raise LLMUngueltigeAusgabe(f"FakeLLM: keine vorbereitete Antwort für Aufgabe {aufgabe!r}")

    def strukturiert(self, system: str, eingabe: str, schema: dict[str, Any], *, aufgabe: str,
                     max_tokens: int = 1024) -> dict[str, Any]:
        self.aufrufe.append({"art": "strukturiert", "aufgabe": aufgabe, "system": system, "eingabe": eingabe,
                             "schema": schema, "max_tokens": max_tokens})
        antwort = self._antwort(aufgabe, eingabe)
        daten = json_objekt(antwort) if isinstance(antwort, str) else antwort
        if not isinstance(daten, dict):
            raise LLMUngueltigeAusgabe("FakeLLM: Antwort ist kein JSON-Objekt")
        return grob_pruefen(dict(daten), schema)

    def text(self, system: str, eingabe: str, *, aufgabe: str, max_tokens: int = 1024) -> str:
        self.aufrufe.append({"art": "text", "aufgabe": aufgabe, "system": system, "eingabe": eingabe,
                             "max_tokens": max_tokens})
        antwort = self._antwort(aufgabe, eingabe)
        if not isinstance(antwort, str) or not antwort.strip():
            raise LLMUngueltigeAusgabe("FakeLLM: Text erwartet")
        return antwort
