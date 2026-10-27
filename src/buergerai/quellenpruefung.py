"""Werkzeuge für die Prüfung der Quellen gegen den Volltext (Issue #45, #53).

- ``verwendungen``: Wo zitiert die Wissensbasis eine Quelle? Liest die
  JSON-Dateien direkt, damit Datei und JSON-Pfad für Korrekturen bekannt sind.
- ``protokoll_geruest``: Prüfprotokoll nach der Vorlage, vorbefüllt mit allen
  Verwendungen.
- ``phase1_quellen``: Quellen der Pilotregion (Geburt, München und Freising).
- ``ohne_protokoll``: Geprüfte Quellen, deren Notiz kein Protokoll verlinkt.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

from .gebiete import hierarchie
from .modell import Pruefstatus, Quelle
from .wissensbasis import STANDARD_DATENVERZEICHNIS, Wissensbasis

PROTOKOLL_VERZEICHNIS = STANDARD_DATENVERZEICHNIS.parent / "docs" / "pruefprotokolle"

# Pilotregion der Phase 1 (ADR 0001): Lebenslage Geburt in München und Freising.
PHASE1_LEBENSLAGE = "geburt"
PHASE1_GEMEINDEN = ("09162000", "09178124")

# Art der Verwendung je Sammlung auf oberster Ebene einer Datei
_ART_DER_SAMMLUNG = {
    "varianten": "Variante",
    "leistungen": "Leistung",
    "zustaendigkeiten": "Zuständigkeit",
    "gebiete": "Gebiet",
    "abdeckung": "Landesabdeckung",
    "fakten": "Fakt",
    "lebenslagen": "Lebenslage",
}


@dataclass(frozen=True)
class Verwendung:
    datei: str  # relativ zum Datenverzeichnis
    pfad: str  # JSON-Pfad, z. B. varianten[3].regel.alle[0]
    art: str  # Variante, Bedingung, Frist, Betrag, Zuständigkeit, Gebiet, ...
    objekt: str  # ID des umgebenden Eintrags (Variante, Leistung, ...)
    text: str  # Was die Wissensbasis an dieser Stelle behauptet
    erben: tuple[str, ...] = ()  # Varianten, die diese Variante per erbt_von übernehmen


def _pfad(teile: list[str]) -> str:
    return "".join(t if t.startswith("[") else f".{t}" for t in teile).lstrip(".")


def _knotentext(knoten: dict[str, Any]) -> str:
    if "pruefung_noetig" in knoten:
        return f"Prüfung nötig: {knoten['pruefung_noetig']}"
    if "fakt" in knoten:
        wert = json.dumps(knoten.get("wert"), ensure_ascii=False)
        bedingung = f"{knoten['fakt']} {knoten.get('op', '')} {wert}"
        return f"{knoten['text']} ({bedingung})" if knoten.get("text") else bedingung
    for typ in ("alle", "eine", "nicht", "lebenslage"):
        if typ in knoten:
            return knoten.get("text") or f"Gruppe „{typ}“"
    return knoten.get("text", "")


def _einordnen(knoten: dict[str, Any], teile: list[str], eintrag: dict[str, Any], sammlung: str) -> tuple[str, str]:
    """Art und Text einer Fundstelle aus ihrem Pfad bestimmen."""
    if "regel" in teile or "vorbedingung" in teile:
        return "Bedingung", _knotentext(knoten)
    if "fristen" in teile:
        return "Frist", knoten.get("text", "")
    if "betraege" in teile:
        return "Betrag", knoten.get("text", "")
    art = _ART_DER_SAMMLUNG.get(sammlung, sammlung)
    if sammlung == "varianten":
        text = f"Leistung {eintrag.get('leistung_id')} in Gebiet {eintrag.get('gebiet_id')}"
    elif sammlung == "abdeckung":
        text = (f"{eintrag.get('gebiet_id')}/{eintrag.get('lebenslage')}: "
                f"Landesleistungen {eintrag.get('landesleistungen')}")
    else:
        text = eintrag.get("name") or eintrag.get("titel") or eintrag.get("text") or ""
    return art, text


def _fundstellen(wert: Any, teile: list[str]) -> Iterator[tuple[list[str], dict[str, Any]]]:
    if isinstance(wert, dict):
        yield teile, wert
        for k, v in wert.items():
            yield from _fundstellen(v, teile + [k])
    elif isinstance(wert, list):
        for i, v in enumerate(wert):
            yield from _fundstellen(v, teile + [f"[{i}]"])


def _erben(roh_varianten: dict[str, dict[str, Any]]) -> dict[str, tuple[str, ...]]:
    """Variante -> alle Varianten, die sie direkt oder über eine Kette erben."""
    kinder: dict[str, list[str]] = {}
    for vid, v in roh_varianten.items():
        if v.get("erbt_von"):
            kinder.setdefault(v["erbt_von"], []).append(vid)

    def alle(vid: str, gesehen: frozenset[str] = frozenset()) -> list[str]:
        ergebnis: list[str] = []
        for k in sorted(kinder.get(vid, ())):
            if k not in gesehen:
                ergebnis += [k] + alle(k, gesehen | {k})
        return ergebnis

    return {vid: tuple(alle(vid)) for vid in kinder}


def verwendungen(kb: Wissensbasis, quelle_id: str, verzeichnis: Optional[Path] = None) -> list[Verwendung]:
    """Alle Stellen der Wissensbasis, die ``quelle_id`` in einer ``quellen``-Liste nennen."""
    verzeichnis = Path(verzeichnis or STANDARD_DATENVERZEICHNIS)
    inhalte = [(d, json.loads(d.read_text(encoding="utf-8"))) for d in kb.dateien]
    roh_varianten = {v["id"]: v for _, inhalt in inhalte for v in inhalt.get("varianten", ()) if "id" in v}
    erben = _erben(roh_varianten)

    ergebnis: list[Verwendung] = []
    erben_genannt: set[str] = set()  # Vererbung nur beim ersten Treffer je Variante nennen
    for datei, inhalt in inhalte:
        try:
            name = datei.relative_to(verzeichnis).as_posix()
        except ValueError:
            name = datei.as_posix()
        for sammlung, eintraege in inhalt.items():
            if sammlung == "quellen" or not isinstance(eintraege, list):
                continue
            for i, eintrag in enumerate(eintraege):
                if not isinstance(eintrag, dict):
                    continue
                for teile, knoten in _fundstellen(eintrag, [sammlung, f"[{i}]"]):
                    quellen = knoten.get("quellen")
                    if not isinstance(quellen, list) or quelle_id not in quellen:
                        continue
                    art, text = _einordnen(knoten, teile[2:], eintrag, sammlung)
                    objekt = str(eintrag.get("id") or eintrag.get("gebiet_id") or "")
                    vererbt: tuple[str, ...] = ()
                    if sammlung == "varianten" and objekt not in erben_genannt:
                        erben_genannt.add(objekt)
                        vererbt = erben.get(objekt, ())
                    ergebnis.append(Verwendung(
                        datei=name,
                        pfad=_pfad(teile),
                        art=art,
                        objekt=objekt,
                        text=text,
                        erben=vererbt,
                    ))
    return ergebnis


def zusammenfassen(liste: list[Verwendung], bevorzugt: Iterable[str] = (), grenze: int = 20,
                   zeigen: int = 3) -> list[Verwendung | str]:
    """Große Gruppen (gleiche Datei und Art, z. B. 10.000 Gebiete) auf einige Beispiele kürzen.

    Einträge, deren Objekt in ``bevorzugt`` steht (z. B. die Gebiete der Pilotregion),
    werden immer gezeigt.
    """
    bevorzugt = set(bevorzugt)
    gruppen: dict[tuple[str, str], list[Verwendung]] = {}
    for v in liste:
        gruppen.setdefault((v.datei, v.art), []).append(v)
    gezeigt: set[int] = set()
    for gruppe in gruppen.values():
        if len(gruppe) <= grenze:
            gezeigt.update(id(v) for v in gruppe)
            continue
        wichtig = [v for v in gruppe if v.objekt in bevorzugt]
        rest = [v for v in gruppe if v.objekt not in bevorzugt]
        gezeigt.update(id(v) for v in wichtig + rest[:max(0, zeigen - len(wichtig))])
    ergebnis: list[Verwendung | str] = []
    for v in liste:
        if id(v) in gezeigt:
            ergebnis.append(v)
        gruppe = gruppen[(v.datei, v.art)]
        if v is gruppe[-1] and len(gruppe) > grenze:
            weitere = sum(1 for w in gruppe if id(w) not in gezeigt)
            ergebnis.append(f"… und {weitere} weitere Einträge der Art {v.art} in {v.datei}")
    return ergebnis


def phase1_gebiete(kb: Wissensbasis) -> set[str]:
    """Gemeinden der Pilotregion und alle übergeordneten Gebiete."""
    return {g.id for gid in PHASE1_GEMEINDEN if gid in kb.gebiete for g in hierarchie(kb, gid)}


def phase1_quellen(kb: Wissensbasis) -> list[str]:
    """Quellen, auf denen das Ergebnis für Geburt in München und Freising beruht."""
    gebiete = phase1_gebiete(kb)
    ids: set[str] = set()
    for gid in gebiete:
        ids.update(kb.gebiete[gid].quellen)
        nachweis = kb.landesabdeckung.get((gid, PHASE1_LEBENSLAGE))
        if nachweis:
            ids.update(nachweis.quellen)
    for leistung in kb.leistungen_fuer([PHASE1_LEBENSLAGE]):
        varianten = [v for v in kb.varianten_von(leistung.id) if v.gebiet_id in gebiete]
        if varianten:  # Beträge nur bei Leistungen, die es in der Pilotregion gibt
            for b in leistung.betraege:
                ids.update(b.quellen)
        for v in varianten:
            ids.update(kb.quellen_von_variante(v))
            z = kb.zustaendigkeiten.get(v.zustaendigkeit_id)
            if z:
                ids.update(z.quellen)
    return sorted(ids)


def protokoll_pfad(quelle_id: str, verzeichnis: Optional[Path] = None) -> Path:
    return Path(verzeichnis or PROTOKOLL_VERZEICHNIS) / f"{quelle_id}.md"


def hat_protokoll(quelle: Quelle, verzeichnis: Optional[Path] = None) -> bool:
    """Die Notiz verlinkt das Protokoll, und die Datei gibt es."""
    return bool(quelle.notiz) and f"pruefprotokolle/{quelle.id}.md" in (quelle.notiz or "") \
        and protokoll_pfad(quelle.id, verzeichnis).is_file()


def ohne_protokoll(kb: Wissensbasis, verzeichnis: Optional[Path] = None) -> list[str]:
    """Geprüfte Quellen (teilweise, verifiziert) ohne verlinktes Prüfprotokoll."""
    geprueft = (Pruefstatus.TEILWEISE, Pruefstatus.VERIFIZIERT)
    return sorted(q.id for q in kb.quellen.values()
                  if q.pruefstatus in geprueft and not hat_protokoll(q, verzeichnis))


def beschreibung(v: Verwendung) -> str:
    was = f"{v.objekt}: {v.art} „{v.text}“" if v.text else f"{v.objekt}: {v.art}"
    if v.erben:
        beispiele = ", ".join(v.erben[:3]) + (", …" if len(v.erben) > 3 else "")
        was += f" – gilt per erbt_von auch für {len(v.erben)} weitere Varianten ({beispiele})"
    return was


def _zelle(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def protokoll_geruest(kb: Wissensbasis, quelle_id: str, heute: date,
                      daten: Optional[Path] = None) -> str:
    """Prüfprotokoll nach der Vorlage aus #45, mit allen Verwendungen vorbefüllt."""
    q = kb.quellen[quelle_id]
    zeilen = [
        f"# Prüfprotokoll: {q.id}",
        "",
        f"- Quelle: {q.titel}, {q.url or '(keine URL)'}",
        "- Fassung/Stand: <z. B. zuletzt geändert durch Art. X G v. TT.MM.JJJJ> · abgerufen am <Datum>",
        "- Geprüft von: Claude (Recherche) · Abnahme: <Name, Datum>",
        f"- Prüfstatus vorher: {q.pruefstatus.value}"
        + (f" ({q.geprueft_am.isoformat()}, {q.geprueft_von})" if q.geprueft_am else ""),
        f"- Gerüst erzeugt am {heute.isoformat()} mit `./bai quellen --protokoll {q.id}`",
        "",
    ]
    if q.notiz:
        zeilen += [f"> Bisherige Notiz: {q.notiz}", ""]
    liste = verwendungen(kb, quelle_id, daten)
    zeilen += [
        f"## Verwendungen in der Wissensbasis ({len(liste)})",
        "",
        "| # | Verwendung in der Wissensbasis | Fundstelle | Wortlaut der Quelle (Zitat, Absatz) | Ergebnis |",
        "|---|---|---|---|---|",
    ]
    nr = 0
    for v in zusammenfassen(liste, phase1_gebiete(kb)):
        if isinstance(v, str):
            zeilen.append(f"| … | {_zelle(v)} (vollständig: `./bai quellen --verwendung {q.id} --alle`) |  |  |  |")
            continue
        nr += 1
        zeilen.append(f"| {nr} | {_zelle(beschreibung(v))} | `{v.datei}` `{v.pfad}` |  |  |")
    if not liste:
        zeilen.append("| – | Keine Verwendung gefunden – Quelle zuordnen oder entfernen |  |  |  |")
    zeilen += [
        "",
        "Ergebnis: ✅ stimmt mit dem Wortlaut überein · ❌ weicht ab (Korrektur nötig) · "
        "⚠️ unklar oder nur teilweise belegt",
        "",
        "## Abweichungen und Folgeaktionen",
        "",
        "- …",
        "",
    ]
    return "\n".join(zeilen)
