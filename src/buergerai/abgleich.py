"""Zitat- und Zahlen-Abgleich gegen den Text der Quelle (#63).

1. Zitate: Jedes Zitat („…“) aus der Spalte „Wortlaut der Quelle“ des
   Prüfprotokolls muss wörtlich im Text der Quelle stehen. „…“ im Zitat gilt
   als Lücke: die Teilstücke werden einzeln gesucht.
2. Zahlen: Schwellenwerte, Stichtage, Fristen und Beträge der Regeln, die die
   Quelle zitieren, sollten im zitierten Paragrafen vorkommen. Nicht gefunden
   ist nur ein Hinweis, kein Urteil – die Auslegung bleibt beim Menschen.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterator, Optional

from .quellenpruefung import _fundstellen, protokoll_pfad
from .quelltext import OK, Quelltext
from .wissensbasis import Wissensbasis

MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
          "November", "Dezember"]
ZAHLWOERTER = {1: ["ein", "eine", "einer", "einem", "einen", "eins"], 2: ["zwei"], 3: ["drei"], 4: ["vier"],
               5: ["fünf"], 6: ["sechs"], 7: ["sieben"], 8: ["acht"], 9: ["neun"], 10: ["zehn"], 11: ["elf"],
               12: ["zwölf"], 13: ["dreizehn"], 14: ["vierzehn"]}
EINHEITEN = {"tage": r"(?:kalender|werk|arbeits)?tag", "wochen": r"(?:kalender)?woche",
             "monate": r"(?:lebens|kalender)?monat"}
MIN_ZITATLAENGE = 12  # kürzere Teilstücke (z. B. „…“ allein) werden nicht gesucht


# ------------------------------------------------------------------ Normalisieren
def normalisieren(text: str) -> str:
    """Vergleichbare Form: Unicode NFKC, einheitliche Anführungszeichen und Striche,
    ohne weiche Trennstriche, Leerraum zusammengefasst, Kleinschreibung."""
    text = unicodedata.normalize("NFKC", text)
    for alt, neu in (("­", ""), ("„", '"'), ("“", '"'), ("”", '"'), ("‚", "'"), ("‘", "'"), ("’", "'"),
                     ("–", "-"), ("—", "-"), ("‑", "-")):
        text = text.replace(alt, neu)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r" ([,.;:!?)])", r"\1", text)
    text = re.sub(r"([(]) ", r"\1", text)
    return text.strip().lower()


# ------------------------------------------------------------------ Zitate
@dataclass(frozen=True)
class Zitat:
    zeile: int  # laufende Nummer in der Protokolltabelle
    text: str

    def teilstuecke(self) -> list[str]:
        teile = re.split(r"\s*(?:…|\.\.\.)\s*", self.text)
        return [t.strip(" ,;") for t in teile if len(t.strip(" ,;")) >= MIN_ZITATLAENGE]


def zitate_aus_protokoll(text: str) -> list[Zitat]:
    """Zitate in „…“ aus der Spalte „Wortlaut der Quelle“ der Verwendungstabelle."""
    ergebnis: list[Zitat] = []
    in_tabelle = False
    for zeile in text.splitlines():
        if zeile.startswith("## "):
            in_tabelle = zeile.startswith("## Verwendungen")
            continue
        if not in_tabelle or not zeile.startswith("|") or zeile.startswith(("|---", "| #")):
            continue
        zellen = [z.strip() for z in zeile.strip().strip("|").split(" | ")]
        if len(zellen) < 5 or not zellen[0].isdigit():
            continue
        for treffer in re.finditer(r"„(.+?)“", zellen[3]):
            ergebnis.append(Zitat(int(zellen[0]), treffer.group(1)))
    return ergebnis


def zitat_gefunden(zitat: Zitat, quelltext: str) -> bool:
    teile = zitat.teilstuecke()
    if not teile:
        return True  # nichts Prüfbares (z. B. nur „…“)
    norm = normalisieren(quelltext)
    return all(normalisieren(t) in norm for t in teile)


# ------------------------------------------------------------------ Zahlen
@dataclass(frozen=True)
class Zahl:
    wert: Any  # int, float, date oder ("tage", 7)
    herkunft: str  # z. B. "elterngeld_bund: Arbeitet höchstens 32 Stunden …"

    def anzeige(self) -> str:
        if isinstance(self.wert, tuple):
            return f"{self.wert[1]} {self.wert[0].capitalize()}"
        if isinstance(self.wert, date):
            return self.wert.strftime("%d.%m.%Y")
        return _tausender(self.wert)


def _tausender(zahl: float) -> str:
    if float(zahl).is_integer():
        return f"{int(zahl):,}".replace(",", ".")
    return f"{zahl:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _datum(wert: Any) -> Optional[date]:
    if isinstance(wert, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", wert):
        try:
            return date.fromisoformat(wert)
        except ValueError:
            return None
    return None


def zahlen_der_quelle(kb: Wissensbasis, quelle_id: str) -> list[Zahl]:
    """Werte aus Regeln, Fristen und Beträgen, die die Quelle zitieren (ohne Doppelte)."""
    gesehen: set[Any] = set()
    ergebnis: list[Zahl] = []

    def merken(wert: Any, herkunft: str) -> None:
        if wert not in gesehen:
            gesehen.add(wert)
            ergebnis.append(Zahl(wert, herkunft))

    for datei in kb.dateien:
        inhalt = json.loads(datei.read_text(encoding="utf-8"))
        for sammlung, eintraege in inhalt.items():
            if sammlung == "quellen" or not isinstance(eintraege, list):
                continue
            for eintrag in eintraege:
                if not isinstance(eintrag, dict):
                    continue
                for _teile, knoten in _fundstellen(eintrag, []):
                    if quelle_id not in (knoten.get("quellen") or ()):
                        continue
                    for wert, herkunft in _werte(knoten, str(eintrag.get("id", ""))):
                        merken(wert, herkunft)
    return ergebnis


def _werte(knoten: dict[str, Any], objekt: str) -> Iterator[tuple[Any, str]]:
    text = knoten.get("text", "")
    herkunft = f"{objekt}: {text}" if text else objekt
    if "fakt" in knoten:
        wert = knoten.get("wert")
        if isinstance(wert, (int, float)) and not isinstance(wert, bool) and wert not in (0, 1):
            yield wert, herkunft
        elif _datum(wert):
            yield _datum(wert), herkunft
    for einheit in ("tage", "wochen", "monate"):
        if knoten.get(einheit):  # negativ = vor dem Ereignis („frühestens 7 Wochen vor“)
            yield (einheit, abs(int(knoten[einheit]))), herkunft
    if "fakt" not in knoten and "tage" not in knoten and text and "€" in text:
        for betrag in re.findall(r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{2}))?\s*€", text):
            zahl = int(betrag[0].replace(".", ""))
            yield (zahl + int(betrag[1]) / 100 if betrag[1] else zahl), herkunft


def _zahl_muster(zahl: float) -> str:
    if float(zahl).is_integer():
        ziffern = str(int(zahl))
        gruppen = []
        while len(ziffern) > 3:
            gruppen.insert(0, ziffern[-3:])
            ziffern = ziffern[:-3]
        gruppen.insert(0, ziffern)
        kern = r"[ .  ]?".join(gruppen)
    else:
        ganz, nachkomma = f"{zahl:.2f}".split(".")
        kern = re.escape(ganz) + r"[,.]" + nachkomma
    # nicht Teil einer größeren Zahl, auch nicht mit Tausender-Leerzeichen („1 175 000“)
    return rf"(?<![\d.,])(?<!\d[ \u00a0\u202f]){kern}(?![\d]|,\d|[ .\u00a0\u202f]\d{{3}}(?!\d))"


def zahl_gefunden(zahl: Zahl, quelltext: str) -> bool:
    text = unicodedata.normalize("NFKC", quelltext)
    wert = zahl.wert
    if isinstance(wert, tuple):
        einheit, n = wert
        woerter = [str(n)] + ZAHLWOERTER.get(n, [])
        muster = rf"(?<!\w)(?:{'|'.join(woerter)})\s+{EINHEITEN[einheit]}"
        if re.search(muster, text, re.IGNORECASE):
            return True
        if einheit == "tage" and n % 7 == 0:  # 7 Tage = eine Woche
            return zahl_gefunden(Zahl(("wochen", n // 7), zahl.herkunft), quelltext)
        return False
    if isinstance(wert, date):
        monat = MONATE[wert.month - 1]
        varianten = [rf"{wert.day}\.\s*{monat}\s+{wert.year}", rf"0?{wert.day}\.\s*0?{wert.month}\.\s*{wert.year}"]
        return any(re.search(v, text) for v in varianten)
    return re.search(_zahl_muster(float(wert)), text) is not None


# ------------------------------------------------------------------ Ergebnis
@dataclass
class Abgleich:
    quelle_id: str
    quelltext: Quelltext
    protokoll: bool  # gibt es ein Protokoll?
    zitate: list[tuple[Zitat, bool]] = field(default_factory=list)
    zahlen: list[tuple[Zahl, bool]] = field(default_factory=list)

    @property
    def fehlende_zitate(self) -> list[Zitat]:
        return [z for z, ok in self.zitate if not ok]

    @property
    def fehlende_zahlen(self) -> list[Zahl]:
        return [z for z, ok in self.zahlen if not ok]

    def zusammenfassung(self) -> str:
        if self.quelltext.status != OK:
            return f"{self.quelltext.status}: {self.quelltext.meldung}"
        teile = []
        if self.protokoll:
            teile.append(f"Zitate {len(self.zitate) - len(self.fehlende_zitate)}/{len(self.zitate)}")
        else:
            teile.append("kein Protokoll")
        teile.append(f"Zahlen {len(self.zahlen) - len(self.fehlende_zahlen)}/{len(self.zahlen)}")
        if self.quelltext.stand:
            teile.append(f"Stand: {self.quelltext.stand}")
        return " · ".join(teile)


def abgleichen(kb: Wissensbasis, quelle_id: str, quelltext: Quelltext,
               protokolle: Optional[Path] = None) -> Abgleich:
    pfad = protokoll_pfad(quelle_id, protokolle)
    ergebnis = Abgleich(quelle_id, quelltext, pfad.is_file())
    if quelltext.status != OK:
        return ergebnis
    if ergebnis.protokoll:
        for z in zitate_aus_protokoll(pfad.read_text(encoding="utf-8")):
            ergebnis.zitate.append((z, zitat_gefunden(z, quelltext.text)))
    for zahl in zahlen_der_quelle(kb, quelle_id):
        ergebnis.zahlen.append((zahl, zahl_gefunden(zahl, quelltext.pruefbereich)))
    return ergebnis


# ------------------------------------------------------------------ Ausgabe ins Protokoll
ABSCHNITT = "## Automatischer Abgleich"


def protokoll_abschnitt(a: Abgleich, heute: date) -> str:
    q = a.quelltext
    zeilen = [ABSCHNITT, "", f"Stand {heute.strftime('%d.%m.%Y')} (`./bai quellen --abgleich {a.quelle_id}`): "
              f"{a.zusammenfassung()}", ""]
    if q.abschnitt_name:
        zeilen += [f"Geprüfter Abschnitt: {q.abschnitt_name}" + (f" ({q.meldung})" if q.meldung else ""), ""]
    for z in a.fehlende_zitate:
        zeilen.append(f"- ❌ Zitat aus Zeile {z.zeile} nicht im Text gefunden: „{z.text}“")
    for z in a.fehlende_zahlen:
        zeilen.append(f"- ⚠️ Zahl {z.anzeige()} nicht im Abschnitt gefunden ({z.herkunft})")
    if not a.fehlende_zitate and not a.fehlende_zahlen and q.status == OK:
        zeilen.append("- ✅ alle Zitate und Zahlen gefunden")
    return "\n".join(zeilen) + "\n"


def in_protokoll_schreiben(a: Abgleich, heute: date, protokolle: Optional[Path] = None) -> bool:
    """Ersetzt bzw. ergänzt den Abschnitt „Automatischer Abgleich“. False ohne Protokoll."""
    pfad = protokoll_pfad(a.quelle_id, protokolle)
    if not pfad.is_file():
        return False
    text = pfad.read_text(encoding="utf-8")
    neu = protokoll_abschnitt(a, heute)
    if ABSCHNITT in text:
        start = text.index(ABSCHNITT)
        ende = text.find("\n## ", start + len(ABSCHNITT))
        text = text[:start] + neu + (text[ende + 1:] if ende != -1 else "")
    else:
        text = text.rstrip("\n") + "\n\n" + neu
    pfad.write_text(text, encoding="utf-8")
    return True
