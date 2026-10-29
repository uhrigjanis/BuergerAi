"""Link-Prüfung der Quellen (#62): Ist jede URL erreichbar?

Nur Standardbibliothek (ADR 0002). Ruft jede URL einmal per GET ab, liest den
Inhalt aber nicht. Proxy-Einstellungen aus der Umgebung (HTTPS_PROXY) gelten.
"""

from __future__ import annotations

import http.client
import socket
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Iterable, Optional
from urllib.parse import urlsplit

from . import __version__

USER_AGENT = f"BuergerAI-Linkpruefung/{__version__} (+https://github.com/uhrigjanis/BuergerAi)"

OK = "ok"
UMLEITUNG = "umleitung"  # auf einen anderen Host – Quelle eventuell umgezogen
FEHLER = "fehler"  # HTTP 4xx/5xx
NICHT_ERREICHBAR = "nicht_erreichbar"  # DNS, Verbindung, Zeitüberschreitung, Proxy


@dataclass(frozen=True)
class Linkergebnis:
    url: str
    status: str
    code: Optional[int] = None
    ziel: Optional[str] = None  # Endadresse nach Umleitungen
    meldung: str = ""

    @property
    def problem(self) -> bool:
        return self.status != OK


# Hosts, auf die ein Bot-Schutz umleitet: die Seite ist nicht umgezogen, nur für Skripte gesperrt.
BOT_SCHUTZ_HOSTS = ("validate.perfdrive.com",)


def url_kodieren(url: str) -> str:
    """Umlaute und andere Nicht-ASCII-Zeichen im Pfad prozentkodieren; Vorhandenes bleibt."""
    return urllib.parse.quote(url, safe=":/?#[]@!$&'()*+,;=%~")


def _host(url: str) -> str:
    host = urlsplit(url).hostname or ""
    return host[4:] if host.startswith("www.") else host


def pruefe_url(url: str, timeout: float = 15.0,
               oeffner: Optional[urllib.request.OpenerDirector] = None) -> Linkergebnis:
    oeffner = oeffner or urllib.request.build_opener()
    try:
        anfrage = urllib.request.Request(url_kodieren(url), headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        with oeffner.open(anfrage, timeout=timeout) as antwort:
            ziel = antwort.geturl()
            code = antwort.status
    except urllib.error.HTTPError as exc:
        return Linkergebnis(url, FEHLER, exc.code, meldung=f"HTTP {exc.code} {exc.reason}")
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as exc:
        grund = getattr(exc, "reason", exc)
        return Linkergebnis(url, NICHT_ERREICHBAR, meldung=str(grund))
    except (ValueError, http.client.HTTPException) as exc:  # z. B. Leerzeichen in der URL
        return Linkergebnis(url, FEHLER, meldung=f"ungültige URL oder Antwort: {exc}")
    if (urlsplit(ziel).hostname or "") in BOT_SCHUTZ_HOSTS:
        return Linkergebnis(url, NICHT_ERREICHBAR, code, ziel, f"gesperrt (Bot-Schutz {urlsplit(ziel).hostname})")
    if _host(ziel) != _host(url):
        return Linkergebnis(url, UMLEITUNG, code, ziel, f"leitet um auf {ziel}")
    return Linkergebnis(url, OK, code, ziel)


def pruefe_urls(urls: Iterable[str], parallel: int = 8, timeout: float = 15.0,
                oeffner: Optional[urllib.request.OpenerDirector] = None) -> list[Linkergebnis]:
    """Prüft jede URL einmal, höchstens ``parallel`` gleichzeitig. Reihenfolge wie übergeben."""
    eindeutig = list(dict.fromkeys(u for u in urls if u))
    with ThreadPoolExecutor(max_workers=max(1, parallel)) as pool:
        return list(pool.map(lambda u: pruefe_url(u, timeout, oeffner), eindeutig))


def kein_netz(ergebnisse: list[Linkergebnis], anteil: float = 0.8) -> bool:
    """Fast nichts erreichbar – vermutlich kein Netz oder ein sperrender Proxy.

    Ein sperrender Proxy beantwortet manche Hosts mit HTTP 403 statt die Verbindung
    abzulehnen; deshalb zählt ein Anteil, nicht „alle“.
    """
    if not ergebnisse:
        return False
    weg = sum(1 for e in ergebnisse if e.status == NICHT_ERREICHBAR)
    return weg / len(ergebnisse) >= anteil
