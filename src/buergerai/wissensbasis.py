"""Lädt die Wissensbasis aus ``data/`` und prüft ihre Konsistenz.

Jede JSON-Datei unter ``data/`` darf beliebige dieser Schlüssel enthalten:
``gebiete``, ``leistungen``, ``varianten``, ``quellen``, ``zustaendigkeiten``,
``fakten``. So können Bund, Länder und Kommunen getrennt gepflegt werden.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .fakten import TYPEN, FaktDefinition
from .modell import (
    Betrag,
    Ebene,
    Frist,
    Gebiet,
    Leistung,
    Leistungsvariante,
    Pruefstatus,
    Quelle,
    Verfahren,
    Zeitraum,
    Zustaendigkeit,
    parse_datum,
)
from .regeln import OPERATOREN, RegelFehler, fakten_in_regel, knotentyp, quellen_in_regel

STANDARD_DATENVERZEICHNIS = Path(__file__).resolve().parents[2] / "data"

FUER_WERTE = ("haushalt", "mutter", "jeder_elternteil")
LEISTUNG_ARTEN = ("pflicht", "antrag", "geldleistung", "information")
FRIST_BEZUEGE = ("geburt", "termin", "keiner")
FRIST_ARTEN = ("spaetestens", "fruehestens", "empfohlen")


class DatenFehler(ValueError):
    def __init__(self, fehler: list[str]):
        super().__init__("Fehler in der Wissensbasis:\n- " + "\n- ".join(fehler))
        self.fehler = fehler


def _zeitraum(roh: dict[str, Any]) -> Zeitraum:
    return Zeitraum(parse_datum(roh.get("gueltig_ab")), parse_datum(roh.get("gueltig_bis")))


def _frist(roh: dict[str, Any]) -> Frist:
    return Frist(
        text=roh["text"],
        bezug=roh.get("bezug", "keiner"),
        art=roh.get("art", "spaetestens"),
        tage=roh.get("tage", 0),
        wochen=roh.get("wochen", 0),
        monate=roh.get("monate", 0),
        quellen=tuple(roh.get("quellen", ())),
    )


def _verfahren(roh: dict[str, Any]) -> Verfahren:
    return Verfahren(
        unterlagen=tuple(roh.get("unterlagen", ())),
        schritte=tuple(roh.get("schritte", ())),
        fristen=tuple(_frist(f) for f in roh.get("fristen", ())),
        kosten=roh.get("kosten"),
        online_url=roh.get("online_url"),
        hinweise=tuple(roh.get("hinweise", ())),
    )


@dataclass
class Wissensbasis:
    gebiete: dict[str, Gebiet] = field(default_factory=dict)
    leistungen: dict[str, Leistung] = field(default_factory=dict)
    varianten: dict[str, Leistungsvariante] = field(default_factory=dict)
    quellen: dict[str, Quelle] = field(default_factory=dict)
    zustaendigkeiten: dict[str, Zustaendigkeit] = field(default_factory=dict)
    fakten: dict[str, FaktDefinition] = field(default_factory=dict)
    dateien: list[Path] = field(default_factory=list)
    _roh_varianten: list[tuple[dict[str, Any], Path]] = field(default_factory=list, repr=False)

    # ------------------------------------------------------------------ Laden
    @classmethod
    def laden(cls, verzeichnis: Optional[Path] = None, pruefen: bool = True) -> "Wissensbasis":
        verzeichnis = Path(verzeichnis or STANDARD_DATENVERZEICHNIS)
        kb = cls()
        fehler: list[str] = []
        dateien = sorted(verzeichnis.rglob("*.json"))
        if not dateien:
            raise DatenFehler([f"Keine JSON-Dateien in {verzeichnis} gefunden"])
        for datei in dateien:
            kb.dateien.append(datei)
            try:
                inhalt = json.loads(datei.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                fehler.append(f"{datei}: ungültiges JSON ({exc})")
                continue
            try:
                kb._einlesen(inhalt, datei, fehler)
            except (KeyError, ValueError, TypeError) as exc:
                fehler.append(f"{datei}: {type(exc).__name__}: {exc}")
        kb._varianten_aufloesen(fehler)
        if pruefen:
            fehler.extend(kb.konsistenz_pruefen())
        if fehler:
            raise DatenFehler(fehler)
        return kb

    def _neu(self, ziel: dict[str, Any], objekt: Any, datei: Path, fehler: list[str]) -> None:
        if objekt.id in ziel:
            fehler.append(f"{datei}: doppelte ID {objekt.id}")
        ziel[objekt.id] = objekt

    def _einlesen(self, inhalt: dict[str, Any], datei: Path, fehler: list[str]) -> None:
        bekannt = {"gebiete", "leistungen", "varianten", "quellen", "zustaendigkeiten", "fakten", "_hinweis"}
        for schluessel in inhalt:
            if schluessel not in bekannt:
                fehler.append(f"{datei}: unbekannter Schlüssel {schluessel}")
        for g in inhalt.get("gebiete", []):
            self._neu(
                self.gebiete,
                Gebiet(
                    id=g["id"],
                    name=g["name"],
                    ebene=Ebene(g["ebene"]),
                    parent_id=g.get("parent_id"),
                    plz=tuple(g.get("plz", ())),
                    plz_praefixe=tuple(g.get("plz_praefixe", ())),
                    kuerzel=g.get("kuerzel"),
                    pilot=g.get("pilot", False),
                    quellen=tuple(g.get("quellen", ())),
                ),
                datei,
                fehler,
            )
        for q in inhalt.get("quellen", []):
            self._neu(
                self.quellen,
                Quelle(
                    id=q["id"],
                    titel=q["titel"],
                    url=q.get("url"),
                    typ=q["typ"],
                    herausgeber=q.get("herausgeber"),
                    pruefstatus=Pruefstatus(q["pruefstatus"]),
                    geprueft_am=parse_datum(q.get("geprueft_am")),
                    geprueft_von=q.get("geprueft_von"),
                    notiz=q.get("notiz"),
                ),
                datei,
                fehler,
            )
        for z in inhalt.get("zustaendigkeiten", []):
            self._neu(
                self.zustaendigkeiten,
                Zustaendigkeit(
                    id=z["id"],
                    name=z["name"],
                    beschreibung=z.get("beschreibung"),
                    url=z.get("url"),
                    quellen=tuple(z.get("quellen", ())),
                ),
                datei,
                fehler,
            )
        for l in inhalt.get("leistungen", []):
            self._neu(
                self.leistungen,
                Leistung(
                    id=l["id"],
                    name=l["name"],
                    kurz=l["kurz"],
                    ereignisse=tuple(l["ereignisse"]),
                    verwaltungsebene=Ebene(l["verwaltungsebene"]),
                    fuer=l["fuer"],
                    voraussetzungen=tuple(l.get("voraussetzungen", ())),
                    betraege=tuple(
                        Betrag(b["text"], _zeitraum(b), tuple(b.get("quellen", ())))
                        for b in l.get("betraege", ())
                    ),
                    art=l.get("art", "antrag"),
                ),
                datei,
                fehler,
            )
        for v in inhalt.get("varianten", []):
            self._roh_varianten.append((v, datei))
        for f in inhalt.get("fakten", []):
            self._neu(
                self.fakten,
                FaktDefinition(
                    id=f["id"],
                    typ=f["typ"],
                    frage=f["frage"],
                    hilfe=f.get("hilfe"),
                    optionen=tuple((o["wert"], o["text"]) for o in f.get("optionen", ())),
                    je_person=f.get("je_person", False),
                    abgeleitet=f.get("abgeleitet", False),
                    grunddaten=f.get("grunddaten", False),
                    nur_wenn=(f["nur_wenn"]["fakt"], f["nur_wenn"]["wert"]) if "nur_wenn" in f else None,
                ),
                datei,
                fehler,
            )

    def _varianten_aufloesen(self, fehler: list[str]) -> None:
        """Baut Varianten; ``erbt_von`` übernimmt Regel, Verfahren und Quellen einer
        anderen Variante (z. B. Landesvariante erbt die Bundesregel)."""
        roh: dict[str, tuple[dict[str, Any], Path]] = {}
        for v, d in self._roh_varianten:
            if v["id"] in roh:
                fehler.append(f"{d}: doppelte ID {v['id']}")
            roh[v["id"]] = (v, d)

        def aufgeloest(vid: str, kette: tuple[str, ...] = ()) -> dict[str, Any]:
            v, datei = roh[vid]
            basis_id = v.get("erbt_von")
            if not basis_id:
                return v
            if basis_id not in roh:
                raise ValueError(f"Variante {vid}: erbt_von unbekannte Variante {basis_id}")
            if basis_id in kette:
                raise ValueError(f"Variante {vid}: Zyklus bei erbt_von")
            basis = aufgeloest(basis_id, kette + (vid,))
            neu = {k: basis[k] for k in ("regel", "verfahren", "quellen", "hinweise") if k in basis}
            neu.update({k: w for k, w in v.items() if k != "erbt_von"})
            return neu

        for vid, (_, datei) in roh.items():
            try:
                v = aufgeloest(vid)
                self._neu(
                    self.varianten,
                    Leistungsvariante(
                        id=v["id"],
                        leistung_id=v["leistung_id"],
                        gebiet_id=v["gebiet_id"],
                        regel=v["regel"],
                        zustaendigkeit_id=v["zustaendigkeit_id"],
                        verfahren=_verfahren(v.get("verfahren", {})),
                        zeitraum=_zeitraum(v),
                        quellen=tuple(v.get("quellen", ())),
                        hinweise=tuple(v.get("hinweise", ())),
                    ),
                    datei,
                    fehler,
                )
            except (KeyError, ValueError, TypeError) as exc:
                fehler.append(f"{datei}: Variante {vid}: {type(exc).__name__}: {exc}")
        self._roh_varianten.clear()

    # ------------------------------------------------------------- Zugriffe
    def fakt_definition(self, fakt_id: str) -> Optional[FaktDefinition]:
        """Definition zu einer (ggf. personenbezogenen) Fakt-ID wie ``mutter.beschaeftigt``."""
        if fakt_id in self.fakten:
            return self.fakten[fakt_id]
        if "." in fakt_id:
            person, rest = fakt_id.split(".", 1)
            if person in ("mutter", "partner"):
                return self.fakten.get("person." + rest)
        return None

    def varianten_von(self, leistung_id: str) -> list[Leistungsvariante]:
        return [v for v in self.varianten.values() if v.leistung_id == leistung_id]

    def quellen_von_variante(self, variante: Leistungsvariante) -> list[str]:
        ids = list(variante.quellen)
        for q in quellen_in_regel(variante.regel):
            if q not in ids:
                ids.append(q)
        for f in variante.verfahren.fristen:
            ids.extend(q for q in f.quellen if q not in ids)
        return ids

    # -------------------------------------------------------------- Prüfung
    def konsistenz_pruefen(self) -> list[str]:
        """Prüft referenzielle Integrität und Regelsyntax. Gibt Fehlertexte zurück."""
        fehler: list[str] = []

        def quellen_ok(ids: tuple[str, ...] | list[str], wo: str) -> None:
            for q in ids:
                if q not in self.quellen:
                    fehler.append(f"{wo}: unbekannte Quelle {q}")

        # Gebiete
        for g in self.gebiete.values():
            if g.parent_id is None and g.ebene is not Ebene.BUND:
                fehler.append(f"Gebiet {g.id}: nur der Bund darf keinen Parent haben")
            if g.parent_id is not None:
                parent = self.gebiete.get(g.parent_id)
                if parent is None:
                    fehler.append(f"Gebiet {g.id}: unbekannter Parent {g.parent_id}")
                elif parent.ebene.rang >= g.ebene.rang:
                    fehler.append(f"Gebiet {g.id}: Parent {parent.id} ist nicht übergeordnet")
            if g.ebene is not Ebene.GEMEINDE and (g.plz or g.plz_praefixe):
                fehler.append(f"Gebiet {g.id}: PLZ dürfen nur an Gemeinden hängen")
            for p in g.plz:
                if not (len(p) == 5 and p.isdigit()):
                    fehler.append(f"Gebiet {g.id}: ungültige PLZ {p}")
            quellen_ok(g.quellen, f"Gebiet {g.id}")
        if sum(1 for g in self.gebiete.values() if g.ebene is Ebene.BUND) != 1:
            fehler.append("Es muss genau ein Gebiet der Ebene 'bund' geben")

        # Fakten
        for f in self.fakten.values():
            if f.typ not in TYPEN:
                fehler.append(f"Fakt {f.id}: unbekannter Typ {f.typ}")
            if f.typ == "auswahl" and not f.optionen:
                fehler.append(f"Fakt {f.id}: Auswahl ohne Optionen")
            if f.je_person != f.id.startswith("person."):
                fehler.append(f"Fakt {f.id}: je_person passt nicht zum Präfix 'person.'")
            if f.nur_wenn is not None and f.nur_wenn[0] not in self.fakten:
                fehler.append(f"Fakt {f.id}: nur_wenn verweist auf unbekannten Fakt {f.nur_wenn[0]}")

        # Zuständigkeiten / Quellen
        for z in self.zustaendigkeiten.values():
            quellen_ok(z.quellen, f"Zuständigkeit {z.id}")
        for q in self.quellen.values():
            if q.pruefstatus is Pruefstatus.VERIFIZIERT and not (q.geprueft_am and q.geprueft_von):
                fehler.append(f"Quelle {q.id}: 'verifiziert' braucht geprueft_am und geprueft_von")

        # Leistungen
        for l in self.leistungen.values():
            if l.fuer not in FUER_WERTE:
                fehler.append(f"Leistung {l.id}: 'fuer' muss eines von {FUER_WERTE} sein")
            if l.art not in LEISTUNG_ARTEN:
                fehler.append(f"Leistung {l.id}: 'art' muss eines von {LEISTUNG_ARTEN} sein")
            for v in l.voraussetzungen:
                if v not in self.leistungen:
                    fehler.append(f"Leistung {l.id}: unbekannte Voraussetzung {v}")
            for b in l.betraege:
                quellen_ok(b.quellen, f"Leistung {l.id} (Betrag)")
            if not self.varianten_von(l.id):
                fehler.append(f"Leistung {l.id}: keine Variante vorhanden")

        # Varianten
        for v in self.varianten.values():
            wo = f"Variante {v.id}"
            if v.leistung_id not in self.leistungen:
                fehler.append(f"{wo}: unbekannte Leistung {v.leistung_id}")
                continue
            if v.gebiet_id not in self.gebiete:
                fehler.append(f"{wo}: unbekanntes Gebiet {v.gebiet_id}")
            if v.zustaendigkeit_id not in self.zustaendigkeiten:
                fehler.append(f"{wo}: unbekannte Zuständigkeit {v.zustaendigkeit_id}")
            if not v.quellen:
                fehler.append(f"{wo}: braucht mindestens eine Quelle")
            quellen_ok(v.quellen, wo)
            for fr in v.verfahren.fristen:
                if fr.bezug not in FRIST_BEZUEGE:
                    fehler.append(f"{wo}: Frist-Bezug {fr.bezug} unbekannt")
                if fr.art not in FRIST_ARTEN:
                    fehler.append(f"{wo}: Frist-Art {fr.art} unbekannt")
                quellen_ok(fr.quellen, f"{wo} (Frist)")
            leistung = self.leistungen[v.leistung_id]
            fehler.extend(self._regel_pruefen(v.regel, wo, leistung.fuer))
        return fehler

    def _regel_pruefen(self, knoten: Any, wo: str, fuer: str) -> list[str]:
        fehler: list[str] = []
        if not isinstance(knoten, dict):
            return [f"{wo}: Regelknoten muss ein Objekt sein: {knoten!r}"]
        try:
            typ = knotentyp(knoten)
        except RegelFehler as exc:
            return [f"{wo}: {exc}"]
        for q in knoten.get("quellen", ()):
            if q not in self.quellen:
                fehler.append(f"{wo}: Regel verweist auf unbekannte Quelle {q}")
        if typ == "fakt":
            fid = knoten["fakt"]
            definition = self.fakt_definition(fid)
            if definition is None:
                fehler.append(f"{wo}: unbekannter Fakt {fid}")
            if fid.startswith("person.") and fuer != "jeder_elternteil":
                fehler.append(f"{wo}: 'person.'-Fakten nur bei Leistungen 'jeder_elternteil'")
            if knoten.get("op") not in OPERATOREN:
                fehler.append(f"{wo}: unbekannter Operator {knoten.get('op')!r}")
            if not knoten.get("text"):
                fehler.append(f"{wo}: Fakt-Bedingung {fid} braucht einen 'text'")
            if definition and definition.typ == "auswahl":
                erlaubt = {w for w, _ in definition.optionen}
                soll = knoten.get("wert")
                for w in soll if isinstance(soll, list) else [soll]:
                    if w not in erlaubt:
                        fehler.append(f"{wo}: Wert {w!r} ist keine Option von {fid}")
        elif typ == "nicht":
            if not knoten.get("text"):
                fehler.append(f"{wo}: 'nicht'-Knoten braucht einen 'text'")
            fehler.extend(self._regel_pruefen(knoten["nicht"], wo, fuer))
        elif typ in ("alle", "eine"):
            if not isinstance(knoten[typ], list):
                fehler.append(f"{wo}: '{typ}' braucht eine Liste")
            else:
                for k in knoten[typ]:
                    fehler.extend(self._regel_pruefen(k, wo, fuer))
        return fehler

    def unbenutzte_fakten(self) -> list[str]:
        """Fakten im Katalog, die weder in Regeln vorkommen noch Grunddaten sind."""
        benutzt: set[str] = set()
        for v in self.varianten.values():
            for fid in fakten_in_regel(v.regel):
                definition = self.fakt_definition(fid)
                if definition is not None:
                    benutzt.add(definition.id)
        return sorted(
            f.id
            for f in self.fakten.values()
            if f.id not in benutzt and not f.abgeleitet and not f.grunddaten
        )
