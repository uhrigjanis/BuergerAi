"""Fachmodule (ADR 0008): Lebenslagen, Modulgrenzen, mehrere Lebenslagen, Ortsbezug, Förderprogramme.

Die echten Daten haben bisher nur das Fachmodul Familie. Die neuen Fähigkeiten
werden deshalb mit einem Probe-Modul in einer Kopie der Wissensbasis geprüft.
"""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Optional

import pytest

from buergerai import gebiete
from buergerai.ausgabe import Farbe, bericht_json, bericht_text, frage_zu, person_name
from buergerai.fakten import EingabeFehler
from buergerai.planer import Anfrage, fragen_priorisieren, planen
from buergerai.regeln import Wert
from buergerai.suche import lebenslagen_suchen
from buergerai.szenarien import fakten_parsen
from buergerai.web import api
from buergerai.wissensbasis import STANDARD_DATENVERZEICHNIS, DatenFehler, Wissensbasis

STICHTAG = date(2026, 10, 24)

QUELLE = {"id": "probe_quelle", "titel": "Probe-Richtlinie", "url": "https://example.org/probe", "typ": "behoerde",
          "herausgeber": "Probe", "pruefstatus": "ungeprueft", "geprueft_am": None, "geprueft_von": None}


def probe_modul() -> dict[str, dict[str, Any]]:
    """Dateien des Probe-Moduls: zwei Lebenslagen, Förderprogramm mit Ortsbezug, geteilte Leistung."""
    return {
        "modul.json": {
            "fachmodul": {"id": "probe", "name": "Probe-Modul", "beschreibung": "Nur für Tests."},
            "lebenslagen": [
                {"id": "probe_kauf", "name": "Probekauf", "typ": "ereignis", "beschreibung": "Kauf einer Immobilie",
                 "einstiegsfragen": ["probe.kaufdatum"], "synonyme": ["Hauskauf", "Wohnung kaufen"],
                 "beispiele": ["Wir kaufen ein Haus."]},
                {"id": "probe_einkommen", "name": "Probeeinkommen", "typ": "situation",
                 "beschreibung": "Wenig Geld im Haushalt", "synonyme": ["wenig Geld"]},
            ],
        },
        "fakten.json": {
            "fakten": [
                {"id": "probe.kaufdatum", "typ": "datum", "frage": "Wann wurde der Kaufvertrag unterschrieben?"},
                {"id": "probe.ort_immobilie", "typ": "ort", "frage": "Wo liegt die Immobilie (PLZ)?"},
                {"id": "probe.erstkauf", "typ": "ja_nein", "frage": "Ist es Ihre erste eigene Immobilie?"},
            ]
        },
        "leistungen.json": {
            "quellen": [QUELLE],
            "zustaendigkeiten": [{"id": "probe_stelle", "name": "Probestelle – {land}"}],
            "leistungen": [
                {"id": "probe_zuschuss", "name": "Probezuschuss", "kurz": "Zuschuss zum Kauf", "lebenslagen": ["probe_kauf"],
                 "verwaltungsebene": "land", "fuer": "haushalt", "art": "foerderprogramm",
                 "ortsbezug": "probe.ort_immobilie"},
                {"id": "probe_geteilt", "name": "Geteilte Leistung", "kurz": "Gehört zu zwei Lebenslagen",
                 "lebenslagen": ["probe_kauf", "probe_einkommen"], "verwaltungsebene": "bund", "fuer": "haushalt",
                 "art": "geldleistung", "rechtsanspruch": False, "beantragt_von": "arbeitgeber"},
                {"id": "probe_pflicht", "name": "Probepflicht", "kurz": "Pflicht nach dem Kauf",
                 "lebenslagen": ["probe_kauf"], "verwaltungsebene": "bund", "fuer": "haushalt", "art": "pflicht"},
            ],
            "varianten": [
                {"id": "probe_zuschuss_he", "leistung_id": "probe_zuschuss", "gebiet_id": "06",
                 "zustaendigkeit_id": "probe_stelle", "quellen": ["probe_quelle"],
                 "regel": {"fakt": "probe.erstkauf", "op": "==", "wert": True, "text": "Erste eigene Immobilie"},
                 "verfahren": {"fristen": [{"text": "Antrag binnen 6 Monaten nach dem Kauf", "bezug": "probe.kaufdatum",
                                            "monate": 6}]}},
                {"id": "probe_geteilt_bund", "leistung_id": "probe_geteilt", "gebiet_id": "DE",
                 "zustaendigkeit_id": "probe_stelle", "quellen": ["probe_quelle"],
                 "regel": {"fakt": "brutto_haushalt_monat", "op": "<", "wert": 3000, "text": "Geringes Einkommen"}},
                {"id": "probe_pflicht_bund", "leistung_id": "probe_pflicht", "gebiet_id": "DE",
                 "zustaendigkeit_id": "probe_stelle", "quellen": ["probe_quelle"], "regel": {"alle": []},
                 "verfahren": {"fristen": [{"text": "Binnen zwei Wochen melden", "bezug": "probe.kaufdatum", "tage": 14}]}},
            ],
        },
    }


def daten_mit_probe(tmp_path: Path, aendern: Optional[Callable[[dict[str, dict[str, Any]]], None]] = None) -> Path:
    ziel = tmp_path / "data"
    shutil.copytree(STANDARD_DATENVERZEICHNIS, ziel)
    dateien = probe_modul()
    if aendern:
        aendern(dateien)
    ordner = ziel / "fachmodule" / "probe"
    ordner.mkdir(parents=True)
    for name, inhalt in dateien.items():
        (ordner / name).write_text(json.dumps(inhalt, ensure_ascii=False), encoding="utf-8")
    return ziel


@pytest.fixture(scope="module")
def probe_kb(tmp_path_factory) -> Wissensbasis:
    return Wissensbasis.laden(daten_mit_probe(tmp_path_factory.mktemp("probe")))


def plane(kb: Wissensbasis, lebenslagen: list[str], fakten: Optional[dict[str, Any]] = None, plz: str = "80331") -> Any:
    return planen(kb, Anfrage(fakten=fakten_parsen(kb, fakten or {}), plz=plz, lebenslagen=lebenslagen, stichtag=STICHTAG))


def fehler_beim_laden(tmp_path: Path, aendern: Callable[[dict[str, dict[str, Any]]], None]) -> list[str]:
    with pytest.raises(DatenFehler) as info:
        Wissensbasis.laden(daten_mit_probe(tmp_path, aendern))
    return info.value.fehler


# ------------------------------------------------------------------ Struktur und Modulgrenzen
@pytest.mark.anforderung("ANF-MOD-01")
def test_echte_daten_haben_fachmodul_familie(kb):
    assert set(kb.fachmodule) == {"familie", "umzug"}
    geburt = kb.lebenslagen["geburt"]
    assert geburt.modul == "familie" and geburt.typ == "ereignis"
    assert geburt.einstiegsfragen[0] == "kind_geboren"
    assert {r.id for r in kb.rollen.values()} == {"mutter", "partner"}
    assert kb.fakten["brutto_haushalt_monat"].modul == "kern"
    assert kb.fakten["eltern_verheiratet"].modul == "familie"
    assert all(l.lebenslagen == ("geburt",) for l in kb.leistungen_fuer(["geburt"]))


@pytest.mark.anforderung("ANF-MOD-01")
def test_probe_modul_ist_konsistent(probe_kb):
    assert probe_kb.konsistenz_pruefen() == []
    assert probe_kb.unbenutzte_fakten() == []
    assert probe_kb.fakten["probe.ort_immobilie"].modul == "probe"


@pytest.mark.anforderung("ANF-MOD-01")
@pytest.mark.parametrize(
    "aendern,meldung",
    [
        # Regel greift auf einen Fakt eines anderen Moduls zu (ohne Import)
        (lambda d: d["leistungen.json"]["varianten"][1].update(
            regel={"fakt": "eltern_verheiratet", "op": "==", "wert": True, "text": "x"}), "gehört zum Modul familie"),
        (lambda d: d["leistungen.json"]["leistungen"][0].update(lebenslagen=["gibt_es_nicht"]), "unbekannte Lebenslage"),
        (lambda d: d["leistungen.json"]["leistungen"][0].update(rechtsanspruch=True), "keinen Rechtsanspruch"),
        (lambda d: d["leistungen.json"]["leistungen"][0].update(ortsbezug="probe.erstkauf"), "Typ 'ort'"),
        (lambda d: d["leistungen.json"]["leistungen"][1].update(beantragt_von="nachbar"), "'beantragt_von'"),
        (lambda d: d["leistungen.json"]["leistungen"][1].update(fuer=["oma"]), "unbekannte Rolle oma"),
        (lambda d: d["modul.json"]["lebenslagen"][0].update(einstiegsfragen=["kind_geboren"]), "gehört zum Modul familie"),
        (lambda d: d["modul.json"]["lebenslagen"][0].update(typ="zustand"), "'typ' muss eines von"),
        (lambda d: d["fakten.json"]["fakten"][2].update(grunddaten=True), "'grunddaten' entfällt"),
        (lambda d: d["modul.json"]["fachmodul"].update(id="anders"), "muss in data/fachmodule/anders/"),
        (lambda d: d["leistungen.json"]["varianten"][2]["verfahren"]["fristen"][0].update(bezug="probe.erstkauf"),
         "Frist-Bezug probe.erstkauf"),
        (lambda d: d["leistungen.json"]["leistungen"][0].update(ereignisse=["probe_kauf"]), "heißt jetzt 'lebenslagen'"),
        (lambda d: d["fakten.json"]["fakten"][2].update(id="wohnen.erstkauf"), "Rolle oder das eigene Modul"),
    ],
)
def test_fehler_im_modul_werden_erkannt(tmp_path, aendern, meldung):
    fehler = fehler_beim_laden(tmp_path, aendern)
    assert any(meldung in f for f in fehler), fehler


@pytest.mark.anforderung("ANF-MOD-01")
def test_import_erlaubt_fremden_fakt(tmp_path):
    def aendern(d):
        d["leistungen.json"]["varianten"][1]["regel"] = {"fakt": "eltern_verheiratet", "op": "==", "wert": True, "text": "x"}
        d["modul.json"]["fachmodul"]["importiert_fakten"] = ["eltern_verheiratet"]

    assert Wissensbasis.laden(daten_mit_probe(tmp_path, aendern)).konsistenz_pruefen() == []


@pytest.mark.anforderung("ANF-MOD-01")
def test_fakten_nur_in_kern_oder_fachmodul(tmp_path):
    daten = daten_mit_probe(tmp_path)
    (daten / "laender" / "by" / "fakten.json").write_text(
        json.dumps({"fakten": [{"id": "irgendwo", "typ": "ja_nein", "frage": "?"}]}), encoding="utf-8")
    with pytest.raises(DatenFehler, match="gehören nach data/kern/ oder data/fachmodule"):
        Wissensbasis.laden(daten)


# ------------------------------------------------------------------ Mehrere Lebenslagen
@pytest.mark.anforderung("ANF-MOD-02")
def test_mehrere_lebenslagen_leistung_nur_einmal(probe_kb):
    b = plane(probe_kb, ["probe_kauf", "probe_einkommen"], {"brutto_haushalt_monat": 2000})
    ids = [e.leistung.id for e in b.eintraege]
    assert ids.count("probe_geteilt") == 1
    assert b.eintrag("probe_geteilt").lebenslagen == ["probe_kauf", "probe_einkommen"]
    assert b.eintrag("probe_geteilt").ergebnis is Wert.JA
    # Mit Geburt kombiniert: Leistungen beider Module, jede mit ihrer Lebenslage
    b = plane(probe_kb, ["geburt", "probe_einkommen"])
    assert "elterngeld" in b.ergebnisse() and "probe_geteilt" in b.ergebnisse()
    assert "probe_pflicht" not in b.ergebnisse()
    assert b.eintrag("elterngeld").lebenslagen == ["geburt"]
    assert b.eintrag("probe_geteilt").lebenslagen == ["probe_einkommen"]


@pytest.mark.anforderung("ANF-MOD-02")
def test_unbekannte_lebenslage(kb):
    with pytest.raises(EingabeFehler, match="Unbekannte Lebenslage heirat"):
        planen(kb, Anfrage(fakten={}, plz="80331", lebenslagen=["heirat"]))
    with pytest.raises(EingabeFehler, match="mindestens eine Lebenslage"):
        planen(kb, Anfrage(fakten={}, plz="80331", lebenslagen=[]))


@pytest.mark.anforderung("ANF-MOD-02", "ANF-MOD-07")
def test_einstiegsfragen_nur_der_gewaehlten_lebenslagen(probe_kb):
    b = plane(probe_kb, ["probe_kauf"])
    assert b.fehlend[0] == "probe.kaufdatum"
    assert "kind_geboren" not in b.fehlend and "partner_im_haushalt" not in b.fehlend
    beide = plane(probe_kb, ["geburt", "probe_kauf"])
    assert beide.fehlend[:3] == ["kind_geboren", "partner_im_haushalt", "probe.kaufdatum"]


@pytest.mark.anforderung("ANF-MOD-02")
def test_warnung_nennt_lebenslage_ohne_landesrecherche(probe_kb):
    # Für Hessen gibt es eine Probe-Landesleistung, aber keinen Abdeckungsnachweis für probe_kauf
    warnungen = plane(probe_kb, ["geburt", "probe_kauf"], {"probe.ort_immobilie": "34225"}, plz="34225").warnungen
    assert any("Hessen ist noch nicht erfasst" in w and "Probekauf" in w for w in warnungen)


# ------------------------------------------------------------------ Rollen
@pytest.mark.anforderung("ANF-MOD-03")
def test_rollen_kommen_aus_den_daten(kb):
    assert person_name(kb, "partner") == "Anderer Elternteil"
    assert person_name(kb, None) == "Haushalt"
    assert frage_zu(kb, "partner.beschaeftigt").startswith("Ist der andere Elternteil angestellt")
    assert frage_zu(kb, "mutter.krankenversicherung") == "Wie ist die Mutter (gebärende Person) krankenversichert?"
    assert kb.fakt_definition("oma.beschaeftigt") is None
    assert kb.rollen["partner"].vorbedingung["fakt"] == "partner_im_haushalt"


@pytest.mark.anforderung("ANF-MOD-03")
def test_vorbedingung_der_rolle(plane):
    from conftest import familie

    # Vorbedingung erfüllt: Partner wird geprüft und die Vorbedingung erscheint in der Begründung
    eg = plane(familie()).eintrag("elterngeld")
    assert [p.person for p in eg.personen] == ["mutter", "partner"]
    assert eg.personen[1].schritt.kinder[0].fakt == "partner_im_haushalt"
    # Nicht erfüllt: nur die Mutter
    assert [p.person for p in plane(familie(partner_im_haushalt="nein")).eintrag("elterngeld").personen] == ["mutter"]
    # Fehlt: nur die Mutter, und die Vorbedingung wird erfragt
    b = plane(familie(partner_im_haushalt=None))
    assert [p.person for p in b.eintrag("elterngeld").personen] == ["mutter"]
    assert "partner_im_haushalt" in b.fehlend


# ------------------------------------------------------------------ Ortsbezug
@pytest.mark.anforderung("ANF-MOD-04", "ANF-MOD-06")
def test_ortsbezug_unbekannt(probe_kb):
    b = plane(probe_kb, ["probe_kauf"])
    assert "probe_zuschuss" not in b.ergebnisse()
    # Der Ort wird direkt nach den Einstiegsfragen erfragt
    assert b.fehlend[:2] == ["probe.kaufdatum", "probe.ort_immobilie"]
    assert [(n.leistung.id, [g.name for g in n.laender]) for n in b.nur_andere_laender] == [("probe_zuschuss", ["Hessen"])]


@pytest.mark.anforderung("ANF-MOD-04")
def test_ortsbezug_anderer_ort_als_wohnort(probe_kb):
    # Wohnort München, Immobilie in Baunatal (Hessen): Landesleistung Hessens gilt
    b = plane(probe_kb, ["probe_kauf"], {"probe.ort_immobilie": "34225", "probe.kaufdatum": "2026-09-01"})
    e = b.eintrag("probe_zuschuss")
    assert e.gebiet.name == "Hessen" and e.zustaendigkeit.name == "Probestelle – Hessen"
    assert e.ergebnis is Wert.UNKLAR and "probe.erstkauf" in b.fehlend
    assert b.nur_andere_laender == []
    # Wohnort Baunatal, Immobilie in München: gibt es dort nicht
    b = plane(probe_kb, ["probe_kauf"], {"probe.ort_immobilie": "80331"}, plz="34225")
    assert "probe_zuschuss" not in b.ergebnisse()
    assert [n.leistung.id for n in b.nur_andere_laender] == ["probe_zuschuss"]
    # Gemeindeschlüssel statt PLZ; "weiß nicht" fragt nicht weiter nach
    assert plane(probe_kb, ["probe_kauf"], {"probe.ort_immobilie": "06611000"}).eintrag("probe_zuschuss").gebiet.id == "06"
    assert "probe.ort_immobilie" not in plane(probe_kb, ["probe_kauf"], {"probe.ort_immobilie": "unbekannt"}).fehlend


@pytest.mark.anforderung("ANF-MOD-04")
def test_hierarchie_fuer_ort(kb):
    assert [g.name for g in gebiete.hierarchie_fuer_ort(kb, "34225")] == ["Baunatal", "Landkreis Kassel", "Hessen", "Deutschland"]
    # Mehrdeutige PLZ (Freising, Hallbergmoos, Oberding): gemeinsamer Teil
    assert [g.id for g in gebiete.hierarchie_fuer_ort(kb, "85356")] == ["09", "DE"]
    assert [g.id for g in gebiete.hierarchie_fuer_ort(kb, "80001")] == ["DE"]  # Postfach
    assert [g.id for g in gebiete.hierarchie_fuer_ort(kb, "99999999")] == ["DE"]  # unbekannter Schlüssel


@pytest.mark.anforderung("ANF-MOD-04")
def test_ort_eingabe_wird_geprueft(probe_kb):
    assert fakten_parsen(probe_kb, {"probe.ort_immobilie": " 34225 "}) == {"probe.ort_immobilie": "34225"}
    with pytest.raises(EingabeFehler, match="Postleitzahl"):
        fakten_parsen(probe_kb, {"probe.ort_immobilie": "Kassel"})


# ------------------------------------------------------------------ Förderprogramm, Antragsteller, Fristen
@pytest.mark.anforderung("ANF-MOD-05")
def test_foerderprogramm_und_antragsteller_werden_angezeigt(probe_kb):
    b = plane(probe_kb, ["probe_kauf"], {"probe.ort_immobilie": "34225", "brutto_haushalt_monat": 2000})
    zuschuss, geteilt = b.eintrag("probe_zuschuss"), b.eintrag("probe_geteilt")
    assert not zuschuss.leistung.rechtsanspruch and not geteilt.leistung.rechtsanspruch
    text = bericht_text(b, probe_kb, Farbe(False))
    assert "Förderprogramm ohne Rechtsanspruch" in text
    assert "Kein Rechtsanspruch: Die zuständige Stelle entscheidet nach Ermessen." in text
    assert "Wer beantragt: Den Antrag stellt der Arbeitgeber" in text
    daten = {e["id"]: e for e in bericht_json(b)["leistungen"]}
    assert daten["probe_geteilt"]["beantragt_von"] == "arbeitgeber"
    assert daten["probe_zuschuss"]["art"] == "foerderprogramm"
    web = {e["id"]: e for e in api.bericht(probe_kb, {"plz": "80331", "lebenslagen": ["probe_kauf"],
                                                      "fakten": {"probe.ort_immobilie": "34225"}})["leistungen"]}
    assert web["probe_zuschuss"]["anspruch_hinweis"].startswith("Förderprogramm")
    assert web["probe_geteilt"]["beantragt_hinweis"].startswith("Den Antrag stellt der Arbeitgeber")


@pytest.mark.anforderung("ANF-MOD-08")
def test_frist_relativ_zu_datumsfakt(probe_kb):
    b = plane(probe_kb, ["probe_kauf"], {"probe.kaufdatum": "2026-10-20", "probe.ort_immobilie": "34225"})
    assert b.eintrag("probe_pflicht").fristen[0].datum == date(2026, 11, 3)
    assert b.eintrag("probe_zuschuss").fristen[0].datum == date(2027, 4, 20)
    assert b.eintrag("probe_pflicht").fristen[0].voraussichtlich is False
    ohne = plane(probe_kb, ["probe_kauf"])
    assert ohne.eintrag("probe_pflicht").fristen[0].datum is None


@pytest.mark.anforderung("ANF-MOD-06")
def test_landesleistung_anderer_laender_im_bericht(plane):
    from conftest import familie

    b = plane(familie(), plz="10115")  # Berlin
    andere = {n.leistung.id: [g.kuerzel for g in n.laender] for n in b.nur_andere_laender}
    assert andere == {"bayerisches_familiengeld": ["BY"], "landeserziehungsgeld_sn": ["SN"]}
    assert "landeserziehungsgeld_sn" not in b.ergebnisse()
    # In Bayern ist das Familiengeld ein normaler Eintrag, nicht "nur in anderen Ländern"
    by = plane(familie())
    assert [n.leistung.id for n in by.nur_andere_laender] == ["landeserziehungsgeld_sn"]


# ------------------------------------------------------------------ Fragen priorisieren
def _eintrag(fehlend: list[str], ergebnis: Wert = Wert.UNKLAR, art: str = "antrag", frist: Optional[date] = None):
    return SimpleNamespace(fehlend=fehlend, ergebnis=ergebnis, leistung=SimpleNamespace(art=art), naechste_frist=frist)


@pytest.mark.anforderung("ANF-MOD-07")
def test_fragen_nach_entscheidungskraft():
    eintraege = [
        _eintrag(["a", "b"]),
        _eintrag(["b"]),
        _eintrag(["c"], art="pflicht", frist=date(2026, 11, 1)),  # Pflicht mit naher Frist: Gewicht 4
        _eintrag(["d"], ergebnis=Wert.JA),  # nur noch für eine weitere Person offen: Gewicht 1
        _eintrag(["e"], art="pflicht", frist=date(2026, 11, 1)),
        _eintrag(["e"]),  # e: 4 + 2 = 6
    ]
    # e (6) vor b und c (je 4, Gleichstand: Reihenfolge des Auftretens) vor a (2) vor d (1)
    assert fragen_priorisieren(["start"], eintraege, STICHTAG) == ["start", "e", "b", "c", "a", "d"]
    # Fragen aus "vorab" erscheinen nicht doppelt
    assert fragen_priorisieren(["b"], eintraege, STICHTAG) == ["b", "e", "c", "a", "d"]


@pytest.mark.anforderung("ANF-MOD-07")
def test_fragen_reihenfolge_geburt(plane):
    fehlend = plane({}).fehlend
    assert fehlend[:2] == ["kind_geboren", "partner_im_haushalt"]
    # Krankenversicherung entscheidet mehrere Leistungen und kommt vor dem Einkommen
    assert fehlend.index("mutter.krankenversicherung") < fehlend.index("zve_eltern")


# ------------------------------------------------------------------ Stichwortsuche
@pytest.mark.anforderung("ANF-MOD-09")
def test_stichwortsuche(kb, probe_kb):
    assert [ll.id for ll, _ in lebenslagen_suchen(kb, "Ich bin schwanger, was muss ich beantragen?")] == ["geburt"]
    assert lebenslagen_suchen(kb, "Steuern auf Kapitalerträge") == []
    assert [ll.id for ll, _ in lebenslagen_suchen(kb, "Wir ziehen nach Berlin, muss ich das Auto ummelden?")][0] == "umzug"
    treffer = [ll.id for ll, _ in lebenslagen_suchen(probe_kb, "Wir wollen ein Haus kaufen und haben wenig Geld")]
    assert set(treffer[:2]) == {"probe_kauf", "probe_einkommen"}
    assert [ll.id for ll, _ in lebenslagen_suchen(probe_kb, "Hauskauf")] == ["probe_kauf"]
