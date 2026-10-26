"""Lädt die Wissensbasis aus ``data/`` und prüft ihre Konsistenz.

Jede JSON-Datei unter ``data/`` darf beliebige dieser Schlüssel enthalten:
``gebiete``, ``leistungen``, ``varianten``, ``quellen``, ``zustaendigkeiten``,
``abdeckung``. So können Bund, Länder und Kommunen getrennt gepflegt werden.

Fachliches gehört an feste Orte (ADR 0008):

- ``data/kern/``: Fakten und Rollen, die alle Fachmodule verwenden dürfen.
- ``data/fachmodule/<id>/``: ein Fachmodul (``fachmodul``, ``lebenslagen``,
  ``rollen``, ``fakten`` sowie seine Leistungen und Bundesvarianten).

Automatisch erzeugte Daten (Kreise, Gemeinden, PLZ) liegen unter
``data/generiert/`` (siehe ``gebietsimport.py``).
"""

from __future__ import annotations

import json
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from .fakten import ABLEITUNGEN, TYPEN, FaktDefinition
from .modell import (
    Betrag,
    Ebene,
    Fachmodul,
    Frist,
    Gebiet,
    Landesabdeckung,
    Lebenslage,
    Leistung,
    Leistungsvariante,
    Pruefstatus,
    Quelle,
    Rolle,
    Verfahren,
    Zeitraum,
    Zustaendigkeit,
    parse_datum,
)
from .regeln import OPERATOREN, RegelFehler, fakten_in_regel, knotentyp, quellen_in_regel

STANDARD_DATENVERZEICHNIS = Path(__file__).resolve().parents[2] / "data"

KERN = "kern"
LEISTUNG_ARTEN = ("pflicht", "antrag", "geldleistung", "foerderprogramm", "information")
BEANTRAGT_VON = ("selbst", "arbeitgeber", "angehoerige", "von_amts_wegen")
LEBENSLAGE_TYPEN = ("ereignis", "situation")
FRIST_BEZUEGE = ("geburt", "termin", "keiner")  # außerdem: ID eines Fakts vom Typ "datum"
FRIST_ARTEN = ("spaetestens", "fruehestens", "empfohlen")
LANDESLEISTUNGEN_WERTE = ("erfasst", "keine")
# Platzhalter in Namen und Beschreibungen von Zuständigkeiten, z. B. "Elterngeldstelle: {kreis}"
PLATZHALTER = ("gemeinde", "kreis", "land")


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
        nicht_vor=(roh["nicht_vor"]["bezug"], roh["nicht_vor"].get("tage", 0)) if "nicht_vor" in roh else None,
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


def _fuer(roh: Any) -> tuple[str, ...]:
    """``"haushalt"`` (oder fehlend) -> (), sonst Liste von Rollen."""
    if roh is None or roh == "haushalt":
        return ()
    if isinstance(roh, list) and roh and all(isinstance(r, str) for r in roh):
        return tuple(roh)
    raise ValueError(f"'fuer' muss \"haushalt\" oder eine nicht leere Liste von Rollen sein (war: {roh!r})")


def _ablage(datei: Path, wurzel: Path) -> Optional[str]:
    """Modul einer Datei: "kern", die ID des Fachmoduls oder None (andere Ablage)."""
    try:
        teile = datei.relative_to(wurzel).parts
    except ValueError:
        return None
    if teile and teile[0] == KERN:
        return KERN
    if len(teile) >= 3 and teile[0] == "fachmodule":
        return teile[1]
    return None


@dataclass
class Wissensbasis:
    gebiete: dict[str, Gebiet] = field(default_factory=dict)
    leistungen: dict[str, Leistung] = field(default_factory=dict)
    varianten: dict[str, Leistungsvariante] = field(default_factory=dict)
    quellen: dict[str, Quelle] = field(default_factory=dict)
    zustaendigkeiten: dict[str, Zustaendigkeit] = field(default_factory=dict)
    fakten: dict[str, FaktDefinition] = field(default_factory=dict)
    fachmodule: dict[str, Fachmodul] = field(default_factory=dict)
    lebenslagen: dict[str, Lebenslage] = field(default_factory=dict)
    rollen: dict[str, Rolle] = field(default_factory=dict)
    landesabdeckung: dict[tuple[str, str], Landesabdeckung] = field(default_factory=dict)
    dateien: list[Path] = field(default_factory=list)
    _roh_varianten: list[tuple[dict[str, Any], Path]] = field(default_factory=list, repr=False)
    # Indizes, die bei Bedarf neu aufgebaut werden, sobald sich die Zahl der Objekte ändert
    _indizes: dict[str, tuple[tuple[int, ...], Any]] = field(default_factory=dict, repr=False)
    _quellen_cache: dict[str, tuple[Leistungsvariante, list[str]]] = field(default_factory=dict, repr=False)

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
                kb._einlesen(inhalt, datei, _ablage(datei, verzeichnis), fehler)
            except (KeyError, ValueError, TypeError) as exc:
                fehler.append(f"{datei}: {type(exc).__name__}: {exc}")
        kb._varianten_aufloesen(fehler)
        if pruefen:
            fehler.extend(kb.konsistenz_pruefen())
        if fehler:
            raise DatenFehler(fehler)
        kb.indizes_aufbauen()
        return kb

    def indizes_aufbauen(self) -> None:
        """Baut alle Indizes vorab, damit die erste Anfrage nicht langsamer ist als die folgenden."""
        self.plz_index()
        self.bund()
        self._varianten_index()
        self.leistungen_fuer(())
        self.hat_landesdaten("")

    def _neu(self, ziel: dict[str, Any], objekt: Any, datei: Path, fehler: list[str]) -> None:
        if objekt.id in ziel:
            fehler.append(f"{datei}: doppelte ID {objekt.id}")
        ziel[objekt.id] = objekt

    def _einlesen(self, inhalt: dict[str, Any], datei: Path, modul: Optional[str], fehler: list[str]) -> None:
        bekannt = {"gebiete", "leistungen", "varianten", "quellen", "zustaendigkeiten", "fakten", "abdeckung",
                   "fachmodul", "lebenslagen", "rollen", "_hinweis", "_import"}
        for schluessel in inhalt:
            if schluessel not in bekannt:
                fehler.append(f"{datei}: unbekannter Schlüssel {schluessel}")
        for schluessel in ("fakten", "rollen"):
            if inhalt.get(schluessel) and modul is None:
                fehler.append(f"{datei}: '{schluessel}' gehören nach data/kern/ oder data/fachmodule/<id>/")
        for schluessel in ("fachmodul", "lebenslagen"):
            if inhalt.get(schluessel) and modul in (None, KERN):
                fehler.append(f"{datei}: '{schluessel}' gehört nach data/fachmodule/<id>/")
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
                    quellen=tuple(g.get("quellen", ())),
                    art=g.get("art"),
                    verband=(g["verband"]["id"], g["verband"]["name"]) if "verband" in g else None,
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
        if "fachmodul" in inhalt and modul not in (None, KERN):
            m = inhalt["fachmodul"]
            if m["id"] != modul:
                fehler.append(f"{datei}: Fachmodul {m['id']!r} muss in data/fachmodule/{m['id']}/ liegen")
            self._neu(
                self.fachmodule,
                Fachmodul(
                    id=m["id"],
                    name=m["name"],
                    beschreibung=m["beschreibung"],
                    abgrenzung=tuple(m.get("abgrenzung", ())),
                    importiert_fakten=tuple(m.get("importiert_fakten", ())),
                ),
                datei,
                fehler,
            )
        for l in inhalt.get("lebenslagen", []) if modul not in (None, KERN) else []:
            self._neu(
                self.lebenslagen,
                Lebenslage(
                    id=l["id"],
                    name=l["name"],
                    typ=l["typ"],
                    modul=modul,
                    beschreibung=l["beschreibung"],
                    einstiegsfragen=tuple(l.get("einstiegsfragen", ())),
                    synonyme=tuple(l.get("synonyme", ())),
                    beispiele=tuple(l.get("beispiele", ())),
                    nicht_erfasst=tuple((n["name"], n["grund"]) for n in l.get("nicht_erfasst", ())),
                ),
                datei,
                fehler,
            )
        for r in inhalt.get("rollen", []) if modul is not None else []:
            self._neu(
                self.rollen,
                Rolle(id=r["id"], name=r["name"], wer=r["wer"], modul=modul, vorbedingung=r.get("vorbedingung")),
                datei,
                fehler,
            )
        for l in inhalt.get("leistungen", []):
            if "ereignisse" in l:
                fehler.append(f"{datei}: Leistung {l['id']}: 'ereignisse' heißt jetzt 'lebenslagen'")
                continue
            art = l.get("art", "antrag")
            self._neu(
                self.leistungen,
                Leistung(
                    id=l["id"],
                    name=l["name"],
                    kurz=l["kurz"],
                    lebenslagen=tuple(l["lebenslagen"]),
                    verwaltungsebene=Ebene(l["verwaltungsebene"]),
                    fuer=_fuer(l.get("fuer")),
                    voraussetzungen=tuple(l.get("voraussetzungen", ())),
                    betraege=tuple(
                        Betrag(b["text"], _zeitraum(b), tuple(b.get("quellen", ())))
                        for b in l.get("betraege", ())
                    ),
                    art=art,
                    rechtsanspruch=l.get("rechtsanspruch", art != "foerderprogramm"),
                    beantragt_von=l.get("beantragt_von", "selbst"),
                    ortsbezug=l.get("ortsbezug"),
                ),
                datei,
                fehler,
            )
        for v in inhalt.get("varianten", []):
            self._roh_varianten.append((v, datei))
        for a in inhalt.get("abdeckung", []):
            if "ereignis" in a:
                fehler.append(f"{datei}: Abdeckung {a.get('gebiet_id')}: 'ereignis' heißt jetzt 'lebenslage'")
                continue
            nachweis = Landesabdeckung(
                gebiet_id=a["gebiet_id"],
                lebenslage=a["lebenslage"],
                landesleistungen=a["landesleistungen"],
                stand=parse_datum(a["stand"]),
                quellen=tuple(a.get("quellen", ())),
                notiz=a.get("notiz"),
            )
            schluessel = (nachweis.gebiet_id, nachweis.lebenslage)
            if schluessel in self.landesabdeckung:
                fehler.append(f"{datei}: doppelte Abdeckung für {nachweis.gebiet_id}/{nachweis.lebenslage}")
            self.landesabdeckung[schluessel] = nachweis
        for f in inhalt.get("fakten", []) if modul is not None else []:
            if "grunddaten" in f:
                fehler.append(f"{datei}: Fakt {f['id']}: 'grunddaten' entfällt, stattdessen 'einstiegsfragen' der Lebenslage")
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
                    nur_wenn=(f["nur_wenn"]["fakt"], f["nur_wenn"]["wert"]) if "nur_wenn" in f else None,
                    modul=modul,
                    ableitung=(f["ableitung"]["art"], f["ableitung"]["ort"]) if "ableitung" in f else None,
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

    # ------------------------------------------------------------- Indizes
    def _index(self, name: str, signatur: tuple[int, ...], bauen: Callable[[], Any]) -> Any:
        """Gibt einen Index zurück und baut ihn neu, wenn sich die Signatur geändert hat.

        Indizes speichern IDs statt Objekten. So bleiben sie gültig, wenn ein
        Objekt unter derselben ID ersetzt wird (z. B. in Tests).
        """
        vorhanden = self._indizes.get(name)
        if vorhanden is None or vorhanden[0] != signatur:
            vorhanden = (signatur, bauen())
            self._indizes[name] = vorhanden
        return vorhanden[1]

    def plz_index(self) -> dict[str, tuple[str, ...]]:
        """PLZ -> IDs der Gemeinden (nach Name sortiert)."""

        def bauen() -> dict[str, tuple[str, ...]]:
            index: dict[str, list[Gebiet]] = {}
            for g in self.gebiete.values():
                if g.ebene is Ebene.GEMEINDE:
                    for p in g.plz:
                        index.setdefault(p, []).append(g)
            return {p: tuple(g.id for g in sorted(gs, key=lambda g: (g.name, g.id))) for p, gs in index.items()}

        return self._index("plz", (len(self.gebiete),), bauen)

    def bund(self) -> Gebiet:
        """Das Gebiet der Ebene Bund (Wurzel der Hierarchie)."""
        gid = self._index(
            "bund", (len(self.gebiete),), lambda: next(g.id for g in self.gebiete.values() if g.ebene is Ebene.BUND)
        )
        return self.gebiete[gid]

    def _varianten_index(self) -> dict[str, tuple[str, ...]]:
        def bauen() -> dict[str, tuple[str, ...]]:
            index: dict[str, list[str]] = {}
            for v in self.varianten.values():
                index.setdefault(v.leistung_id, []).append(v.id)
            return {k: tuple(ids) for k, ids in index.items()}

        return self._index("varianten", (len(self.varianten),), bauen)

    def varianten_von(self, leistung_id: str) -> list[Leistungsvariante]:
        return [self.varianten[i] for i in self._varianten_index().get(leistung_id, ()) if i in self.varianten]

    def leistungen_fuer(self, lebenslagen: Iterable[str]) -> list[Leistung]:
        """Leistungen der Lebenslagen, jede nur einmal, nach ID sortiert."""

        def bauen() -> dict[str, tuple[str, ...]]:
            index: dict[str, list[str]] = {}
            for l in self.leistungen.values():
                for ll in l.lebenslagen:
                    index.setdefault(ll, []).append(l.id)
            return {k: tuple(ids) for k, ids in index.items()}

        index = self._index("lebenslagen", (len(self.leistungen),), bauen)
        ids = {i for ll in lebenslagen for i in index.get(ll, ())}
        return [self.leistungen[i] for i in sorted(ids) if i in self.leistungen]

    def hat_landesdaten(self, lebenslage: str) -> bool:
        """Gibt es für die Lebenslage irgendwo Varianten unterhalb der Bundesebene?

        Nur dann kann in einem Land ohne Recherche tatsächlich etwas fehlen.
        """

        def bauen() -> set[str]:
            ergebnis: set[str] = set()
            for v in self.varianten.values():
                leistung, gebiet = self.leistungen.get(v.leistung_id), self.gebiete.get(v.gebiet_id)
                if leistung and gebiet and gebiet.ebene is not Ebene.BUND:
                    ergebnis.update(leistung.lebenslagen)
            return ergebnis

        return lebenslage in self._index("landesdaten", (len(self.varianten), len(self.leistungen)), bauen)

    # ------------------------------------------------------------- Zugriffe
    def rolle_von_fakt(self, fakt_id: str) -> Optional[Rolle]:
        """Rolle aus dem Präfix einer Fakt-ID (``mutter.beschaeftigt`` -> Mutter), sonst None."""
        if "." not in fakt_id:
            return None
        return self.rollen.get(fakt_id.split(".", 1)[0])

    def fakt_definition(self, fakt_id: str) -> Optional[FaktDefinition]:
        """Definition zu einer (ggf. personenbezogenen) Fakt-ID wie ``mutter.beschaeftigt``."""
        if fakt_id in self.fakten:
            return self.fakten[fakt_id]
        if self.rolle_von_fakt(fakt_id) is not None:
            return self.fakten.get("person." + fakt_id.split(".", 1)[1])
        return None

    def einstiegsfragen(self, lebenslagen: Iterable[str]) -> list[FaktDefinition]:
        """Einstiegsfragen der Lebenslagen in der angegebenen Reihenfolge, ohne Dubletten."""
        ergebnis: list[FaktDefinition] = []
        for ll in lebenslagen:
            for fid in self.lebenslagen[ll].einstiegsfragen if ll in self.lebenslagen else ():
                d = self.fakten.get(fid)
                if d is not None and d not in ergebnis:
                    ergebnis.append(d)
        return ergebnis

    def module_von_leistung(self, leistung: Leistung) -> set[str]:
        return {self.lebenslagen[ll].modul for ll in leistung.lebenslagen if ll in self.lebenslagen}

    def quellen_von_variante(self, variante: Leistungsvariante) -> list[str]:
        """Alle Quellen einer Variante (eigene, aus der Regel, aus Fristen); zwischengespeichert."""
        vorhanden = self._quellen_cache.get(variante.id)
        if vorhanden is not None and vorhanden[0] is variante:
            return vorhanden[1]
        ids = list(variante.quellen)
        for q in quellen_in_regel(variante.regel):
            if q not in ids:
                ids.append(q)
        for f in variante.verfahren.fristen:
            ids.extend(q for q in f.quellen if q not in ids)
        self._quellen_cache[variante.id] = (variante, ids)
        return ids

    # -------------------------------------------------------------- Prüfung
    def konsistenz_pruefen(self) -> list[str]:
        """Prüft referenzielle Integrität, Regelsyntax und Modulgrenzen. Gibt Fehlertexte zurück."""
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

        # Fachmodule, Lebenslagen, Rollen
        for m in self.fachmodule.values():
            if m.id in self.rollen:
                fehler.append(f"Fachmodul {m.id}: ID darf nicht zugleich eine Rolle sein")
            for fid in m.importiert_fakten:
                d = self.fakten.get(fid)
                if d is None:
                    fehler.append(f"Fachmodul {m.id}: importiert unbekannten Fakt {fid}")
                elif d.modul in (m.id, KERN):
                    fehler.append(f"Fachmodul {m.id}: Import von {fid} ist unnötig (eigener oder Kern-Fakt)")
            if not any(ll.modul == m.id for ll in self.lebenslagen.values()):
                fehler.append(f"Fachmodul {m.id}: hat keine Lebenslage")
        for ll in self.lebenslagen.values():
            wo = f"Lebenslage {ll.id}"
            if ll.modul not in self.fachmodule:
                fehler.append(f"{wo}: Fachmodul {ll.modul} hat keinen Steckbrief (modul.json mit 'fachmodul')")
            if ll.typ not in LEBENSLAGE_TYPEN:
                fehler.append(f"{wo}: 'typ' muss eines von {LEBENSLAGE_TYPEN} sein")
            for fid in ll.einstiegsfragen:
                d = self.fakten.get(fid)
                if d is None:
                    fehler.append(f"{wo}: unbekannte Einstiegsfrage {fid}")
                elif d.modul not in (KERN, ll.modul):
                    fehler.append(f"{wo}: Einstiegsfrage {fid} gehört zum Modul {d.modul}")
                elif d.abgeleitet or d.je_person:
                    fehler.append(f"{wo}: Einstiegsfrage {fid} darf weder abgeleitet noch je Person sein")
            if not self.leistungen_fuer([ll.id]):
                fehler.append(f"{wo}: keine Leistung zugeordnet")
        for r in self.rollen.values():
            if r.vorbedingung is not None:
                fehler.extend(self._regel_pruefen(r.vorbedingung, f"Rolle {r.id} (Vorbedingung)", (), {KERN, r.modul}))

        # Fakten
        for f in self.fakten.values():
            if f.typ not in TYPEN:
                fehler.append(f"Fakt {f.id}: unbekannter Typ {f.typ}")
            if f.typ == "auswahl" and not f.optionen:
                fehler.append(f"Fakt {f.id}: Auswahl ohne Optionen")
            if f.je_person != f.id.startswith("person."):
                fehler.append(f"Fakt {f.id}: je_person passt nicht zum Präfix 'person.'")
            praefix = f.id.split(".", 1)[0]
            if "." in f.id and not f.je_person and praefix != f.modul and self.rolle_von_fakt(f.id) is None:
                fehler.append(f"Fakt {f.id}: Präfix vor dem Punkt muss eine Rolle oder das eigene Modul ({f.modul}) sein")
            if f.nur_wenn is not None and f.nur_wenn[0] not in self.fakten:
                fehler.append(f"Fakt {f.id}: nur_wenn verweist auf unbekannten Fakt {f.nur_wenn[0]}")
            if f.modul != KERN and f.modul not in self.fachmodule:
                fehler.append(f"Fakt {f.id}: Fachmodul {f.modul} hat keinen Steckbrief")
            if f.ableitung is not None:
                art, ort = f.ableitung
                quelle = self.fakten.get(ort)
                if art not in ABLEITUNGEN:
                    fehler.append(f"Fakt {f.id}: Ableitung {art!r} unbekannt (erlaubt: {', '.join(ABLEITUNGEN)})")
                if not f.abgeleitet or f.typ != "ja_nein":
                    fehler.append(f"Fakt {f.id}: Ableitung nur bei abgeleiteten Fakten vom Typ ja_nein")
                if quelle is None or quelle.typ != "ort":
                    fehler.append(f"Fakt {f.id}: Ableitung braucht einen Ortsfakt (war: {ort})")
                elif quelle.modul not in (KERN, f.modul):
                    fehler.append(f"Fakt {f.id}: Ortsfakt {ort} gehört zum Modul {quelle.modul}")

        # Zuständigkeiten / Quellen
        for z in self.zustaendigkeiten.values():
            quellen_ok(z.quellen, f"Zuständigkeit {z.id}")
            for text in (z.name, z.beschreibung or ""):
                try:
                    namen = {n for _, n, _, _ in string.Formatter().parse(text) if n is not None}
                except ValueError as exc:
                    fehler.append(f"Zuständigkeit {z.id}: ungültiger Platzhalter ({exc})")
                    continue
                for n in sorted(namen - set(PLATZHALTER)):
                    fehler.append(f"Zuständigkeit {z.id}: unbekannter Platzhalter {{{n}}} (erlaubt: {PLATZHALTER})")
        for q in self.quellen.values():
            if q.pruefstatus is Pruefstatus.VERIFIZIERT and not (q.geprueft_am and q.geprueft_von):
                fehler.append(f"Quelle {q.id}: 'verifiziert' braucht geprueft_am und geprueft_von")

        # Leistungen
        for l in self.leistungen.values():
            wo = f"Leistung {l.id}"
            if not l.lebenslagen:
                fehler.append(f"{wo}: braucht mindestens eine Lebenslage")
            for ll in l.lebenslagen:
                if ll not in self.lebenslagen:
                    fehler.append(f"{wo}: unbekannte Lebenslage {ll}")
            for r in l.fuer:
                if r not in self.rollen:
                    fehler.append(f"{wo}: unbekannte Rolle {r} in 'fuer'")
            if l.art not in LEISTUNG_ARTEN:
                fehler.append(f"{wo}: 'art' muss eines von {LEISTUNG_ARTEN} sein")
            if l.art == "foerderprogramm" and l.rechtsanspruch:
                fehler.append(f"{wo}: Förderprogramme haben keinen Rechtsanspruch")
            if l.beantragt_von not in BEANTRAGT_VON:
                fehler.append(f"{wo}: 'beantragt_von' muss eines von {BEANTRAGT_VON} sein")
            if l.ortsbezug is not None:
                d = self.fakten.get(l.ortsbezug)
                if d is None or d.typ != "ort":
                    fehler.append(f"{wo}: 'ortsbezug' muss ein Fakt vom Typ 'ort' sein (war: {l.ortsbezug})")
                elif not self._fakt_erlaubt(d, l):
                    fehler.append(f"{wo}: Ortsbezug {d.id} gehört zum Modul {d.modul}")
            for v in l.voraussetzungen:
                if v not in self.leistungen:
                    fehler.append(f"{wo}: unbekannte Voraussetzung {v}")
            for b in l.betraege:
                quellen_ok(b.quellen, f"{wo} (Betrag)")
            if not self.varianten_von(l.id):
                fehler.append(f"{wo}: keine Variante vorhanden")

        # Varianten
        for v in self.varianten.values():
            wo = f"Variante {v.id}"
            if v.leistung_id not in self.leistungen:
                fehler.append(f"{wo}: unbekannte Leistung {v.leistung_id}")
                continue
            leistung = self.leistungen[v.leistung_id]
            if v.gebiet_id not in self.gebiete:
                fehler.append(f"{wo}: unbekanntes Gebiet {v.gebiet_id}")
            if v.zustaendigkeit_id not in self.zustaendigkeiten:
                fehler.append(f"{wo}: unbekannte Zuständigkeit {v.zustaendigkeit_id}")
            if not v.quellen:
                fehler.append(f"{wo}: braucht mindestens eine Quelle")
            quellen_ok(v.quellen, wo)
            for fr in v.verfahren.fristen:
                if fr.bezug not in FRIST_BEZUEGE:
                    d = self.fakten.get(fr.bezug)
                    if d is None or d.typ != "datum":
                        fehler.append(f"{wo}: Frist-Bezug {fr.bezug} ist weder {FRIST_BEZUEGE} noch ein Datumsfakt")
                    elif not self._fakt_erlaubt(d, leistung):
                        fehler.append(f"{wo}: Frist-Bezug {d.id} gehört zum Modul {d.modul}")
                if fr.nicht_vor is not None:
                    d = self.fakten.get(fr.nicht_vor[0])
                    if d is None or d.typ != "datum" or not self._fakt_erlaubt(d, leistung):
                        fehler.append(f"{wo}: 'nicht_vor' braucht einen erlaubten Datumsfakt (war: {fr.nicht_vor[0]})")
                if fr.art not in FRIST_ARTEN:
                    fehler.append(f"{wo}: Frist-Art {fr.art} unbekannt")
                quellen_ok(fr.quellen, f"{wo} (Frist)")
            fehler.extend(self._regel_pruefen(v.regel, wo, leistung.fuer, self._erlaubte_module(leistung), leistung))

        # Abdeckung der Länder: "erfasst" nur mit eigener Landesleistung, "keine" nur ohne
        for (gid, lebenslage), a in self.landesabdeckung.items():
            wo = f"Abdeckung {gid}/{lebenslage}"
            gebiet = self.gebiete.get(gid)
            if gebiet is None or gebiet.ebene is not Ebene.LAND:
                fehler.append(f"{wo}: Gebiet muss ein Land sein")
                continue
            if lebenslage not in self.lebenslagen:
                fehler.append(f"{wo}: unbekannte Lebenslage {lebenslage}")
            if a.landesleistungen not in LANDESLEISTUNGEN_WERTE:
                fehler.append(f"{wo}: 'landesleistungen' muss eines von {LANDESLEISTUNGEN_WERTE} sein")
            if not a.quellen:
                fehler.append(f"{wo}: braucht mindestens eine Quelle")
            quellen_ok(a.quellen, wo)
            eigene = self.landesleistungen(gid, lebenslage)
            if a.landesleistungen == "erfasst" and not eigene:
                fehler.append(f"{wo}: 'erfasst', aber keine Landesleistung mit Variante für {gebiet.name}")
            if a.landesleistungen == "keine" and eigene:
                fehler.append(f"{wo}: 'keine', aber Landesleistungen vorhanden: {', '.join(eigene)}")
        return fehler

    def _erlaubte_module(self, leistung: Leistung) -> set[str]:
        return {KERN} | self.module_von_leistung(leistung)

    def _fakt_erlaubt(self, d: FaktDefinition, leistung: Leistung) -> bool:
        """Darf eine Regel der Leistung diesen Fakt verwenden? (Kern, eigene Module, Importe)"""
        module = self.module_von_leistung(leistung)
        if d.modul == KERN or d.modul in module:
            return True
        return any(d.id in self.fachmodule[m].importiert_fakten for m in module if m in self.fachmodule)

    def landesleistungen(self, land_id: str, lebenslage: str) -> list[str]:
        """Leistungen, die es nur auf Landesebene gibt (keine Bundesvariante), mit Variante in diesem Land."""
        bund_ids = {g.id for g in self.gebiete.values() if g.ebene is Ebene.BUND}
        ergebnis = []
        for l in self.leistungen_fuer([lebenslage]):
            varianten = self.varianten_von(l.id)
            if any(v.gebiet_id in bund_ids for v in varianten):
                continue
            if any(v.gebiet_id == land_id for v in varianten):
                ergebnis.append(l.id)
        return sorted(ergebnis)

    def _regel_pruefen(
        self,
        knoten: Any,
        wo: str,
        fuer: tuple[str, ...],
        module: set[str],
        leistung: Optional[Leistung] = None,
    ) -> list[str]:
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
            elif leistung is not None and not self._fakt_erlaubt(definition, leistung):
                fehler.append(f"{wo}: Fakt {fid} gehört zum Modul {definition.modul} (erlaubt: Kern, eigene Module, Importe)")
            elif leistung is None and definition.modul not in module:
                fehler.append(f"{wo}: Fakt {fid} gehört zum Modul {definition.modul}")
            if fid.startswith("person.") and not fuer:
                fehler.append(f"{wo}: 'person.'-Fakten nur bei Leistungen, die je Rolle geprüft werden ('fuer')")
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
            fehler.extend(self._regel_pruefen(knoten["nicht"], wo, fuer, module, leistung))
        elif typ == "lebenslage":
            ll = knoten["lebenslage"]
            if ll not in self.lebenslagen:
                fehler.append(f"{wo}: unbekannte Lebenslage {ll} im Regelknoten")
            elif leistung is not None and ll not in leistung.lebenslagen:
                fehler.append(f"{wo}: Regelknoten für Lebenslage {ll}, zu der die Leistung nicht gehört")
            if not knoten.get("text"):
                fehler.append(f"{wo}: 'lebenslage'-Knoten braucht einen 'text'")
            if "regel" not in knoten:
                fehler.append(f"{wo}: 'lebenslage'-Knoten braucht eine 'regel'")
            else:
                fehler.extend(self._regel_pruefen(knoten["regel"], wo, fuer, module, leistung))
        elif typ in ("alle", "eine"):
            if not isinstance(knoten[typ], list):
                fehler.append(f"{wo}: '{typ}' braucht eine Liste")
            else:
                for k in knoten[typ]:
                    fehler.extend(self._regel_pruefen(k, wo, fuer, module, leistung))
        return fehler

    def unbenutzte_fakten(self) -> list[str]:
        """Fakten im Katalog, die nirgends verwendet werden (Regeln, Einstiegsfragen, Rollen, Orte, Fristen)."""
        benutzt: set[str] = set()

        def merken(fid: str) -> None:
            definition = self.fakt_definition(fid)
            if definition is not None:
                benutzt.add(definition.id)
                if definition.nur_wenn:
                    benutzt.add(definition.nur_wenn[0])

        for v in self.varianten.values():
            for fid in fakten_in_regel(v.regel):
                merken(fid)
            for fr in v.verfahren.fristen:
                merken(fr.bezug)
                if fr.nicht_vor is not None:
                    merken(fr.nicht_vor[0])
        for ll in self.lebenslagen.values():
            for fid in ll.einstiegsfragen:
                merken(fid)
        for r in self.rollen.values():
            if r.vorbedingung is not None:
                for fid in fakten_in_regel(r.vorbedingung):
                    merken(fid)
        for l in self.leistungen.values():
            if l.ortsbezug:
                merken(l.ortsbezug)
        for f in list(self.fakten.values()):
            if f.ableitung and f.id in benutzt:
                merken(f.ableitung[1])
        return sorted(f.id for f in self.fakten.values() if f.id not in benutzt and not f.abgeleitet)
