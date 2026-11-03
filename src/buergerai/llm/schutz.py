"""Schutzregeln vor dem LLM (#82, ADR 0009 §8): Code statt Prompt.

- ``MAX_TOKENS``: feste Obergrenze der Antwortlänge je Aufgabe.
- ``notlage_im_text``: Stichwortliste, damit der Notlage-Hinweis auch ohne LLM erscheint.
- ``RateLimit``: Freitext-Anfragen je IP; die IP liegt nur im Speicher und nur,
  solange sie für das Zeitfenster gebraucht wird.
- ``GeschuetztesLLM``: Hülle um ein ``LLM`` mit Aufrufdeckel je Tag und Monat und
  einem kurzen Cache für gleiche Anfragen. Ist der Deckel erreicht, gibt es einen
  ``LLMKostendeckel`` und der Aufrufer fällt wie bei jedem ``LLMFehler`` zurück.

Der Deckel zählt Aufrufe, nicht Tokens. Mit der Tokenzählung (#80) wird er auf
Tokens umgestellt. Rate-Limit, Deckel und Cache leben im Speicher des Prozesses
und beginnen nach einem Neustart von vorn.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import threading
import time
from collections import OrderedDict, deque
from datetime import date
from typing import Any, Callable, Mapping, Optional

from .basis import LLM, LLMKostendeckel, log

MAX_TOKENS = {"router": 600, "extraktion": 1500}

# ------------------------------------------------------------------ Notlagen
# Bewusst eng gefasst: lieber ein Hinweis zu viel als einer zu wenig, aber normale
# Lebenslagen (Todesfall, Pflege, Jobverlust) dürfen ihn nicht auslösen.
NOTLAGE_MUSTER = [
    r"suizid", r"selbstmord", r"umbringen", r"(mir|mich|uns) das leben (zu )?nehmen",
    r"nicht mehr leben (will|möchte)", r"will nicht mehr leben", r"möchte nicht mehr leben",
    r"(schlägt|schlagen|verprügelt|würgt|bedroht) (mich|uns)", r"häusliche gewalt", r"vergewaltig",
    r"obdachlos", r"(keinen|kein) schlafplatz", r"auf der straße (schlafen|leben|sitzen)",
    r"nichts (mehr )?(gegessen|zu essen)", r"atmet nicht", r"bewusstlos",
]
_NOTLAGE = re.compile("|".join(f"(?:{m})" for m in NOTLAGE_MUSTER), re.IGNORECASE)


def notlage_im_text(text: str) -> bool:
    """Deutet der Text auf eine akute Notlage hin? Ohne Modellaufruf."""
    return bool(_NOTLAGE.search(" ".join(text.split())))


# ------------------------------------------------------------------ Rate-Limit
class RateLimit:
    """Höchstens ``pro_minute`` und ``pro_tag`` Anfragen je Schlüssel (IP), gleitendes Fenster."""

    def __init__(self, pro_minute: int = 10, pro_tag: int = 100, uhr: Callable[[], float] = time.monotonic):
        self.pro_minute, self.pro_tag, self.uhr = pro_minute, pro_tag, uhr
        self._zeiten: dict[str, deque[float]] = {}
        self._sperre = threading.Lock()

    def erlaubt(self, schluessel: str) -> bool:
        """Zählt die Anfrage, wenn sie erlaubt ist. Abgelehnte Anfragen zählen nicht."""
        jetzt = self.uhr()
        with self._sperre:
            self._aufraeumen(jetzt)
            zeiten = self._zeiten.setdefault(schluessel, deque())
            letzte_minute = sum(1 for t in zeiten if jetzt - t < 60)
            if len(zeiten) >= self.pro_tag or letzte_minute >= self.pro_minute:
                return False
            zeiten.append(jetzt)
            return True

    def _aufraeumen(self, jetzt: float) -> None:
        for schluessel in list(self._zeiten):
            zeiten = self._zeiten[schluessel]
            while zeiten and jetzt - zeiten[0] >= 86400:
                zeiten.popleft()
            if not zeiten:
                del self._zeiten[schluessel]  # IP nicht länger behalten als nötig (ADR 0009 §3)

    def anzahl_schluessel(self) -> int:
        with self._sperre:
            self._aufraeumen(self.uhr())
            return len(self._zeiten)


# ------------------------------------------------------------------ Deckel und Cache
class Aufrufdeckel:
    """Höchstens ``pro_tag`` und ``pro_monat`` Modellaufrufe; danach bis zum nächsten Zeitraum aus."""

    def __init__(self, pro_tag: int, pro_monat: int, heute: Callable[[], date] = date.today):
        self.pro_tag, self.pro_monat, self.heute = pro_tag, pro_monat, heute
        self._tag: tuple[Optional[date], int] = (None, 0)
        self._monat: tuple[Optional[tuple[int, int]], int] = (None, 0)
        self._sperre = threading.Lock()

    def belasten(self) -> None:
        tag = self.heute()
        monat = (tag.year, tag.month)
        with self._sperre:
            n_tag = self._tag[1] if self._tag[0] == tag else 0
            n_monat = self._monat[1] if self._monat[0] == monat else 0
            if n_tag >= self.pro_tag or n_monat >= self.pro_monat:
                log.warning("llm kostendeckel erreicht zeitraum=%s", "tag" if n_tag >= self.pro_tag else "monat")
                raise LLMKostendeckel("Kostendeckel erreicht")
            self._tag, self._monat = (tag, n_tag + 1), (monat, n_monat + 1)


class GeschuetztesLLM:
    """Gleiche Schnittstelle wie ``LLM``: erst Cache, dann Deckel, dann das Modell."""

    def __init__(self, llm: LLM, deckel: Aufrufdeckel, cache_sekunden: float = 600, cache_max: int = 256,
                 uhr: Callable[[], float] = time.monotonic):
        self.llm, self.deckel, self.name = llm, deckel, llm.name
        self.cache_sekunden, self.cache_max, self.uhr = cache_sekunden, cache_max, uhr
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._sperre = threading.Lock()

    @staticmethod
    def _schluessel(*teile: Any) -> str:
        # Nur der Hash steht im Cache-Schlüssel, nicht der Text
        roh = json.dumps(teile, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(roh.encode("utf-8")).hexdigest()

    def _gecacht(self, schluessel: str, aufrufen: Callable[[], Any]) -> Any:
        jetzt = self.uhr()
        with self._sperre:
            for k in [k for k, (t, _) in self._cache.items() if jetzt - t >= self.cache_sekunden]:
                del self._cache[k]
            if schluessel in self._cache:
                self._cache.move_to_end(schluessel)
                return copy.deepcopy(self._cache[schluessel][1])
        self.deckel.belasten()
        wert = aufrufen()  # Fehler werden nicht gecacht
        with self._sperre:
            self._cache[schluessel] = (jetzt, copy.deepcopy(wert))
            while len(self._cache) > self.cache_max:
                self._cache.popitem(last=False)
        return wert

    def strukturiert(self, system: str, eingabe: str, schema: dict[str, Any], *, aufgabe: str,
                     max_tokens: int = 1024) -> dict[str, Any]:
        k = self._schluessel("strukturiert", aufgabe, max_tokens, system, eingabe, schema)
        return self._gecacht(k, lambda: self.llm.strukturiert(system, eingabe, schema, aufgabe=aufgabe,
                                                              max_tokens=max_tokens))

    def text(self, system: str, eingabe: str, *, aufgabe: str, max_tokens: int = 1024) -> str:
        k = self._schluessel("text", aufgabe, max_tokens, system, eingabe)
        return self._gecacht(k, lambda: self.llm.text(system, eingabe, aufgabe=aufgabe, max_tokens=max_tokens))


STANDARD_DECKEL_TAG = 1000
STANDARD_DECKEL_MONAT = 10000


def schuetzen(llm: LLM, env: Optional[Mapping[str, str]] = None) -> GeschuetztesLLM:
    """Hülle für den Betrieb; Grenzen aus ``BUERGERAI_LLM_MAX_AUFRUFE_TAG`` und ``..._MONAT``.

    Ungültige Werte sind ein ``LLMKonfigurationsfehler`` (die Anwendung schaltet die LLM-Schicht dann aus).
    """
    from .konfiguration import _zahl, umgebung

    env = umgebung() if env is None else env
    deckel = Aufrufdeckel(int(_zahl(env, "BUERGERAI_LLM_MAX_AUFRUFE_TAG", STANDARD_DECKEL_TAG, int)),
                          int(_zahl(env, "BUERGERAI_LLM_MAX_AUFRUFE_MONAT", STANDARD_DECKEL_MONAT, int)))
    return GeschuetztesLLM(llm, deckel)


__all__ = ["MAX_TOKENS", "NOTLAGE_MUSTER", "Aufrufdeckel", "GeschuetztesLLM", "RateLimit", "notlage_im_text",
           "schuetzen"]
