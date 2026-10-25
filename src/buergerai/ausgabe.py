"""Darstellung von Berichten im Terminal (Text) und als JSON."""

from __future__ import annotations

import os
import sys
from datetime import date
from typing import Any, Optional

from .fakten import UNBEKANNT, wert_als_text
from .fristen import BerechneteFrist
from .modell import Abdeckung, Ebene, Leistung, Pruefstatus
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
BEANTRAGT_TEXT = {
    "selbst": None,
    "arbeitgeber": "Den Antrag stellt der Arbeitgeber, nicht Sie selbst.",
    "angehoerige": "Den Antrag stellen Angehörige bzw. Hinterbliebene.",
    "von_amts_wegen": "Kein Antrag nötig: Die Stelle wird von sich aus tätig.",
}
ABDECKUNG_TEXT = {
    Abdeckung.ERFASST: "zuständige Stelle erfasst",
    Abdeckung.ALLGEMEIN: "nur allgemeine Angaben, Stelle vor Ort nicht erfasst",
    Abdeckung.FEHLT: "nicht erfasst",
}
PRUEF_TEXT = {
    Pruefstatus.VERIFIZIERT: "Quellen verifiziert",
    Pruefstatus.TEILWEISE: "Quellen teilweise geprüft",
    Pruefstatus.UNGEPRUEFT: "Quellen ungeprüft",
    Pruefstatus.WIDERSPRUECHLICH: "Quellen widersprüchlich",
}
EBENE_TEXT = {Ebene.BUND: "Bund", Ebene.LAND: "Land", Ebene.KREIS: "Kreis", Ebene.GEMEINDE: "Gemeinde"}


def person_name(kb: Wissensbasis, person: Optional[str]) -> str:
    """Kurzname einer Rolle (z. B. "Mutter"); ``None`` steht für den ganzen Haushalt."""
    if person is None:
        return "Haushalt"
    rolle = kb.rollen.get(person)
    return rolle.name if rolle else person


def anspruch_text(l: Leistung) -> Optional[str]:
    """Hinweis bei Leistungen ohne Rechtsanspruch (Förderprogramme, Ermessen)."""
    if l.art == "foerderprogramm":
        return "Förderprogramm ohne Rechtsanspruch: Förderung nur, solange Mittel vorhanden sind. Programme können enden."
    if not l.rechtsanspruch:
        return "Kein Rechtsanspruch: Die zuständige Stelle entscheidet nach Ermessen."
    return None


def lebenslagen_text(kb: Wissensbasis, ids: list[str]) -> str:
    return ", ".join(kb.lebenslagen[i].name if i in kb.lebenslagen else i for i in ids)


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
            text += f.grau(f"  [Angabe fehlt: {frage_zu(kb, s.fakt)}]")
        elif s.ist is UNBEKANNT:
            text += f.grau("  [Angabe: unbekannt]")
        elif s.ist is not None:
            definition = kb.fakt_definition(s.fakt) if s.fakt else None
            if definition is not None and definition.typ == "ja_nein" and s.fakt:
                text += f.grau(f"  [{frage_zu(kb, s.fakt)} → {wert_als_text(s.ist)}]")
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


def eintrag_text(
    e: Eintrag, nr: int, kb: Wissensbasis, f: Farbe, details: bool, mehrere_lebenslagen: bool = False
) -> list[str]:
    l = e.leistung
    meta = [f"Daten: {EBENE_TEXT[e.gebiet.ebene]}", ABDECKUNG_TEXT[e.abdeckung], PRUEF_TEXT[e.pruefstatus]]
    zeilen = [f"{f.fett(f'{nr}. {l.name}')}  {f.grau('[' + ' · '.join(meta) + ']')}"]
    zeilen.append(f"   {l.kurz}")
    if mehrere_lebenslagen and e.lebenslagen:
        zeilen.append(f"   {f.grau('Lebenslage: ' + lebenslagen_text(kb, e.lebenslagen))}")
    if len(e.personen) > 1 or e.personen[0].person is not None:
        teile = []
        for p in e.personen:
            farbe = {Wert.JA: f.gruen, Wert.NEIN: f.rot, Wert.UNKLAR: f.gelb}[p.schritt.wert]
            teile.append(f"{person_name(kb, p.person)}: {farbe(p.schritt.wert.value)}")
        zeilen.append("   Für: " + ", ".join(teile))
    if anspruch_text(l):
        zeilen.append(f"   {f.gelb('Hinweis:')} {anspruch_text(l)}")
    if BEANTRAGT_TEXT.get(l.beantragt_von):
        zeilen.append(f"   Wer beantragt: {BEANTRAGT_TEXT[l.beantragt_von]}")
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
            zeilen.append(f"     {person_name(kb, p.person)}:")
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
    titel = "Lebenslage" if len(a.lebenslagen) == 1 else "Lebenslagen"
    zeilen = [
        f.fett(f"BürgerAI – {titel} {lebenslagen_text(kb, a.lebenslagen)}") + f.grau(f"   (Stichtag {datum(a.stichtag)})"),
        f"Wohnort: {ort_text(bericht)}",
    ]
    if "geburt" in a.lebenslagen:
        zeilen.append(f"Kind:    {geburt_text(a.fakten)}")
    zeilen.append(
        f.grau("Hinweis: Unverbindliche Orientierung, keine Rechtsberatung. Verbindlich entscheidet die zuständige Stelle.")
    )
    for w in bericht.warnungen:
        zeilen.append(f.gelb(f"⚠ {w}"))
    if bericht.nur_andere_laender:
        zeilen.append(f.grau("Nur in anderen Ländern (hier nicht verfügbar): " + nur_andere_laender_text(bericht)))

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
            zeilen.extend(eintrag_text(e, nr, kb, f, details, len(a.lebenslagen) > 1))

    if bericht.nicht_erfasst:
        zeilen.append("")
        zeilen.append(f.fett(f"== Noch nicht erfasst ({len(bericht.nicht_erfasst)}) =="))
        for ll, name, grund in bericht.nicht_erfasst:
            zusatz = f" ({lebenslagen_text(kb, [ll])})" if len(a.lebenslagen) > 1 else ""
            zeilen.append(f"  - {name}{zusatz}: {f.grau(grund)}")

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


def nur_andere_laender_text(bericht: Bericht) -> str:
    return "; ".join(
        f"{n.leistung.name} ({', '.join(g.name for g in n.laender)})" for n in bericht.nur_andere_laender
    )


def frage_zu(kb: Wissensbasis, fid: str) -> str:
    definition = kb.fakt_definition(fid)
    if definition is None:
        return fid
    rolle = kb.rolle_von_fakt(fid)
    return definition.frage_fuer(rolle.wer if rolle else None)


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
            "lebenslagen": list(a.lebenslagen),
            "stichtag": a.stichtag.isoformat(),
            "fakten": {k: _wert_json(v) for k, v in a.fakten.items()},
        },
        "hierarchie": [{"id": g.id, "name": g.name, "ebene": g.ebene.value} for g in bericht.hierarchie],
        "warnungen": bericht.warnungen,
        "fehlende_angaben": bericht.fehlend,
        "nicht_erfasst": [
            {"lebenslage": ll, "name": n, "grund": g} for ll, n, g in bericht.nicht_erfasst
        ],
        "nur_andere_laender": [
            {"id": n.leistung.id, "name": n.leistung.name, "laender": [g.kuerzel for g in n.laender]}
            for n in bericht.nur_andere_laender
        ],
        "leistungen": [
            {
                "id": e.leistung.id,
                "name": e.leistung.name,
                "ergebnis": e.ergebnis.value,
                "lebenslagen": e.lebenslagen,
                "art": e.leistung.art,
                "rechtsanspruch": e.leistung.rechtsanspruch,
                "beantragt_von": e.leistung.beantragt_von,
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
