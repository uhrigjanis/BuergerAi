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
import re
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


def tabellenzellen(zeile: str) -> list[str]:
    """Zellen einer Markdown-Tabellenzeile. Trennt nur an nicht maskierten ``|``;
    ``\\|`` (so schreibt ``_zelle`` einen senkrechten Strich) bleibt Teil der Zelle."""
    innen = zeile.strip()
    innen = innen[1:] if innen.startswith("|") else innen
    innen = innen[:-1] if innen.endswith("|") and not innen.endswith("\\|") else innen
    return [z.strip().replace("\\|", "|") for z in re.split(r"(?<!\\)\|", innen)]


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


# ------------------------------------------------------------------ Abnahme
class AbnahmeFehler(Exception):
    """Die Abnahme ist nicht möglich; die Meldung sagt, was fehlt."""


@dataclass(frozen=True)
class Protokollstand:
    zeilen: int  # Tabellenzeilen mit Verwendungen
    ohne_ergebnis: int
    abweichungen: int  # ❌
    hinweise: int  # ⚠️


def protokoll_lesen(text: str) -> Protokollstand:
    """Zählt die Ergebnisse in der Tabelle „Verwendungen in der Wissensbasis“."""
    zeilen = ohne = abweichungen = hinweise = 0
    in_tabelle = False
    for zeile in text.splitlines():
        if zeile.startswith("## "):
            in_tabelle = zeile.startswith("## Verwendungen")
            continue
        if not in_tabelle or not zeile.startswith("|") or zeile.startswith(("|---", "| #", "| …", "| –")):
            continue
        zellen = tabellenzellen(zeile)
        ergebnis = zellen[-1] if len(zellen) >= 5 else ""
        zeilen += 1
        if not ergebnis:
            ohne += 1
        elif "❌" in ergebnis:
            abweichungen += 1
        elif "⚠" in ergebnis:
            hinweise += 1
    return Protokollstand(zeilen, ohne, abweichungen, hinweise)


def _quelldatei(kb: Wissensbasis, quelle_id: str) -> Path:
    for datei in kb.dateien:
        inhalt = json.loads(datei.read_text(encoding="utf-8"))
        if any(q.get("id") == quelle_id for q in inhalt.get("quellen", ())):
            return datei
    raise AbnahmeFehler(f"Quelle {quelle_id} in keiner Datei gefunden")


def _eintrag_ersetzen(text: str, quelle_id: str, aendern: Any) -> str:
    """Ersetzt nur den JSON-Eintrag der Quelle; der Rest der Datei bleibt Zeichen für Zeichen gleich.

    ``aendern`` bekommt den Eintrag (dict) und gibt den neuen zurück.
    """
    decoder = json.JSONDecoder()
    for treffer in re.finditer(r'"id"\s*:\s*' + re.escape(json.dumps(quelle_id)), text):
        start = text.rfind("{", 0, treffer.start())
        while start != -1:
            try:
                objekt, ende = decoder.raw_decode(text, start)
            except json.JSONDecodeError:
                objekt, ende = None, -1
            if isinstance(objekt, dict) and objekt.get("id") == quelle_id and ende > treffer.end():
                break
            start = text.rfind("{", 0, start)
        else:
            continue
        if "pruefstatus" not in objekt or "titel" not in objekt:
            continue  # gleiche ID, aber kein Quellen-Eintrag
        neu = aendern(dict(objekt))
        zeilenanfang = text.rfind("\n", 0, start) + 1
        einrueckung = text[zeilenanfang:start] if not text[zeilenanfang:start].strip() else ""
        if "\n" in text[start:ende]:
            block = json.dumps(neu, ensure_ascii=False, indent=2).replace("\n", "\n" + einrueckung)
        else:
            block = json.dumps(neu, ensure_ascii=False)
        ergebnis = text[:start] + block + text[ende:]
        # Sicherheitsnetz: inhaltlich darf sich nur dieser Eintrag geändert haben
        vorher, nachher = json.loads(text), json.loads(ergebnis)
        erwartet = json.loads(json.dumps(vorher))
        for q in erwartet.get("quellen", ()):
            if q.get("id") == quelle_id:
                q.clear()
                q.update(neu)
        if nachher != erwartet:
            raise AbnahmeFehler(f"Eintrag von {quelle_id} ließ sich nicht sicher ersetzen")
        return ergebnis
    raise AbnahmeFehler(f"Eintrag von {quelle_id} nicht gefunden")


def _felder_setzen(eintrag: dict[str, Any], werte: dict[str, Any]) -> dict[str, Any]:
    """Setzt Felder; neue Prüffelder stehen direkt hinter pruefstatus, sonst bleibt die Reihenfolge."""
    neu: dict[str, Any] = {}
    for k, v in eintrag.items():
        neu[k] = werte.get(k, v)
        if k == "pruefstatus":
            for zusatz in ("geprueft_am", "geprueft_von"):
                if zusatz in werte and zusatz not in eintrag:
                    neu[zusatz] = werte[zusatz]
    for k, v in werte.items():
        neu.setdefault(k, v)
    return neu


def _abnahme_im_protokoll(text: str, eintrag: str) -> str:
    if re.search(r"Abnahme:[^\n]*", text):
        return re.sub(r"Abnahme:[^\n]*", lambda _m: f"Abnahme: {eintrag}", text, count=1)
    zeilen = text.splitlines(keepends=True)
    letzte = max((i for i, z in enumerate(zeilen[:15]) if z.startswith("- ")), default=0)
    zeilen.insert(letzte + 1, f"- Abnahme: {eintrag}\n")
    return "".join(zeilen)


def abnehmen(kb: Wissensbasis, quelle_id: str, von: str, am: date, trotz_hinweisen: bool = False,
             protokolle: Optional[Path] = None) -> Path:
    """Setzt eine Quelle nach menschlicher Prüfung auf ``verifiziert`` (ADR 0004, ANF-QS-02).

    Gibt die geänderte Datendatei zurück. Prüft vorher Protokoll und Name.
    """
    von = von.strip()
    if not von:
        raise AbnahmeFehler("Name fehlt (--von)")
    if von.lower().startswith("claude"):
        raise AbnahmeFehler("'verifiziert' setzt nur ein Mensch – bitte den eigenen Namen angeben")
    q = kb.quellen.get(quelle_id)
    if q is None:
        raise AbnahmeFehler(f"Unbekannte Quelle {quelle_id}")
    pfad = protokoll_pfad(quelle_id, protokolle)
    if not hat_protokoll(q, protokolle):
        raise AbnahmeFehler(
            f"Kein verlinktes Prüfprotokoll: {pfad} muss existieren und in der Notiz der Quelle "
            f"als docs/pruefprotokolle/{quelle_id}.md genannt sein (anlegen: buergerai quellen --protokoll {quelle_id})")
    protokoll = pfad.read_text(encoding="utf-8")
    stand = protokoll_lesen(protokoll)
    if stand.zeilen == 0:
        raise AbnahmeFehler("Das Protokoll hat keine Verwendungen mit Ergebnis")
    if stand.ohne_ergebnis:
        raise AbnahmeFehler(f"{stand.ohne_ergebnis} von {stand.zeilen} Zeilen im Protokoll ohne Ergebnis")
    if stand.abweichungen:
        raise AbnahmeFehler(f"{stand.abweichungen} Abweichung(en) (❌) im Protokoll – erst korrigieren")
    if stand.hinweise and not trotz_hinweisen:
        raise AbnahmeFehler(f"{stand.hinweise} Zeile(n) mit ⚠️ im Protokoll – geklärt? Dann mit --trotz-hinweisen")

    datei = _quelldatei(kb, quelle_id)
    werte = {"pruefstatus": Pruefstatus.VERIFIZIERT.value, "geprueft_am": am.isoformat(), "geprueft_von": von}
    # Eine neue Abnahme erledigt auch den Hinweis des Änderungswächters (#64)
    text = _eintrag_ersetzen(datei.read_text(encoding="utf-8"), quelle_id, lambda e: _felder_setzen(
        {k: v for k, v in e.items() if k != "seit_pruefung_geaendert"}, werte))
    datei.write_text(text, encoding="utf-8")
    pfad.write_text(_abnahme_im_protokoll(protokoll, f"{von}, {am.strftime('%d.%m.%Y')}"), encoding="utf-8")
    return datei


def zuruecksetzen(kb: Wissensbasis, quelle_id: str, am: date, protokolle: Optional[Path] = None) -> Path:
    """Nimmt eine Abnahme zurück (z. B. nach einer Gesetzesänderung): Status wieder ``teilweise``."""
    q = kb.quellen.get(quelle_id)
    if q is None:
        raise AbnahmeFehler(f"Unbekannte Quelle {quelle_id}")
    if q.pruefstatus is not Pruefstatus.VERIFIZIERT:
        raise AbnahmeFehler(f"{quelle_id} ist nicht verifiziert (Status: {q.pruefstatus.value})")
    datei = _quelldatei(kb, quelle_id)
    text = _eintrag_ersetzen(datei.read_text(encoding="utf-8"), quelle_id,
                             lambda e: _felder_setzen(e, {"pruefstatus": Pruefstatus.TEILWEISE.value}))
    datei.write_text(text, encoding="utf-8")
    pfad = protokoll_pfad(quelle_id, protokolle)
    if pfad.is_file():
        vorher = f"{q.geprueft_von}, {q.geprueft_am.strftime('%d.%m.%Y') if q.geprueft_am else '?'}"
        pfad.write_text(_abnahme_im_protokoll(
            pfad.read_text(encoding="utf-8"),
            f"zurückgenommen am {am.strftime('%d.%m.%Y')} (vorher {vorher}) – erneut prüfen"), encoding="utf-8")
    return datei
