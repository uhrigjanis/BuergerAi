"""Änderungswächter für geprüfte Quellen (#64).

Eine geprüfte Quelle darf nicht unbemerkt veralten. Dafür wird bei der Abnahme
(oder nach dem Protokoll) ein **Fingerabdruck** gespeichert: der normalisierte
Text des geprüften Abschnitts, seine Prüfsumme und der Stand.

- Bezugstexte: ``docs/pruefprotokolle/texte/<id>.txt`` (lesbar, Änderungen im Git-Diff sichtbar)
- Verzeichnis: ``docs/pruefprotokolle/fingerabdruecke.json`` (Prüfsumme, Stand, URL, Datum)

``vergleichen`` holt den aktuellen Text und meldet Abweichungen mit Diff. Bei
Bundesgesetzen wird zuerst der Stand („Zuletzt geändert durch …“) verglichen;
ändert sich nur ein anderer Paragraf des Gesetzes, ist das keine Änderung der Quelle.
Unwesentliches (Navigation, „Seite aktualisiert am …“) blendet ``AUSSCHLUSS`` aus.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urlsplit

from . import quellenpruefung as qp
from .quelltext import MANUELL, NICHT_ERREICHBAR, OK, Quelltext
from .wissensbasis import Wissensbasis

DATEINAME = "fingerabdruecke.json"
TEXTE = "texte"
DIFF_ZEILEN_MAX = 200

# ------------------------------------------------------------------ Ausschlussliste
# Zeilen, die ganz auf eines dieser Muster passen, zählen nicht (Groß-/Kleinschreibung egal).
AUSSCHLUSS_UEBERALL = (
    r"(seite |inhalt )?(zuletzt )?(aktualisiert|geändert|bearbeitet)( am)?:?\s*\d.*",
    r"stand:?\s*\d{1,2}\.\s*\d{1,2}\.\s*\d{2,4}",
    r"\d{1,2}\.\s*\d{1,2}\.\s*\d{4}",
    r"(zum seitenanfang|nach oben|drucken|seite drucken|teilen|link kopieren|schließen)",
    r".*cookie.*",
    r"©.*",
)


@dataclass(frozen=True)
class Hostregel:
    """Bereich und Ausschlüsse für einen Host. ``beginn``/``ende``: der Inhalt liegt nach der
    letzten Zeile, die auf ``beginn`` passt (Navigation steht oft doppelt), und vor der ersten
    danach, die auf ``ende`` passt.
    ``stand``: Zeile mit dem Stand der Seite (wie „Zuletzt geändert durch“ bei Gesetzen)."""
    beginn: Optional[str] = None
    ende: Optional[str] = None
    ignorieren: tuple[str, ...] = ()
    stand: Optional[str] = None


AUSSCHLUSS: dict[str, Hostregel] = {
    # Bayern.Recht: Navigation und Inhaltsverzeichnis oben, Fußleiste unten
    "gesetze-bayern.de": Hostregel(beginn=r"Nächstes Dokument.*", ende=r"Bayern\.de",
                                   stand=r"Text gilt ab:.*"),
    # abgeordnetenwatch: Menü oben; unten Newsletter, Namensliste (seitenweise) und Fußzeile
    "abgeordnetenwatch.de": Hostregel(beginn=r"Ausschüsse",
                                      ende=r"Abstimmungsverhalten von insgesamt.*|Einfluss, Profite.*",
                                      ignorieren=(r"Weiterlesen",)),
}


def _host(url: str) -> str:
    return (urlsplit(url).hostname or "").removeprefix("www.")


def _passt(muster: Iterable[str], zeile: str) -> bool:
    return any(re.fullmatch(m, zeile, re.IGNORECASE) for m in muster)


def _zeile_normalisieren(zeile: str) -> str:
    zeile = unicodedata.normalize("NFKC", zeile).replace("­", "")
    return re.sub(r"\s+", " ", zeile).strip()


def _saetze(zeile: str) -> list[str]:
    """Lange Zeilen (Gesetze: ein Paragraf je Zeile) in Absätze und Sätze teilen, damit der Diff lesbar bleibt.
    Nach einer Ordnungszahl („1. Januar“) wird nicht geteilt."""
    teile = re.split(r"\s+(?=\(\d+[a-z]?\)\s)", zeile)
    ergebnis: list[str] = []
    for t in teile:
        ergebnis.extend(s for s in re.split(r"(?<=[.;:])(?<!\d\.)\s+(?=\(?\d+[a-z]?[.)]\s|[A-ZÄÖÜ])", t) if s)
    return ergebnis


def bezugstext(qt: Quelltext) -> tuple[list[str], Optional[str]]:
    """(Zeilen des verglichenen Texts, Stand). Bei Gesetzen der Paragraf aus der URL."""
    regel = AUSSCHLUSS.get(_host(qt.url), Hostregel())
    stand = qt.stand
    roh = [_zeile_normalisieren(z) for z in qt.pruefbereich.splitlines()]
    roh = [z for z in roh if z]
    if regel.stand and stand is None:
        stand = next((z for z in roh if re.fullmatch(regel.stand, z, re.IGNORECASE)), None)
    if regel.beginn:
        treffer = [i for i, z in enumerate(roh) if re.fullmatch(regel.beginn, z, re.IGNORECASE)]
        if treffer:
            start = treffer[-1]
            roh = roh[start + 1:]
    if regel.ende:
        ende = next((i for i, z in enumerate(roh) if re.fullmatch(regel.ende, z, re.IGNORECASE)), None)
        if ende is not None:
            roh = roh[:ende]
    zeilen: list[str] = []
    for z in roh:
        if _passt(AUSSCHLUSS_UEBERALL, z) or _passt(regel.ignorieren, z):
            continue
        zeilen.extend(_saetze(z))
    return zeilen, stand


def pruefsumme(zeilen: list[str]) -> str:
    return "sha256:" + hashlib.sha256("\n".join(zeilen).encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ Fingerabdrücke
@dataclass(frozen=True)
class Fingerabdruck:
    quelle_id: str
    url: str
    pruefsumme: str
    erfasst_am: date
    anlass: str  # abnahme | erfasst
    stand: Optional[str] = None
    abschnitt: Optional[str] = None


def _verzeichnis(verzeichnis: Optional[Path]) -> Path:
    return Path(verzeichnis or qp.PROTOKOLL_VERZEICHNIS)


def textpfad(quelle_id: str, verzeichnis: Optional[Path] = None) -> Path:
    return _verzeichnis(verzeichnis) / TEXTE / f"{quelle_id}.txt"


def _lesen_roh(verzeichnis: Optional[Path]) -> dict:
    pfad = _verzeichnis(verzeichnis) / DATEINAME
    if not pfad.is_file():
        return {}
    return json.loads(pfad.read_text(encoding="utf-8")).get("quellen", {})


def lesen(verzeichnis: Optional[Path] = None) -> dict[str, Fingerabdruck]:
    return {
        qid: Fingerabdruck(qid, e["url"], e["pruefsumme"], date.fromisoformat(e["erfasst_am"]), e["anlass"],
                           e.get("stand"), e.get("abschnitt"))
        for qid, e in _lesen_roh(verzeichnis).items()
    }


def speichern(qt: Quelltext, quelle_id: str, am: date, anlass: str,
              verzeichnis: Optional[Path] = None) -> Fingerabdruck:
    """Speichert Bezugstext und Fingerabdruck der Quelle (ersetzt einen vorhandenen)."""
    if qt.status != OK:
        raise ValueError(f"{quelle_id}: Text nicht verfügbar ({qt.status}: {qt.meldung})")
    zeilen, stand = bezugstext(qt)
    if not zeilen:
        raise ValueError(f"{quelle_id}: kein Text nach dem Ausblenden – Ausschlussliste prüfen")
    fa = Fingerabdruck(quelle_id, qt.url, pruefsumme(zeilen), am, anlass, stand, qt.abschnitt_name)
    ziel = textpfad(quelle_id, verzeichnis)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    alle = _lesen_roh(verzeichnis)
    eintrag = {"url": fa.url, "abschnitt": fa.abschnitt, "stand": fa.stand, "pruefsumme": fa.pruefsumme,
               "erfasst_am": am.isoformat(), "anlass": anlass}
    alle[quelle_id] = {k: v for k, v in eintrag.items() if v is not None}
    inhalt = {
        "_hinweis": "Fingerabdrücke geprüfter Quellen für den Änderungswächter (#64). Bezugstexte in texte/. "
                    "Erzeugt von ./bai quellen --abnehmen bzw. --fingerabdruck, nicht von Hand ändern.",
        "quellen": dict(sorted(alle.items())),
    }
    (ziel.parent.parent / DATEINAME).write_text(json.dumps(inhalt, ensure_ascii=False, indent=2) + "\n",
                                                 encoding="utf-8")
    return fa


# ------------------------------------------------------------------ Vergleich
UNVERAENDERT = "unverändert"
GEAENDERT = "geändert"
KEIN_FINGERABDRUCK = "kein Fingerabdruck"
URL_GEAENDERT = "URL geändert"


@dataclass
class Vergleich:
    quelle_id: str
    status: str  # UNVERAENDERT, GEAENDERT, KEIN_FINGERABDRUCK, URL_GEAENDERT, MANUELL, NICHT_ERREICHBAR
    fingerabdruck: Optional[Fingerabdruck] = None
    stand_neu: Optional[str] = None
    diff: list[str] = field(default_factory=list)
    meldung: str = ""

    @property
    def geaendert(self) -> bool:
        return self.status == GEAENDERT

    def zusammenfassung(self) -> str:
        fa = self.fingerabdruck
        seit = f" seit {fa.erfasst_am.strftime('%d.%m.%Y')}" if fa else ""
        if self.status == UNVERAENDERT:
            text = f"Text{seit} unverändert"
            if fa and fa.stand and self.stand_neu and fa.stand != self.stand_neu:
                text += f" (Gesetz geändert, Abschnitt nicht: {self.stand_neu})"
            return text
        if self.status == GEAENDERT:
            plus = sum(1 for z in self.diff if z.startswith("+") and not z.startswith("+++"))
            minus = sum(1 for z in self.diff if z.startswith("-") and not z.startswith("---"))
            return f"Text{seit} GEÄNDERT (+{plus}/−{minus} Zeilen)" + \
                (f", Stand jetzt: {self.stand_neu}" if self.stand_neu and fa and self.stand_neu != fa.stand else "")
        if self.status in (MANUELL, NICHT_ERREICHBAR):
            return f"{self.status}: {self.meldung}"
        return f"{self.status}" + (f": {self.meldung}" if self.meldung else "")


def vergleichen(quelle_id: str, qt: Quelltext, fa: Optional[Fingerabdruck], heute: date,
                verzeichnis: Optional[Path] = None) -> Vergleich:
    if fa is None:
        return Vergleich(quelle_id, KEIN_FINGERABDRUCK, meldung="anlegen: buergerai quellen --fingerabdruck "
                                                                 + quelle_id)
    if fa.url != qt.url:
        return Vergleich(quelle_id, URL_GEAENDERT, fa,
                         meldung=f"Fingerabdruck für {fa.url} – nach Prüfung neu erfassen")
    if qt.status != OK:
        return Vergleich(quelle_id, qt.status, fa, meldung=qt.meldung)
    if qt.stand and fa.stand and qt.stand == fa.stand:
        return Vergleich(quelle_id, UNVERAENDERT, fa, qt.stand)  # Gesetz unverändert: Text nicht nötig
    zeilen, stand = bezugstext(qt)
    if pruefsumme(zeilen) == fa.pruefsumme:
        return Vergleich(quelle_id, UNVERAENDERT, fa, stand)
    pfad = textpfad(quelle_id, verzeichnis)
    alt = pfad.read_text(encoding="utf-8").splitlines() if pfad.is_file() else []
    diff = list(difflib.unified_diff(alt, zeilen, f"geprüft ({fa.erfasst_am.isoformat()})",
                                     f"aktuell ({heute.isoformat()})", lineterm="", n=1))
    if not alt:
        meldung = f"Bezugstext {pfad.name} fehlt – kein Diff möglich"
    elif len(diff) > DIFF_ZEILEN_MAX:
        meldung = f"Diff gekürzt auf {DIFF_ZEILEN_MAX} von {len(diff)} Zeilen"
        diff = diff[:DIFF_ZEILEN_MAX]
    else:
        meldung = ""
    return Vergleich(quelle_id, GEAENDERT, fa, stand, diff, meldung)


# ------------------------------------------------------------------ Hinweis in den Daten
FELD = "seit_pruefung_geaendert"


def vermerken(kb: Wissensbasis, quelle_id: str, am: Optional[date]) -> Path:
    """Setzt (``am``) oder entfernt (``None``) den Hinweis „Quelle seit Prüfung geändert“ am Quellen-Eintrag.
    Der Prüfstatus bleibt (ADR 0004, Nachtrag #64). Ändert nur dieses Feld."""
    datei = qp._quelldatei(kb, quelle_id)

    def aendern(eintrag: dict) -> dict:
        if am is None:
            eintrag.pop(FELD, None)
            return eintrag
        return qp._felder_setzen(eintrag, {FELD: am.isoformat()})

    text = datei.read_text(encoding="utf-8")
    neu = qp._eintrag_ersetzen(text, quelle_id, aendern)
    if neu != text:
        datei.write_text(neu, encoding="utf-8")
    return datei


# ------------------------------------------------------------------ Issue-Text
def issue_text(kb: Wissensbasis, v: Vergleich, heute: date, daten: Optional[Path] = None) -> str:
    q = kb.quellen[v.quelle_id]
    fa = v.fingerabdruck
    assert fa is not None
    pruefung = f"{q.pruefstatus.value}"
    if q.geprueft_am:
        pruefung += f" (geprüft am {q.geprueft_am.strftime('%d.%m.%Y')} von {q.geprueft_von})"
    zeilen = [
        f"Der Änderungswächter (#64) hat am {heute.strftime('%d.%m.%Y')} eine Änderung an **`{q.id}`** festgestellt.",
        "",
        f"- Quelle: {q.titel}, {q.url}",
    ]
    if fa.abschnitt:
        zeilen.append(f"- Abschnitt: {fa.abschnitt}")
    zeilen += [
        f"- Prüfstatus: {pruefung}",
        f"- Bezugstext vom {fa.erfasst_am.strftime('%d.%m.%Y')} ({fa.anlass})"
        + (f", Stand damals: {fa.stand}" if fa.stand else ""),
    ]
    if v.stand_neu and v.stand_neu != fa.stand:
        zeilen.append(f"- Stand jetzt: {v.stand_neu}")
    if qp.protokoll_pfad(q.id).is_file():
        zeilen.append(f"- Prüfprotokoll: `docs/pruefprotokolle/{q.id}.md`")
    zeilen += ["", "### Änderung", ""]
    if v.meldung:
        zeilen += [f"_{v.meldung}_", ""]
    zeilen += ["```diff", *v.diff, "```", ""]
    liste = qp.verwendungen(kb, q.id, daten)
    zeilen += [f"### Betroffene Verwendungen ({len(liste)})", ""]
    for e in qp.zusammenfassen(liste, qp.phase1_gebiete(kb)):
        if isinstance(e, str):
            zeilen.append(f"- … {e}")
        else:
            zeilen.append(f"- {qp.beschreibung(e)} – `{e.datei}` `{e.pfad}`")
    if not liste:
        zeilen.append("- keine")
    zeilen += [
        "",
        "### Nächste Schritte",
        "",
        "1. Diff lesen und mit dem Prüfprotokoll vergleichen.",
        f"2. **Unwesentlich** (z. B. Redaktion, Verweise): `./bai quellen --fingerabdruck {q.id}` speichert "
        "den neuen Bezugstext. Committen, Issue schließen.",
        "3. **Wesentlich**: Daten und Regeln anpassen, Protokoll aktualisieren. Bei einer verifizierten Quelle "
        f"`./bai quellen --zuruecksetzen {q.id}`, nach erneuter Prüfung `./bai quellen --abnehmen {q.id} --von \"…\"`.",
        "",
        f"Bis zur Klärung zeigt `./bai quellen --aenderungen {q.id} --vermerken` (danach committen) in den "
        "Ergebnissen den Hinweis „Quelle seit Prüfung geändert“.",
        "",
    ]
    text = "\n".join(zeilen)
    if len(text) > 60000:  # GitHub erlaubt 65 536 Zeichen im Issue-Text
        text = text[:60000] + "\n```\n\n_(gekürzt)_\n"
    return text


def bericht_markdown(ergebnisse: list[Vergleich]) -> str:
    zeilen = ["## Änderungswächter", "", "| Quelle | Ergebnis |", "|---|---|"]
    for v in ergebnisse:
        symbol = {"geändert": "🔴", "unverändert": "✅"}.get(v.status, "⚠️")
        zeilen.append(f"| `{v.quelle_id}` | {symbol} {v.zusammenfassung().replace('|', '/')} |")
    return "\n".join(zeilen) + "\n\n"
