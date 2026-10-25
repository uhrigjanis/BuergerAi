"""JSON-API der Web-Oberfläche.

Jede Funktion bekommt bereits geparstes JSON und liefert ein JSON-fähiges
``dict``. Fehler werden als ``ApiFehler`` mit HTTP-Status gemeldet. Die
Ergebnisse kommen aus derselben Engine wie im Terminal (``planer.planen``).
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timezone
from typing import Any, Optional

from .. import __version__
from .. import gebiete as gebiete_mod
from .. import szenarien as szenarien_mod
from ..ausgabe import ABDECKUNG_TEXT, EBENE_TEXT, PERSON_NAME, PRUEF_TEXT, frage_zu, geburt_text
from ..fakten import PERSONEN, UNBEKANNT, EingabeFehler, wert_als_text
from ..fristen import BerechneteFrist
from ..modell import Gebiet
from ..planer import Anfrage, Bericht, Eintrag, landesabdeckung, planen
from ..regeln import Schritt, Wert, begruendung
from ..wissensbasis import Wissensbasis

FRIST_ART_TEXT = {"spaetestens": "spätestens", "fruehestens": "frühestens ab", "empfohlen": "empfohlen bis"}
MAX_FAKTEN = 200


class ApiFehler(Exception):
    def __init__(self, http_status: int, meldung: str, **extra: Any):
        super().__init__(meldung)
        self.status = http_status
        self.meldung = meldung
        self.extra = extra

    def json(self) -> dict[str, Any]:
        return {"fehler": self.meldung, **self.extra}


# ------------------------------------------------------------------ Helfer
def _text(daten: dict[str, Any], schluessel: str, max_laenge: int = 20) -> Optional[str]:
    wert = daten.get(schluessel)
    if wert is None or wert == "":
        return None
    if not isinstance(wert, str) or len(wert) > max_laenge:
        raise ApiFehler(400, f"Ungültiger Wert für {schluessel!r}")
    return wert.strip()


def _stichtag(daten: dict[str, Any]) -> date:
    roh = _text(daten, "stichtag")
    if roh is None:
        return date.today()
    # fromisoformat akzeptiert ab Python 3.11 auch 20261024 oder 2026-W43; erlaubt ist nur JJJJ-MM-TT
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", roh):
        raise ApiFehler(400, "Stichtag als JJJJ-MM-TT erwartet")
    try:
        return date.fromisoformat(roh)
    except ValueError as exc:
        raise ApiFehler(400, "Stichtag als JJJJ-MM-TT erwartet") from exc


def _wert_json(w: Any) -> Any:
    if w is UNBEKANNT:
        return "unbekannt"
    if isinstance(w, date):
        return w.isoformat()
    return w


def _gebiet_json(g: Gebiet) -> dict[str, Any]:
    return {"id": g.id, "name": g.name, "ebene": g.ebene.value, "ebene_text": EBENE_TEXT[g.ebene]}


def _gemeinde_wahl_json(kb: Wissensbasis, g: Gebiet) -> dict[str, Any]:
    kreis = gebiete_mod.kreis_von(kb, g)
    return {"id": g.id, "name": g.name, "kreis": kreis.name if kreis else None}


def _person(fid: str) -> Optional[str]:
    kopf = fid.split(".")[0]
    return kopf if kopf in PERSONEN else None


def frage_json(kb: Wissensbasis, fid: str) -> dict[str, Any]:
    """Alles, was die Oberfläche braucht, um eine Angabe abzufragen."""
    d = kb.fakt_definition(fid)
    if d is None:
        raise ApiFehler(400, f"Unbekannte Angabe {fid!r}")
    person = _person(fid)
    return {
        "id": fid,
        "frage": frage_zu(kb, fid),
        "hilfe": d.hilfe,
        "typ": d.typ,
        "optionen": [{"wert": w, "text": t} for w, t in d.optionen],
        "person": person,
        "person_name": PERSON_NAME[person] if person else None,
    }


def anzeige(kb: Wissensbasis, fid: str, wert: Any) -> str:
    """Wert lesbar machen; bei Auswahlfeldern die Beschriftung statt des Codes."""
    d = kb.fakt_definition(fid)
    if d is not None and d.typ == "auswahl":
        for w, text in d.optionen:
            if w == wert:
                return text
    return wert_als_text(wert)


def _anfrage(kb: Wissensbasis, daten: Any) -> Anfrage:
    if not isinstance(daten, dict):
        raise ApiFehler(400, "JSON-Objekt erwartet")
    roh_fakten = daten.get("fakten") or {}
    if not isinstance(roh_fakten, dict) or len(roh_fakten) > MAX_FAKTEN:
        raise ApiFehler(400, "'fakten' muss ein Objekt sein")
    for wert in roh_fakten.values():
        if not isinstance(wert, (str, int, float, bool)) or (isinstance(wert, str) and len(wert) > 40):
            raise ApiFehler(400, "Angaben müssen Text, Zahl oder ja/nein sein")
    try:
        fakten = szenarien_mod.fakten_parsen(kb, roh_fakten)
    except EingabeFehler as exc:
        raise ApiFehler(400, str(exc)) from exc
    return Anfrage(
        fakten=fakten,
        plz=_text(daten, "plz"),
        gemeinde=_text(daten, "gemeinde"),
        land=_text(daten, "land"),
        stichtag=_stichtag(daten),
    )


def _hierarchie(kb: Wissensbasis, anfrage: Anfrage) -> list[Gebiet]:
    try:
        return gebiete_mod.aufloesen(kb, anfrage.plz, anfrage.gemeinde, anfrage.land)
    except gebiete_mod.PlzMehrdeutig as exc:
        raise ApiFehler(
            409, str(exc), status="mehrdeutig", gemeinden=[_gemeinde_wahl_json(kb, g) for g in exc.gemeinden]
        ) from exc
    except gebiete_mod.PlzUnbekannt as exc:
        raise ApiFehler(409, str(exc), status="unbekannt", laender=laender_json(kb)) from exc
    except gebiete_mod.GebietFehler as exc:
        raise ApiFehler(400, str(exc), status="ungueltig") from exc


def laender_json(kb: Wissensbasis) -> list[dict[str, Any]]:
    return [
        {"kuerzel": g.kuerzel, "name": g.name, "abdeckung": landesabdeckung(kb, g, "geburt").value}
        for g in gebiete_mod.laender(kb)
    ]


# ------------------------------------------------------------------ Endpunkte
def meta(kb: Wissensbasis) -> dict[str, Any]:
    szenarien = []
    for s in szenarien_mod.alle(kb):
        szenarien.append({"id": s.id, "name": s.name, "beschreibung": s.beschreibung})
    return {"version": __version__, "heute": date.today().isoformat(), "laender": laender_json(kb), "szenarien": szenarien}


def ort(kb: Wissensbasis, daten: Any) -> dict[str, Any]:
    """Löst den Wohnort auf. Mehrdeutige/unbekannte PLZ ergeben 409 mit Auswahl."""
    anfrage = _anfrage(kb, {k: daten.get(k) for k in ("plz", "gemeinde", "land")} if isinstance(daten, dict) else daten)
    hierarchie = _hierarchie(kb, anfrage)
    return {
        "status": "ok",
        "plz": anfrage.plz,
        "gemeinde": anfrage.gemeinde,
        "land": anfrage.land,
        "hierarchie": [_gebiet_json(g) for g in hierarchie],
        "text": " → ".join(g.name for g in hierarchie),
    }


def szenario(kb: Wissensbasis, name: str) -> dict[str, Any]:
    """Liefert ein gespeichertes Szenario im Format, das ``bericht`` erwartet."""
    if not re.fullmatch(r"[a-z0-9_]+", name):
        raise ApiFehler(404, "Szenario nicht gefunden")
    try:
        s = szenarien_mod.finden(kb, name)
    except FileNotFoundError as exc:
        raise ApiFehler(404, "Szenario nicht gefunden") from exc
    a = s.anfrage
    return {
        "name": s.name,
        "beschreibung": s.beschreibung,
        "plz": a.plz,
        "gemeinde": a.gemeinde,
        "land": a.land,
        "stichtag": a.stichtag.isoformat(),
        "fakten": {k: _wert_json(v) for k, v in a.fakten.items()},
    }


def _grund_json(s: Schritt, kb: Wissensbasis) -> dict[str, Any]:
    d: dict[str, Any] = {"ergebnis": s.wert.value, "art": s.art, "text": s.text or s.fakt or ""}
    if s.art == "fakt" and s.fakt:
        if s.fakt in s.fehlend:
            d["fehlt"] = frage_zu(kb, s.fakt)
        elif s.ist is not None:
            d["angabe"] = anzeige(kb, s.fakt, s.ist)
    return d


def _frist_json(bf: BerechneteFrist) -> dict[str, Any]:
    return {
        "text": bf.frist.text,
        "art": bf.frist.art,
        "art_text": FRIST_ART_TEXT[bf.frist.art],
        "datum": bf.datum.isoformat() if bf.datum else None,
        "braucht_datum": bf.datum is None and bf.frist.bezug != "keiner",
        "voraussichtlich": bf.voraussichtlich,
        "tage_bis": bf.tage_bis,
        "abgelaufen": bf.abgelaufen,
        "bald": bf.tage_bis is not None and 0 <= bf.tage_bis <= 14 and bf.frist.art != "fruehestens",
    }


def _eintrag_json(e: Eintrag, kb: Wissensbasis) -> dict[str, Any]:
    v = e.variante.verfahren
    return {
        "id": e.leistung.id,
        "name": e.leistung.name,
        "kurz": e.leistung.kurz,
        "art": e.leistung.art,
        "ergebnis": e.ergebnis.value,
        "gebiet": _gebiet_json(e.gebiet),
        "abdeckung": e.abdeckung.value,
        "abdeckung_text": ABDECKUNG_TEXT[e.abdeckung],
        "pruefstatus": e.pruefstatus.value,
        "pruef_text": PRUEF_TEXT[e.pruefstatus],
        "zustaendigkeit": {
            "name": e.zustaendigkeit.name,
            "beschreibung": e.zustaendigkeit.beschreibung,
            "url": e.zustaendigkeit.url,
        },
        "betrag": e.betrag.text if e.betrag else None,
        "fristen": [_frist_json(bf) for bf in e.fristen],
        "voraussetzungen": [kb.leistungen[x].name for x in e.leistung.voraussetzungen if x in kb.leistungen],
        "hinweise": list(e.variante.hinweise),
        "personen": [
            {
                "person": p.person,
                "name": PERSON_NAME[p.person],
                "ergebnis": p.schritt.wert.value,
                "gruende": [_grund_json(s, kb) for s in begruendung(p.schritt)],
            }
            for p in e.personen
        ],
        "verfahren": {
            "unterlagen": list(v.unterlagen),
            "schritte": list(v.schritte),
            "kosten": v.kosten,
            "online_url": v.online_url,
            "hinweise": list(v.hinweise),
        },
        "quellen": [
            {"id": q.id, "titel": q.titel, "url": q.url, "typ": q.typ, "pruefstatus": q.pruefstatus.value}
            for q in e.quellen
        ],
        "offene_fragen": len(e.fehlend),
    }


def _zeitplan(bericht: Bericht) -> list[dict[str, Any]]:
    """Alle datierten Fristen relevanter Leistungen, nach Datum sortiert."""
    termine = []
    for e in bericht.eintraege:
        if e.ergebnis is Wert.NEIN:
            continue
        for bf in e.fristen:
            if bf.datum is None:
                continue
            termine.append({"leistung_id": e.leistung.id, "leistung": e.leistung.name, "ergebnis": e.ergebnis.value, **_frist_json(bf)})
    return sorted(termine, key=lambda t: (t["datum"], t["leistung"]))


def _aktiv(kb: Wissensbasis, fid: str, fakten: dict[str, Any]) -> bool:
    """False, wenn die Angabe nach einer späteren Änderung nicht mehr gilt (z. B. Termin nach der Geburt)."""
    d = kb.fakt_definition(fid)
    return d is None or d.nur_wenn is None or fakten.get(d.nur_wenn[0]) == d.nur_wenn[1]


def bericht_berechnen(kb: Wissensbasis, daten: Any) -> tuple[Anfrage, Bericht]:
    anfrage = _anfrage(kb, daten)
    _hierarchie(kb, anfrage)  # verständliche Fehler (mehrdeutig/unbekannt) vor der Planung
    return anfrage, planen(kb, anfrage)


def bericht(kb: Wissensbasis, daten: Any) -> dict[str, Any]:
    anfrage, b = bericht_berechnen(kb, daten)
    zaehler = {w.value: sum(1 for e in b.eintraege if e.ergebnis is w) for w in Wert}
    return {
        "stichtag": anfrage.stichtag.isoformat(),
        "ort": {"hierarchie": [_gebiet_json(g) for g in b.hierarchie], "text": " → ".join(g.name for g in b.hierarchie)},
        "kind": geburt_text(anfrage.fakten),
        "warnungen": b.warnungen,
        "fragen": [frage_json(kb, fid) for fid in b.fehlend],
        "angaben": [
            {**frage_json(kb, fid), "wert": _wert_json(w), "anzeige": anzeige(kb, fid, w), "aktiv": _aktiv(kb, fid, anfrage.fakten)}
            for fid, w in anfrage.fakten.items()
        ],
        "zaehler": zaehler,
        "leistungen": [_eintrag_json(e, kb) for e in b.eintraege],
        "zeitplan": _zeitplan(b),
    }


# ------------------------------------------------------------------ Kalender
def _ics_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _ics_falten(zeile: str) -> list[str]:
    """Zeilen nach RFC 5545 auf höchstens 75 Bytes falten."""
    teile: list[str] = []
    aktuell = ""
    for zeichen in zeile:
        grenze = 75 if not teile else 74  # Folgezeilen beginnen mit Leerzeichen
        if len((aktuell + zeichen).encode("utf-8")) > grenze:
            teile.append(aktuell)
            aktuell = ""
        aktuell += zeichen
    teile.append(aktuell)
    return [teile[0]] + [" " + t for t in teile[1:]]


def kalender(kb: Wissensbasis, daten: Any) -> str:
    """Fristen als iCalendar-Datei (ganztägige Termine)."""
    _, b = bericht_berechnen(kb, daten)
    jetzt = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    zeilen = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//BuergerAI//Phase 2//DE", "CALSCALE:GREGORIAN"]
    for t in _zeitplan(b):
        tag = date.fromisoformat(t["datum"])
        uid = hashlib.sha1(f"{t['leistung_id']}|{t['text']}|{t['datum']}".encode()).hexdigest()
        titel = f"{t['leistung']}: {t['art_text']}" + (" (voraussichtlich)" if t["voraussichtlich"] else "")
        zeilen += [
            "BEGIN:VEVENT",
            f"UID:{uid}@buergerai",
            f"DTSTAMP:{jetzt}",
            f"DTSTART;VALUE=DATE:{tag.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{date.fromordinal(tag.toordinal() + 1).strftime('%Y%m%d')}",
            f"SUMMARY:{_ics_text(titel)}",
            f"DESCRIPTION:{_ics_text(t['text'] + ' – Unverbindliche Orientierung, keine Rechtsberatung.')}",
            "END:VEVENT",
        ]
    zeilen.append("END:VCALENDAR")
    gefaltet = [teil for z in zeilen for teil in _ics_falten(z)]
    return "\r\n".join(gefaltet) + "\r\n"
