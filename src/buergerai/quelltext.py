"""Text einer Quelle holen (#63): Bundesgesetze als XML, andere Seiten als HTML-Text.

- Bundesgesetze (gesetze-im-internet.de): ``<abk>/xml.zip`` enthält das ganze
  Gesetz als XML, je Paragraf eine ``norm`` mit ``enbez`` (z. B. "§ 1") und
  den Stand ("Zuletzt geändert durch …") in den Metadaten. Robuster als HTML.
- Andere Seiten: HTML auf Text reduziert (nur Standardbibliothek, ADR 0002).
- PDFs werden nicht ausgelesen, sondern als "manuell" gemeldet.

Abrufe werden im Prozess und optional auf der Platte zwischengespeichert,
damit mehrere Quellen desselben Gesetzes (beeg_1, beeg_7, …) nur einen Abruf
kosten und wiederholte Läufe die Server schonen.
"""

from __future__ import annotations

import hashlib
import http.client
import io
import re
import socket
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlsplit

from . import __version__

USER_AGENT = f"BuergerAI-Quellenabgleich/{__version__} (+https://github.com/uhrigjanis/BuergerAi)"
GII_HOST = "gesetze-im-internet.de"
CACHE_GUELTIG_SEKUNDEN = 24 * 3600

OK = "ok"
MANUELL = "manuell"  # z. B. PDF – nicht automatisch auswertbar
NICHT_ERREICHBAR = "nicht_erreichbar"


class AbrufFehler(Exception):
    """Abruf gescheitert. ``netz``: der Host hat gar nicht geantwortet (Zeitüberschreitung,
    Verbindung, DNS) – weitere Abrufe beim selben Host sind dann zwecklos."""

    def __init__(self, meldung: str, netz: bool = False):
        super().__init__(meldung)
        self.netz = netz


@dataclass
class Quelltext:
    url: str
    status: str
    text: str = ""  # ganzer Text (bei Gesetzen: alle Paragrafen)
    abschnitt: Optional[str] = None  # Text des Paragrafen aus der URL, falls bestimmbar
    abschnitt_name: Optional[str] = None  # z. B. "§ 1 BEEG"
    stand: Optional[str] = None  # z. B. "Zuletzt geändert durch Art. 2 G v. …"
    abschnitte: dict[str, str] = field(default_factory=dict)  # enbez -> Text
    meldung: str = ""

    @property
    def pruefbereich(self) -> str:
        """Text für den Zahlenabgleich: der Paragraf, sonst alles."""
        return self.abschnitt or self.text


# ------------------------------------------------------------------ Abruf
Abrufer = Callable[[str], tuple[bytes, str]]  # url -> (Inhalt, Content-Type)


def http_abruf(url: str, timeout: float = 30.0) -> tuple[bytes, str]:
    anfrage = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:
            return antwort.read(), antwort.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        raise AbrufFehler(f"HTTP {exc.code} {exc.reason}") from exc
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as exc:
        raise AbrufFehler(str(getattr(exc, "reason", exc)), netz=True) from exc
    except (ValueError, http.client.HTTPException) as exc:  # z. B. Leerzeichen in der URL
        raise AbrufFehler(f"ungültige URL oder Antwort: {exc}") from exc


class Zwischenspeicher:
    """Speichert Abrufe im Prozess und optional als Dateien (gültig 24 Stunden)."""

    def __init__(self, abrufer: Optional[Abrufer] = None, verzeichnis: Optional[Path] = None):
        self.abrufer = abrufer or http_abruf
        self.verzeichnis = verzeichnis
        self._speicher: dict[str, tuple[bytes, str]] = {}
        self._fehler: dict[str, AbrufFehler] = {}
        self._stumme_hosts: set[str] = set()  # antworteten nicht – nicht erneut warten

    def holen(self, url: str) -> tuple[bytes, str]:
        if url in self._speicher:
            return self._speicher[url]
        if url in self._fehler:
            raise self._fehler[url]
        host = urlsplit(url).hostname or ""
        if host in self._stumme_hosts:
            raise AbrufFehler(f"{host} antwortete schon vorher nicht – übersprungen", netz=True)
        datei = self._datei(url)
        if datei and datei.exists() and time.time() - datei.stat().st_mtime < CACHE_GUELTIG_SEKUNDEN:
            typ, _, inhalt = datei.read_bytes().partition(b"\n")
            ergebnis = (inhalt, typ.decode("utf-8", "replace"))
        else:
            try:
                ergebnis = self.abrufer(url)
            except AbrufFehler as exc:
                self._fehler[url] = exc
                if exc.netz:
                    self._stumme_hosts.add(host)
                raise
            if datei:
                datei.parent.mkdir(parents=True, exist_ok=True)
                datei.write_bytes(ergebnis[1].encode("utf-8") + b"\n" + ergebnis[0])
        self._speicher[url] = ergebnis
        return ergebnis

    def _datei(self, url: str) -> Optional[Path]:
        if not self.verzeichnis:
            return None
        return self.verzeichnis / hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]


# ------------------------------------------------------------------ Gesetze im Internet
def gii_ziel(url: str) -> Optional[tuple[str, Optional[str]]]:
    """(Gesetzes-Kürzel aus der URL, Paragraf) für gesetze-im-internet.de, sonst None.

    ``https://www.gesetze-im-internet.de/beeg/__1.html`` -> ("beeg", "§ 1")
    ``…/bgb/__1626a.html`` -> ("bgb", "§ 1626a"), ``…/beeg/`` -> ("beeg", None)
    """
    teile = urlsplit(url)
    host = (teile.hostname or "").removeprefix("www.")
    if host != GII_HOST:
        return None
    pfad = [p for p in teile.path.split("/") if p]
    if not pfad:
        return None
    paragraf = None
    if len(pfad) > 1:
        treffer = re.fullmatch(r"__(\w+)\.html", pfad[1])
        if treffer:
            paragraf = f"§ {treffer.group(1)}"
        elif re.fullmatch(r"art_(\w+)\.html", pfad[1]):
            paragraf = f"Art {pfad[1][4:-5]}"
    return pfad[0], paragraf


def _xml_text(element: Optional[ET.Element]) -> str:
    if element is None:
        return ""
    return " ".join(t.strip() for t in element.itertext() if t.strip())


def gii_xml_lesen(inhalt: bytes) -> tuple[dict[str, str], Optional[str], str]:
    """Liest das Gesetzes-XML (auch als ZIP). Gibt (enbez -> Text, Stand, Kürzel) zurück."""
    if inhalt[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(inhalt)) as z:
            name = next((n for n in z.namelist() if n.lower().endswith(".xml")), None)
            if name is None:
                raise AbrufFehler("ZIP enthält keine XML-Datei")
            inhalt = z.read(name)
    wurzel = ET.fromstring(inhalt)
    abschnitte: dict[str, str] = {}
    stand: Optional[str] = None
    kuerzel = ""
    for norm in wurzel.iter("norm"):
        meta = norm.find("metadaten")
        if meta is None:
            continue
        kuerzel = kuerzel or _xml_text(meta.find("jurabk"))
        for angabe in meta.iter("standangabe"):
            if _xml_text(angabe.find("standtyp")) == "Stand" and stand is None:
                stand = _xml_text(angabe.find("standkommentar"))
        enbez = _xml_text(meta.find("enbez"))
        text = _xml_text(norm.find("textdaten/text"))
        if enbez and text:
            titel = _xml_text(meta.find("titel"))
            abschnitte[_enbez_schluessel(enbez)] = f"{enbez} {titel} {text}".strip()
    return abschnitte, stand, kuerzel


def _enbez_schluessel(enbez: str) -> str:
    """"§ 1" / "§1" / "Art 9a" / "Art. 9a" einheitlich als Schlüssel."""
    enbez = enbez.replace("Art.", "Art").replace("\xa0", " ")
    return re.sub(r"\s+", " ", re.sub(r"^(§|Art)\s*", r"\1 ", enbez.strip()))


# ------------------------------------------------------------------ HTML
class _TextParser(HTMLParser):
    BLOCK = {"p", "div", "br", "li", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "dd", "dt", "section"}
    WEG = {"script", "style", "noscript", "template", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.teile: list[str] = []
        self._weg = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:  # type: ignore[override]
        if tag in self.WEG:
            self._weg += 1
        elif tag in self.BLOCK:
            self.teile.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.WEG and self._weg:
            self._weg -= 1
        elif tag in self.BLOCK:
            self.teile.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._weg:
            self.teile.append(data)


def html_text(inhalt: bytes, content_type: str = "") -> str:
    zeichensatz = "utf-8"
    treffer = re.search(r"charset=([\w-]+)", content_type)
    if treffer:
        zeichensatz = treffer.group(1)
    try:
        dekodiert = inhalt.decode(zeichensatz, "replace")
    except LookupError:  # unbekannter Zeichensatz im Header
        dekodiert = inhalt.decode("utf-8", "replace")
    parser = _TextParser()
    parser.feed(dekodiert)
    text = "".join(parser.teile)
    return "\n".join(z for z in (re.sub(r"[ \t\xa0]+", " ", zeile).strip() for zeile in text.splitlines()) if z)


# ------------------------------------------------------------------ Einstieg
def holen(url: str, speicher: Zwischenspeicher) -> Quelltext:
    """Text der Quelle hinter ``url``. Fehler landen im Status, nicht als Ausnahme."""
    try:
        ziel = gii_ziel(url)
        if ziel:
            kuerzel, paragraf = ziel
            inhalt, _ = speicher.holen(f"https://www.gesetze-im-internet.de/{kuerzel}/xml.zip")
            abschnitte, stand, jurabk = gii_xml_lesen(inhalt)
            abschnitt = abschnitte.get(_enbez_schluessel(paragraf)) if paragraf else None
            meldung = "" if abschnitt or not paragraf else f"{paragraf} nicht im XML gefunden – ganzes Gesetz geprüft"
            return Quelltext(url, OK, "\n".join(abschnitte.values()), abschnitt,
                             f"{paragraf} {jurabk}".strip() if paragraf else jurabk, stand, abschnitte, meldung)
        inhalt, typ = speicher.holen(url)
        if "pdf" in typ.lower() or inhalt[:5] == b"%PDF-" or urlsplit(url).path.lower().endswith(".pdf"):
            return Quelltext(url, MANUELL, meldung="PDF – bitte von Hand prüfen")
        return Quelltext(url, OK, html_text(inhalt, typ))
    except (AbrufFehler, zipfile.BadZipFile, ET.ParseError) as exc:
        return Quelltext(url, NICHT_ERREICHBAR, meldung=str(exc))
