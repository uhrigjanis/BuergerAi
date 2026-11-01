"""Konfiguration der LLM-Schicht über Umgebungsvariablen (#74).

Ohne ``BUERGERAI_LLM_ANBIETER`` ist die LLM-Schicht aus und alles läuft wie
bisher über Formular und Stichwortsuche. Schlüssel stehen nie im Repository.

| Variable | Bedeutung |
|---|---|
| ``BUERGERAI_LLM_ANBIETER`` | ``mistral`` oder ``fake``; leer = aus |
| ``BUERGERAI_LLM_MODELL`` | Modell, Standard je Anbieter (Mistral: ``mistral-small-latest``) |
| ``MISTRAL_API_KEY`` | Schlüssel für Mistral |
| ``BUERGERAI_LLM_TIMEOUT`` | Sekunden je Anfrage, Standard 20 |
| ``BUERGERAI_LLM_VERSUCHE`` | Versuche bei Rate-Limit und Serverfehlern, Standard 3 |
| ``BUERGERAI_LLM_URL`` | andere Adresse des Anbieters (Tests, Proxy) |
| ``BUERGERAI_LLM_FAKE_DATEI`` | Antworten für ``fake`` (JSON), zum Ausprobieren ohne Modell |
| ``BUERGERAI_ENV_DATEI`` | andere ``.env``-Datei (Standard: ``.env`` im aktuellen Ordner, sonst im Repository) |

Die Werte können in einer lokalen ``.env`` stehen, die Git ignoriert (Vorlage:
``.env.beispiel``). Gesetzte Umgebungsvariablen haben Vorrang. Die Datei wird
nur gelesen, nie als Shell-Code ausgeführt.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional

from .basis import LLM, LLMKonfigurationsfehler

log = logging.getLogger("buergerai.llm")

REPO = Path(__file__).resolve().parents[3]
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
PLATZHALTER = "hier-deinen-schluessel-eintragen"  # aus .env.beispiel

ANBIETER = ("mistral", "fake")  # Vertex AI (Betrieb, ADR 0009 §5) folgt
STANDARD_MODELL = {"mistral": "mistral-small-latest", "fake": "fake"}


@dataclass(frozen=True)
class Konfiguration:
    anbieter: str
    modell: str
    schluessel: Optional[str] = field(default=None, repr=False)
    timeout: float = 20.0
    versuche: int = 3
    url: Optional[str] = None
    fake_datei: Optional[str] = None

    def beschreibung(self) -> str:
        """Für Ausgaben und Logs: ohne Schlüssel."""
        teile = [f"Anbieter {self.anbieter}", f"Modell {self.modell}", f"Timeout {self.timeout:g} s",
                 f"{self.versuche} Versuche"]
        if self.anbieter != "fake":
            teile.append("Schlüssel gesetzt" if self.schluessel else "kein Schlüssel")
        if self.url:
            teile.append(f"URL {self.url}")
        return ", ".join(teile)


def _zahl(env: Mapping[str, str], name: str, standard: float, typ: type = float) -> float:
    roh = env.get(name, "").strip()
    if not roh:
        return standard
    try:
        wert = typ(roh)
    except ValueError:
        raise LLMKonfigurationsfehler(f"{name}: Zahl erwartet") from None
    if wert <= 0:
        raise LLMKonfigurationsfehler(f"{name}: muss größer als 0 sein")
    return wert


def env_datei_lesen(pfad: Path) -> dict[str, str]:
    """Liest ``NAME=wert``-Zeilen. Kommentare (#), Leerzeilen und ``export`` sind erlaubt.

    Werte in Anführungszeichen bleiben wörtlich. Ungültige Zeilen werden mit
    Zeilennummer gemeldet und übersprungen; ihr Inhalt erscheint nie im Log.
    """
    werte: dict[str, str] = {}
    for nr, zeile in enumerate(pfad.read_text(encoding="utf-8").splitlines(), 1):
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#"):
            continue
        if zeile.startswith("export "):
            zeile = zeile[len("export "):].lstrip()
        name, gleich, wert = zeile.partition("=")
        name = name.strip()
        if not gleich or not _NAME.fullmatch(name):
            log.warning("env datei=%s zeile=%d ungueltig, uebersprungen", pfad.name, nr)
            continue
        wert = wert.strip()
        if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in "\"'":
            wert = wert[1:-1]
        elif " #" in wert:
            wert = wert.split(" #", 1)[0].rstrip()
        werte[name] = wert
    return werte


def env_datei_finden(env: Optional[Mapping[str, str]] = None) -> Optional[Path]:
    """``BUERGERAI_ENV_DATEI``, sonst ``.env`` im aktuellen Ordner, sonst im Repository."""
    env = os.environ if env is None else env
    eigene = env.get("BUERGERAI_ENV_DATEI", "").strip()
    kandidaten = [Path(eigene)] if eigene else [Path.cwd() / ".env", REPO / ".env"]
    return next((p for p in kandidaten if p.is_file()), None)


def umgebung() -> dict[str, str]:
    """Werte aus der ``.env`` (falls vorhanden), überschrieben von gesetzten Umgebungsvariablen."""
    pfad = env_datei_finden()
    werte = env_datei_lesen(pfad) if pfad else {}
    werte.update(os.environ)
    return werte


def aus_umgebung(env: Optional[Mapping[str, str]] = None) -> Optional[Konfiguration]:
    """Konfiguration aus Umgebungsvariablen und ``.env``; ``None``, wenn die LLM-Schicht aus ist."""
    env = umgebung() if env is None else env
    anbieter = env.get("BUERGERAI_LLM_ANBIETER", "").strip().lower()
    if not anbieter:
        return None
    if anbieter not in ANBIETER:
        raise LLMKonfigurationsfehler(f"BUERGERAI_LLM_ANBIETER: unbekannt, erlaubt sind {', '.join(ANBIETER)}")
    schluessel = None
    if anbieter == "mistral":
        schluessel = env.get("MISTRAL_API_KEY", "").strip() or None
    if anbieter == "mistral" and not schluessel:
        raise LLMKonfigurationsfehler("MISTRAL_API_KEY fehlt")
    if schluessel == PLATZHALTER:
        raise LLMKonfigurationsfehler("MISTRAL_API_KEY ist noch der Platzhalter aus .env.beispiel")
    fake_datei = env.get("BUERGERAI_LLM_FAKE_DATEI", "").strip() or None
    if anbieter == "fake" and not fake_datei:
        raise LLMKonfigurationsfehler("BUERGERAI_LLM_FAKE_DATEI fehlt")
    return Konfiguration(
        anbieter=anbieter,
        modell=env.get("BUERGERAI_LLM_MODELL", "").strip() or STANDARD_MODELL[anbieter],
        schluessel=schluessel,
        timeout=_zahl(env, "BUERGERAI_LLM_TIMEOUT", 20.0),
        versuche=int(_zahl(env, "BUERGERAI_LLM_VERSUCHE", 3, int)),
        url=env.get("BUERGERAI_LLM_URL", "").strip() or None,
        fake_datei=fake_datei,
    )


def erzeugen(konfig: Konfiguration) -> LLM:
    if konfig.anbieter == "mistral":
        from .mistral import MistralLLM

        return MistralLLM(konfig)
    if konfig.anbieter == "fake":
        from .fake import FakeLLM

        return FakeLLM.aus_datei(konfig.fake_datei or "")
    raise LLMKonfigurationsfehler(f"Anbieter {konfig.anbieter!r} unbekannt")


def llm_aus_umgebung(env: Optional[Mapping[str, str]] = None) -> Optional[LLM]:
    """Für die Anwendung: ein LLM oder ``None``. Fehler in der Konfiguration schalten die LLM-Schicht aus."""
    try:
        konfig = aus_umgebung(env)
        return erzeugen(konfig) if konfig else None
    except LLMKonfigurationsfehler as exc:
        log.warning("llm aus grund=konfiguration meldung=%s", exc)
        return None
