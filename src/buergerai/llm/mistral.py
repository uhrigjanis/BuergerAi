"""Mistral La Plateforme über die REST-API (ADR 0009 §5a, #74).

Nur die Standardbibliothek (``urllib``), deshalb kein zusätzliches Paket.
Für die Entwicklung mit dem kostenlosen Plan „Experiment“: nur ausgedachte
Texte, Training-Opt-out in der Mistral-Konsole einschalten.

Bei HTTP 429 und Serverfehlern wird mit Wartezeit wiederholt (``Retry-After``
oder 1, 2, 4 … Sekunden, höchstens 30). Danach gilt ein ``LLMFehler``.
"""

from __future__ import annotations

import json
import re
import socket
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Optional

from .basis import (
    LLMAblehnung,
    LLMDienstfehler,
    LLMFehler,
    LLMKonfigurationsfehler,
    LLMRateLimit,
    LLMTimeout,
    LLMUngueltigeAusgabe,
    grob_pruefen,
    json_objekt,
    protokollieren,
)
from .konfiguration import Konfiguration

URL = "https://api.mistral.ai/v1/chat/completions"
# Nur kurze Kennungen aus der Fehlerantwort übernehmen, nie den Fehlertext (kann die Eingabe enthalten)
_KENNUNG = re.compile(r"[A-Za-z0-9_.-]{1,64}")
ZERTIFIKAT_HINWEIS = (
    "TLS-Zertifikat nicht prüfbar: Python findet keine passenden Stammzertifikate. "
    "Auf dem Mac mit Python von python.org einmal 'Install Certificates.command' ausführen, "
    "im Firmennetz BUERGERAI_LLM_CA_DATEI auf das Firmenzertifikat setzen (README, LLM-Schicht)"
)
MAX_WARTEN = 30.0


class MistralLLM:
    def __init__(self, konfig: Konfiguration, schlafen: Callable[[float], None] = time.sleep):
        if not konfig.schluessel:
            raise LLMKonfigurationsfehler("MISTRAL_API_KEY fehlt")
        self.konfig = konfig
        self.name = f"mistral/{konfig.modell}"
        self._schlafen = schlafen
        self._ssl: Optional[ssl.SSLContext] = None
        if konfig.ca_datei:
            try:
                self._ssl = ssl.create_default_context(cafile=str(Path(konfig.ca_datei).expanduser()))
            except (OSError, ssl.SSLError):
                raise LLMKonfigurationsfehler("BUERGERAI_LLM_CA_DATEI: keine gültigen Zertifikate (PEM)") from None

    # ------------------------------------------------------------ Schnittstelle

    def strukturiert(self, system: str, eingabe: str, schema: dict[str, Any], *, aufgabe: str,
                     max_tokens: int = 1024) -> dict[str, Any]:
        format_ = {"type": "json_schema", "json_schema": {"name": aufgabe, "schema": schema, "strict": True}}
        inhalt = self._aufruf(system, eingabe, aufgabe, max_tokens, format_)
        return grob_pruefen(json_objekt(inhalt), schema)

    def text(self, system: str, eingabe: str, *, aufgabe: str, max_tokens: int = 1024) -> str:
        return self._aufruf(system, eingabe, aufgabe, max_tokens, None)

    # ------------------------------------------------------------ intern

    def _aufruf(self, system: str, eingabe: str, aufgabe: str, max_tokens: int,
                format_: Optional[dict[str, Any]]) -> str:
        body: dict[str, Any] = {
            "model": self.konfig.modell,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": eingabe}],
            "temperature": 0,
            "max_tokens": max_tokens,
        }
        if format_:
            body["response_format"] = format_
        start = time.monotonic()
        try:
            daten = self._senden(body)
            inhalt, tokens = self._auswerten(daten)
        except LLMFehler as exc:
            protokollieren(self.name, aufgabe, time.monotonic() - start, exc.art)
            raise
        protokollieren(self.name, aufgabe, time.monotonic() - start, "ok", *tokens)
        return inhalt

    def _senden(self, body: dict[str, Any]) -> dict[str, Any]:
        anfrage = urllib.request.Request(
            self.konfig.url or URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.konfig.schluessel}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        for versuch in range(1, self.konfig.versuche + 1):
            letzter = versuch == self.konfig.versuche
            try:
                with urllib.request.urlopen(anfrage, timeout=self.konfig.timeout, context=self._ssl) as antwort:
                    return json.loads(antwort.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                status = exc.code
                kennung = self._kennung(exc)
                if status in (401, 403):
                    raise LLMKonfigurationsfehler(f"Schlüssel abgelehnt (HTTP {status}{kennung})") from None
                if status == 429 or status >= 500:
                    if letzter:
                        fehler = LLMRateLimit if status == 429 else LLMDienstfehler
                        meldung = f"HTTP {status} nach {versuch} Versuchen{kennung}"
                        if "capacity" in kennung:
                            meldung += (": Modell im kostenlosen Plan ausgelastet, später erneut versuchen "
                                        "oder ein anderes Modell wählen (BUERGERAI_LLM_MODELL)")
                        elif status == 429:
                            meldung += ": Limit erreicht, kurz warten und erneut versuchen"
                        raise fehler(meldung) from None
                    self._schlafen(self._wartezeit(exc.headers.get("Retry-After"), versuch))
                    continue
                raise LLMDienstfehler(f"HTTP {status}{kennung}") from None
            except (TimeoutError, socket.timeout):
                raise LLMTimeout(f"keine Antwort nach {self.konfig.timeout:g} s") from None
            except urllib.error.URLError as exc:
                if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                    raise LLMTimeout(f"keine Antwort nach {self.konfig.timeout:g} s") from None
                if isinstance(exc.reason, ssl.SSLCertVerificationError):
                    raise LLMDienstfehler(ZERTIFIKAT_HINWEIS) from None
                raise LLMDienstfehler(f"keine Verbindung ({type(exc.reason).__name__})") from None
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise LLMDienstfehler("Antwort des Dienstes ist kein JSON") from None
        raise LLMDienstfehler("keine Antwort")  # nur bei versuche < 1

    @staticmethod
    def _kennung(exc: urllib.error.HTTPError) -> str:
        """Fehlertyp und -code aus der Antwort, z. B. " (service_tier_capacity_exceeded, 3505)".

        Übernommen werden nur kurze Kennungen aus den Feldern ``type`` und ``code``,
        nie ``message`` oder ``detail``: Diese können die Eingabe enthalten.
        """
        try:
            daten = json.loads(exc.read(4096).decode("utf-8"))
        except Exception:  # Fehlerantwort ohne JSON: dann eben ohne Kennung
            return ""
        if not isinstance(daten, dict):
            return ""
        teile = [str(daten[k]) for k in ("type", "code") if daten.get(k) is not None]
        teile = [t for t in teile if _KENNUNG.fullmatch(t)]
        return f" ({', '.join(teile)})" if teile else ""

    @staticmethod
    def _wartezeit(retry_after: Optional[str], versuch: int) -> float:
        try:
            if retry_after:
                return min(max(float(retry_after), 0.0), MAX_WARTEN)
        except ValueError:
            pass
        return min(2.0 ** (versuch - 1), MAX_WARTEN)

    @staticmethod
    def _auswerten(daten: dict[str, Any]) -> tuple[str, tuple[Optional[int], Optional[int]]]:
        try:
            wahl = daten["choices"][0]
            inhalt = wahl["message"].get("content")
        except (KeyError, IndexError, TypeError, AttributeError):
            raise LLMUngueltigeAusgabe("Antwort ohne choices[0].message") from None
        grund = wahl.get("finish_reason")
        if grund in ("length", "model_length"):
            raise LLMUngueltigeAusgabe("Antwort abgeschnitten (max_tokens)")
        if grund == "content_filter":
            raise LLMAblehnung("vom Anbieter abgelehnt")
        if grund == "error":
            raise LLMDienstfehler("Anbieter meldet einen Fehler")
        if isinstance(inhalt, list):  # Mistral kann Inhalte als Liste von Teilen liefern
            inhalt = "".join(t.get("text", "") for t in inhalt if isinstance(t, dict))
        if not isinstance(inhalt, str) or not inhalt.strip():
            raise LLMUngueltigeAusgabe("leere Antwort")
        nutzung = daten.get("usage") or {}
        return inhalt, (nutzung.get("prompt_tokens"), nutzung.get("completion_tokens"))
