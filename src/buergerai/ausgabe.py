"""Darstellung von Berichten im Terminal (Text) und als JSON."""

from __future__ import annotations

import os
import sys
from datetime import date
from typing import Any, Optional

from .fakten import PERSONEN, UNBEKANNT, wert_als_text
from .fristen import BerechneteFrist
from .modell import Abdeckung, Ebene, Pruefstatus
from .planer import Bericht, Eintrag
from .regeln import Schritt, Wert, begruendung
from .wissensbasis import Wissensbasis


class Farbe:
    def __init__(self, aktiv: Optional[bool] = None):
        if aktiv is None:
            aktiv = sys.stdout.isatty() and "NO_COLOR" not in os.environ
        self.aktiv = aktiv

    def _c(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.aktiv else text

    def fett(self, t: str) -> str:
        return self._c("1", t)

    def gruen(self, t: str) -> str:
        return self._c("32", t)

    def rot(self, t: str) -> str:
        return self._c("31", t)

    def gelb(self, t: str) -> str:
        return self._c("33", t)

    def grau(self, t: str) -> str:
        return self._c("2", t)

    def blau(self, t: str) -> str:
        return self._c("36", t)


SYMBOL = {Wert.JA: "✓", Wert.NEIN: "✗", Wert.UNKLAR: "?"}
PERSON_NAME = {None: "Haushalt", "mutter": "Mutter", "partner": "Anderer Elternteil"}
ABDECKUNG_TEXT = {
    Abdeckung.VOLLSTAENDIG: "vollständig erfasst",
    Abdeckung.ALLGEMEIN: "nur allgemeine Daten, Details vor Ort fehlen",
}
PRUEF_TEXT = {
    Pruefstatus.VERIFIZIERT: "Quellen verifiziert",
    Pruefstatus.TEILWEISE: "Quellen teilweise geprüft",
    Pruefstatus.UNGEPRUEFT: "Quellen ungeprüft",
    Pruefstatus.WIDERSPRUECHLICH: "Quellen widersprüchlich",
}
EBENE_TEXT = {Ebene.BUND: "Bund", Ebene.LAND: "Land", Ebene.KREIS: "Kreis", Ebene.GEMEINDE: "Gemeinde"}


def datum(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def frist_text(bf: BerechneteFrist, f: Farbe) -> str:
    art = {"spaetestens": "spätestens", "fruehestens": "frühestens ab", "empfohlen": "empfohlen bis"}[
        bf.frist.art
    ]
    if bf.datum is None:
        if bf.frist.bezug == "keiner":
            return bf.frist.text
        return f"{bf.frist.text} {f.grau('(Datum fehlt für die Berechnung)')}"
    zusatz = []
    if bf.voraussichtlich:
        zusatz.append("voraussichtlich")
    if bf.tage_bis is not None:
        if bf.tage_bis < 0:
            zusatz.append(f"vor {-bf.tage_bis} Tagen")
        elif bf.tage_bis == 0:
            zusatz.append("heute")
        else:
            zusatz.append(f"in {bf.tage_bis} Tagen")
    kopf = f"{art} {datum(bf.datum)} ({', '.join(zusatz)})"
    if bf.abgelaufen:
        kopf = f.rot(kopf + " – ABGELAUFEN")
    elif bf.tage_bis is not None and 0 <= bf.tage_bis <= 14 and bf.frist.art != "fruehestens":
        kopf = f.gelb(kopf)
    return f"{kopf}: {bf.frist.text}"


def schritt_text(s: Schritt, kb: Wissensbasis, f: Farbe) -> str:
    if s.art == "pruefung_noetig":
        return f.gelb(f"! Prüfung nötig: {s.text}")
    sym = SYMBOL[s.wert]
    text = s.text or (s.fakt or "")
    if s.art == "fakt":
        if s.fakt and s.fakt in s.fehlend:
            definition = kb.fakt_definition(s.fakt)
            person = s.fakt.split(".")[0] if s.fakt.split(".")[0] in PERSONEN else None
            frage = definition.frage_fuer(person) if definition else s.fakt
            text += f.grau(f"  [Angabe fehlt: {frage}]")
        elif s.ist is UNBEKANNT:
            text += f.grau("  [Angabe: unbekannt]")
        elif s.ist is not None:
            definition = kb.fakt_definition(s.fakt) if s.fakt else None
            if definition is not None and definition.typ == "ja_nein":
                person = s.fakt.split(".")[0] if s.fakt.split(".")[0] in PERSONEN else None
                text += f.grau(f"  [{definition.frage_fuer(person)} → {wert_als_text(s.ist)}]")
            else:
                text += f.grau(f"  [Angabe: {wert_als_text(s.ist)}]")
    farbe = {Wert.JA: f.gruen, Wert.NEIN: f.rot, Wert.UNKLAR: f.gelb}[s.wert]
    return f"{farbe(sym)} {text}"


def _quellen_zeilen(e: Eintrag, f: Farbe) -> list[str]:
    zeilen = []
    for q in e.quellen:
        status = q.pruefstatus.value
        if q.pruefstatus is Pruefstatus.WIDERSPRUECHLICH:
            status = f.rot(status)
        elif q.pruefstatus is not Pruefstatus.VERIFIZIERT:
            status = f.gelb(status)
        zeilen.append(f"- {q.titel} [{status}]" + (f"\n        {f.grau(q.url)}" if q.url else ""))
    return zeilen


def eintrag_text(e: Eintrag, nr: int, kb: Wissensbasis, f: Farbe, details: bool) -> list[str]:
    l = e.leistung
    meta = [f"Daten: {EBENE_TEXT[e.gebiet.ebene]}", ABDECKUNG_TEXT[e.abdeckung], PRUEF_TEXT[e.pruefstatus]]
    zeilen = [f"{f.fett(f'{nr}. {l.name}')}  {f.grau('[' + ' · '.join(meta) + ']')}"]
    zeilen.append(f"   {l.kurz}")
    if len(e.personen) > 1 or e.personen[0].person is not None:
        teile = []
        for p in e.personen:
            farbe = {Wert.JA: f.gruen, Wert.NEIN: f.rot, Wert.UNKLAR: f.gelb}[p.schritt.wert]
            teile.append(f"{PERSON_NAME[p.person]}: {farbe(p.schritt.wert.value)}")
        zeilen.append("   Für: " + ", ".join(teile))
    zeilen.append(f"   Zuständig: {e.zustaendigkeit.name}")
    if e.zustaendigkeit.beschreibung and details:
        zeilen.append(f"              {f.grau(e.zustaendigkeit.beschreibung)}")
    if e.zustaendigkeit.url:
        zeilen.append(f"              {f.blau(e.zustaendigkeit.url)}")
    if e.betrag and e.ergebnis is not Wert.NEIN:
        zeilen.append(f"   Betrag: {e.betrag.text}")
    if e.ergebnis is not Wert.NEIN:
        for bf in e.fristen:
            zeilen.append(f"   Frist: {frist_text(bf, f)}")
    voraus = [kb.leistungen[v].name for v in l.voraussetzungen if v in kb.leistungen]
    if voraus and e.ergebnis is not Wert.NEIN:
        zeilen.append(f"   Vorher erledigen: {', '.join(voraus)}")
    for h in e.variante.hinweise:
        zeilen.append(f"   {f.gelb('Hinweis:')} {h}")

    titel = {Wert.JA: "Warum", Wert.NEIN: "Warum nicht", Wert.UNKLAR: "Warum unklar"}[e.ergebnis]
    zeilen.append(f"   {titel}:")
    for p in e.personen:
        if len(e.personen) > 1:
            zeilen.append(f"     {PERSON_NAME[p.person]}:")
        einrueck = "       " if len(e.personen) > 1 else "     "
        gruende = begruendung(p.schritt)
        if not gruende:
            zeilen.append(f"{einrueck}{f.gruen('✓')} Keine besonderen Voraussetzungen")
        for s in gruende:
            zeilen.append(einrueck + schritt_text(s, kb, f))

    if details and e.ergebnis is not Wert.NEIN:
        v = e.variante.verfahren
        if v.unterlagen:
            zeilen.append("   Unterlagen:")
            zeilen.extend(f"     - {u}" for u in v.unterlagen)
        if v.schritte:
            zeilen.append("   So geht's:")
            zeilen.extend(f"     {i}. {s}" for i, s in enumerate(v.schritte, 1))
        if v.kosten:
            zeilen.append(f"   Kosten: {v.kosten}")
        if v.online_url:
            zeilen.append(f"   Online: {f.blau(v.online_url)}")
        for h in v.hinweise:
            zeilen.append(f"   Hinweis: {h}")
    if details:
        zeilen.append("   Quellen:")
        zeilen.extend("     " + z for z in _quellen_zeilen(e, f))
    return zeilen


def ort_text(bericht: Bericht) -> str:
    return " → ".join(f"{g.name} ({EBENE_TEXT[g.ebene]} {g.id})" for g in bericht.hierarchie)


def geburt_text(fakten: dict[str, Any]) -> str:
    if fakten.get("kind_geboren") is True and isinstance(fakten.get("geburtsdatum"), date):
        return f"geboren am {datum(fakten['geburtsdatum'])}"
    if fakten.get("kind_geboren") is False and isinstance(fakten.get("errechneter_termin"), date):
        return f"errechneter Termin {datum(fakten['errechneter_termin'])}"
    if fakten.get("kind_geboren") is UNBEKANNT:
        return "unbekannt, ob schon geboren – Fristen können nicht berechnet werden"
    return "Datum noch nicht angegeben"


def bericht_text(
    bericht: Bericht, kb: Wissensbasis, farbe: Optional[Farbe] = None, details: bool = False
) -> str:
    f = farbe or Farbe()
    a = bericht.anfrage
    zeilen = [
        f.fett(f"BürgerAI – Lebensereignis {a.ereignis.capitalize()}") + f.grau(f"   (Stichtag {datum(a.stichtag)})"),
        f"Wohnort: {ort_text(bericht)}",
        f"Kind:    {geburt_text(a.fakten)}",
        f.grau("Hinweis: Unverbindliche Orientierung, keine Rechtsberatung. Verbindlich entscheidet die zuständige Stelle."),
    ]
    for w in bericht.warnungen:
        zeilen.append(f.gelb(f"⚠ {w}"))

    gruppen = [
        (Wert.JA, "Das steht Ihnen voraussichtlich zu / ist zu erledigen", f.gruen),
        (Wert.UNKLAR, "Unklar – fehlende Angaben oder Prüfung nötig", f.gelb),
        (Wert.NEIN, "Voraussichtlich kein Anspruch / nicht nötig", f.rot),
    ]
    nr = 0
    for wert, titel, farbfn in gruppen:
        eintraege = [e for e in bericht.eintraege if e.ergebnis is wert]
        if not eintraege:
            continue
        zeilen.append("")
        zeilen.append(farbfn(f.fett(f"== {titel} ({len(eintraege)}) ==")))
        for e in eintraege:
            nr += 1
            zeilen.append("")
            zeilen.extend(eintrag_text(e, nr, kb, f, details))

    if bericht.fehlend:
        zeilen.append("")
        zeilen.append(f.fett(f"== Offene Fragen ({len(bericht.fehlend)}) =="))
        zeilen.append(f.grau("Mit diesen Angaben werden die unklaren Punkte genauer:"))
        for fid in bericht.fehlend:
            zeilen.append(f"  - {frage_zu(kb, fid)}  {f.grau('--fakt ' + fid + '=…')}")
        zeilen.append(f.grau("Tipp: 'buergerai interaktiv' fragt diese Punkte nacheinander ab."))
    if not details:
        zeilen.append("")
        zeilen.append(f.grau("Mit --details: Unterlagen, Schritte, Kosten und Quellen je Leistung."))
    return "\n".join(zeilen)


def frage_zu(kb: Wissensbasis, fid: str) -> str:
    definition = kb.fakt_definition(fid)
    if definition is None:
        return fid
    person = fid.split(".")[0] if fid.split(".")[0] in PERSONEN else None
    return definition.frage_fuer(person)


def baum_text(s: Schritt, kb: Wissensbasis, f: Farbe, tiefe: int = 0) -> list[str]:
    einrueck = "  " * tiefe
    if s.art in ("alle", "eine"):
        titel = {"alle": "ALLE müssen erfüllt sein", "eine": "MINDESTENS EINE muss erfüllt sein"}[s.art]
        farbe = {Wert.JA: f.gruen, Wert.NEIN: f.rot, Wert.UNKLAR: f.gelb}[s.wert]
        zeilen = [f"{einrueck}{farbe(SYMBOL[s.wert] + ' ' + s.wert.value.upper())} {titel}" + (f": {s.text}" if s.text else "")]
        if not s.kinder:
            zeilen.append(f"{einrueck}  {f.grau('(keine Bedingungen)')}")
        for k in s.kinder:
            zeilen.extend(baum_text(k, kb, f, tiefe + 1))
        return zeilen
    if s.art == "nicht":
        zeilen = [einrueck + schritt_text(s, kb, f) + f.grau("  (Verneinung von:)")]
        zeilen.extend(baum_text(s.kinder[0], kb, f, tiefe + 2))
        return zeilen
    zeile = einrueck + schritt_text(s, kb, f)
    if s.quellen:
        zeile += f.grau(f"  <{', '.join(s.quellen)}>")
    return [zeile]


def _wert_json(w: Any) -> Any:
    if w is UNBEKANNT:
        return "unbekannt"
    if isinstance(w, date):
        return w.isoformat()
    return w


def schritt_json(s: Schritt) -> dict[str, Any]:
    d: dict[str, Any] = {"art": s.art, "ergebnis": s.wert.value}
    if s.text:
        d["text"] = s.text
    if s.fakt:
        d["fakt"] = s.fakt
        d["angabe"] = _wert_json(s.ist)
    if s.quellen:
        d["quellen"] = list(s.quellen)
    if s.fehlend:
        d["fehlend"] = s.fehlend
    if s.kinder:
        d["kinder"] = [schritt_json(k) for k in s.kinder]
    return d


def bericht_json(bericht: Bericht) -> dict[str, Any]:
    a = bericht.anfrage
    return {
        "anfrage": {
            "plz": a.plz,
            "gemeinde": a.gemeinde,
            "land": a.land,
            "ereignis": a.ereignis,
            "stichtag": a.stichtag.isoformat(),
            "fakten": {k: _wert_json(v) for k, v in a.fakten.items()},
        },
        "hierarchie": [{"id": g.id, "name": g.name, "ebene": g.ebene.value} for g in bericht.hierarchie],
        "warnungen": bericht.warnungen,
        "fehlende_angaben": bericht.fehlend,
        "leistungen": [
            {
                "id": e.leistung.id,
                "name": e.leistung.name,
                "ergebnis": e.ergebnis.value,
                "variante": e.variante.id,
                "gebiet": e.gebiet.id,
                "abdeckung": e.abdeckung.value,
                "pruefstatus": e.pruefstatus.value,
                "zustaendigkeit": e.zustaendigkeit.name,
                "betrag": e.betrag.text if e.betrag else None,
                "fristen": [
                    {
                        "text": bf.frist.text,
                        "art": bf.frist.art,
                        "datum": bf.datum.isoformat() if bf.datum else None,
                        "voraussichtlich": bf.voraussichtlich,
                    }
                    for bf in e.fristen
                ],
                "personen": [
                    {"person": p.person or "haushalt", "ergebnis": p.schritt.wert.value, "pruefung": schritt_json(p.schritt)}
                    for p in e.personen
                ],
                "quellen": [q.id for q in e.quellen],
            }
            for e in bericht.eintraege
        ],
    }
