"""Bundesweite Abdeckung (Issue #40): Import, Länderdaten, Abdeckungsstatus, Ladezeit."""

import json
import time
from datetime import date
from pathlib import Path

import pytest

from buergerai import gebiete, gebietsimport as gi
from buergerai.cli import main
from buergerai.modell import Abdeckung, Ebene, Zustaendigkeit
from buergerai.planer import landesabdeckung, zustaendigkeit_fuer_ort
from buergerai.wissensbasis import STANDARD_DATENVERZEICHNIS, Wissensbasis
from conftest import familie

GENERIERT = STANDARD_DATENVERZEICHNIS / "generiert" / "gebiete.json"


# ------------------------------------------------------------------ Testdaten
def strassen_csv(pfad: Path, zeilen: list[tuple[str, str, str, str]]) -> Path:
    text = "Name,PostalCode,Locality,RegionalKey,Borough,Suburb\n"
    text += "".join(f'"{n}",{p},{o},{ags},,\n' for n, p, o, ags in zeilen)
    pfad.write_text(text, encoding="utf-8")
    return pfad


def kreise_csv(pfad: Path, zeilen: list[tuple[str, str, str]]) -> Path:
    text = "AGS;type;name;NUTS3\n" + "".join(f"{a};{t};{n};X\n" for a, t, n in zeilen)
    pfad.write_text(text, encoding="utf-8")
    return pfad


def gv100_satz(satzart: str, rs: str, verband: str, name: str, kennzeichen: str = "") -> str:
    """Ein Datensatz im GV100AD-Format (feste Spalten laut Datensatzbeschreibung)."""
    zeile = satzart + "20250331" + rs.ljust(8) + verband.ljust(4) + name.ljust(50) + "".ljust(50) + kennzeichen.ljust(6)
    return zeile.ljust(220)


STRASSEN = [
    ("Hauptstr.", "85354", "Freising", "09178124"),
    ("Bahnhofstr.", "85354", "Freising", "09178124"),
    ("Flughafen", "85356", "Freising", "09178124"),
    ("Nordallee", "85356", "Oberding", "09177133"),
    ("Dorfstr.", "85445", "Oberding", "09177133"),
]


# ------------------------------------------------------------------ Import
@pytest.mark.anforderung("ANF-DAT-08")
def test_import_aus_plz_und_kreisliste(tmp_path):
    plz = gi.plz_lesen(strassen_csv(tmp_path / "s.csv", STRASSEN))
    kreise = gi.kreisliste_lesen(kreise_csv(tmp_path / "k.csv", [
        ("09177", "Landkreis", "Erding"), ("09178", "Landkreis", "Freising"), ("09162", "Kreisfreie Stadt", "München, Landeshauptstadt"),
    ]))
    daten = gi.zusammenfuehren(plz, kreise)
    assert daten.gemeinden["09178124"].plz == {"85354", "85356"}
    assert daten.gemeinden["09177133"].plz == {"85356", "85445"}
    assert set(daten.kreise) == {"09177", "09178"}  # München ohne Gemeinde: weggelassen
    assert any("09162" in h for h in daten.hinweise)
    inhalt = gi.datei_erzeugen(daten, gi.QUELLE_KREISE, "test@abc", "31.12.2018", date(2026, 10, 25))
    assert inhalt["_import"]["importiert_am"] == "2026-10-25"
    assert inhalt["_import"]["quellen"] == {gi.QUELLE_PLZ: "test@abc", gi.QUELLE_KREISE: "31.12.2018"}
    assert inhalt["_import"]["anzahl"] == {"kreise": 2, "gemeinden": 2, "plz": 3}
    kreis = next(g for g in inhalt["gebiete"] if g["id"] == "09178")
    assert kreis == {"id": "09178", "name": "Landkreis Freising", "ebene": "kreis", "parent_id": "09",
                     "art": "Landkreis", "quellen": [gi.QUELLE_KREISE]}
    # Ergebnis ist eine ladbare Wissensbasis-Datei (zusammen mit Bund und Ländern)
    text = gi.als_text(inhalt)
    assert json.loads(text) == inhalt
    gebietszeilen = [z for z in text.splitlines() if z.startswith('    {"id": "09')]
    assert len(gebietszeilen) == len(inhalt["gebiete"])  # ein Gebiet je Zeile


@pytest.mark.anforderung("ANF-DAT-08")
def test_import_ladbar_und_aufloesbar(tmp_path):
    daten_dir = tmp_path / "daten"
    (daten_dir / "bund").mkdir(parents=True)
    (daten_dir / "bund" / "gebiete.json").write_text(
        (STANDARD_DATENVERZEICHNIS / "bund" / "gebiete.json").read_text(encoding="utf-8"), encoding="utf-8")
    plz = gi.plz_lesen(strassen_csv(tmp_path / "s.csv", STRASSEN))
    kreise = gi.kreisliste_lesen(kreise_csv(tmp_path / "k.csv", [("09177", "Landkreis", "Erding"), ("09178", "Landkreis", "Freising")]))
    inhalt = gi.datei_erzeugen(gi.zusammenfuehren(plz, kreise), gi.QUELLE_KREISE, "x", "y")
    (daten_dir / "generiert").mkdir()
    (daten_dir / "generiert" / "gebiete.json").write_text(gi.als_text(inhalt), encoding="utf-8")
    # Ohne Leistungen meldet die Konsistenzprüfung nichts zu Gebieten
    kb = Wissensbasis.laden(daten_dir, pruefen=False)
    assert not [f for f in kb.konsistenz_pruefen() if "Gebiet" in f]
    assert [g.name for g in gebiete.aufloesen(kb, plz="85445")] == ["Oberding", "Landkreis Erding", "Bayern", "Deutschland"]
    with pytest.raises(gebiete.PlzMehrdeutig):
        gebiete.aufloesen(kb, plz="85356")


@pytest.mark.anforderung("ANF-DAT-08")
def test_import_fehler(tmp_path):
    with pytest.raises(gi.ImportFehler, match="Spalten fehlen"):
        gi.plz_lesen(kreise_csv(tmp_path / "falsch.csv", []))
    with pytest.raises(gi.ImportFehler, match="ungültige PLZ"):
        gi.plz_lesen(strassen_csv(tmp_path / "s.csv", [("A", "8535", "X", "09178124")]))
    plz = gi.plz_lesen(strassen_csv(tmp_path / "s2.csv", STRASSEN))
    with pytest.raises(gi.ImportFehler, match="Kreise fehlen.*09177"):
        gi.zusammenfuehren(plz, {"09178": gi.Kreis("09178", "Freising", "Landkreis")})


@pytest.mark.anforderung("ANF-DAT-10")
def test_gv100ad_mit_gemeindeverbaenden(tmp_path):
    saetze = [
        gv100_satz("10", "09", "", "Bayern"),
        gv100_satz("40", "09177", "", "Erding", "44"),
        gv100_satz("40", "09178", "", "Freising", "44"),
        gv100_satz("50", "09177", "5301", "Oberding (VGem)", "51"),
        gv100_satz("60", "09177133", "5301", "Oberding", "63"),
        gv100_satz("60", "09177999", "5301", "Neudorf", "63"),
        gv100_satz("60", "09178124", "0124", "Freising, GKSt", "67"),
    ]
    datei = tmp_path / "GV100AD_310325.txt"
    datei.write_text("\r\n".join(saetze) + "\r\n", encoding="latin-1")
    stand, kreise, gemeinden = gi.gv100ad_lesen(datei)
    assert stand == "2025-03-31"
    assert kreise["09178"].art == "Landkreis" and kreise["09178"].anzeigename == "Landkreis Freising"
    assert gemeinden["09177133"].verband == ("091775301", "Oberding (VGem)")
    assert gemeinden["09178124"].verband is None
    plz = gi.plz_lesen(strassen_csv(tmp_path / "s.csv", STRASSEN))
    daten = gi.zusammenfuehren(plz, kreise, gemeinden)
    assert daten.gemeinden["09177999"].plz == set()  # Gemeinde ohne Straßen bleibt erhalten
    assert daten.gemeinden["09177999"].verband == ("091775301", "Oberding (VGem)")
    assert any("ohne Straßen" in h for h in daten.hinweise)
    eintrag = next(g for g in gi.gebiete_json(daten) if g["id"] == "09177133")
    assert eintrag["verband"] == {"id": "091775301", "name": "Oberding (VGem)"}
    with pytest.raises(gi.ImportFehler, match="fehlen im Gemeindeverzeichnis"):
        gi.zusammenfuehren(plz, kreise, {k: v for k, v in gemeinden.items() if k != "09178124"})


@pytest.mark.anforderung("ANF-DAT-09")
def test_diff_zeigt_aenderungen():
    alt = [
        {"id": "09178", "name": "Landkreis Freising", "parent_id": "09"},
        {"id": "09178124", "name": "Freising", "parent_id": "09178", "plz": ["85354", "85356"]},
        {"id": "16056000", "name": "Eisenach", "parent_id": "16056", "plz": ["99817"]},
    ]
    neu = [
        {"id": "09178", "name": "Landkreis Freising", "parent_id": "09"},
        {"id": "09178124", "name": "Freising, Große Kreisstadt", "parent_id": "09178", "plz": ["85354", "85358"]},
        {"id": "16063105", "name": "Eisenach", "parent_id": "16063", "plz": ["99817"]},
    ]
    d = gi.vergleichen(alt, neu)
    assert d.neu == ["16063105 Eisenach"] and d.entfallen == ["16056000 Eisenach"]
    assert d.umbenannt == [("09178124", "Freising", "Freising, Große Kreisstadt")]
    assert d.plz_neu == [("85358", "09178124")] and d.plz_entfallen == [("85356", "09178124")]
    text = "\n".join(d.zeilen())
    assert "Neue Gebiete: 1" in text and "PLZ entfallen: 1" in text
    assert gi.vergleichen(neu, neu).zeilen() == ["Keine Änderungen an Gebieten und PLZ."]


@pytest.mark.anforderung("ANF-DAT-09")
def test_cli_import_wiederholbar(tmp_path, capsys):
    s = strassen_csv(tmp_path / "s.csv", STRASSEN)
    k = kreise_csv(tmp_path / "k.csv", [("09177", "Landkreis", "Erding"), ("09178", "Landkreis", "Freising")])
    ziel = tmp_path / "gebiete.json"
    argv = ["--keine-farbe", "gebiete-import", "--plz", str(s), "--kreise", str(k), "--ziel", str(ziel)]
    assert main(argv + ["--nur-diff"]) == 0 and not ziel.exists()
    assert main(argv) == 0 and ziel.exists()
    erster = ziel.read_text(encoding="utf-8")
    capsys.readouterr()
    assert main(argv) == 0
    assert "Keine Änderungen" in capsys.readouterr().out
    assert ziel.read_text(encoding="utf-8") == erster
    assert main(["gebiete-import", "--plz", str(tmp_path / "fehlt.csv"), "--kreise", str(k), "--ziel", str(ziel)]) == 1


@pytest.mark.anforderung("ANF-DAT-08")
def test_generierte_datei_hat_herkunft():
    inhalt = json.loads(GENERIERT.read_text(encoding="utf-8"))
    assert inhalt["_import"]["importiert_am"]
    assert set(inhalt["_import"]["quellen"]) >= {gi.QUELLE_PLZ}
    lizenzen = " ".join(q["notiz"] for q in inhalt["quellen"])
    assert "ODbL" in lizenzen and "Statistisches Bundesamt" in lizenzen
    assert all(q["pruefstatus"] == "ungeprueft" for q in inhalt["quellen"])  # Import startet ungeprüft


# ------------------------------------------------------------------ Ladezeit
@pytest.mark.anforderung("ANF-DAT-13")
def test_wissensbasis_laedt_in_unter_2_sekunden():
    start = time.perf_counter()
    kb = Wissensbasis.laden()
    dauer = time.perf_counter() - start
    assert len(kb.gebiete) > 11_000
    assert dauer < 2.0, f"Laden dauerte {dauer:.2f} s"
    start = time.perf_counter()
    for plz in list(kb.plz_index())[:2000]:
        gebiete.gemeinden_fuer_plz(kb, plz)
    assert time.perf_counter() - start < 1.0


# ------------------------------------------------------------------ Länder
ELTERNGELD_STELLE = {
    "24103": "LASG Schleswig-Holstein, Elterngeldstelle Neumünster",
    "20095": "Elterngeldstelle des Bezirksamts",
    "30159": "Elterngeldstelle – Region Hannover",
    "28195": "Elterngeldstelle – Kreisfreie Stadt Bremen",
    "50667": "Elterngeldstelle – Kreisfreie Stadt Köln",
    "34225": "Hessisches Amt für Versorgung und Soziales Kassel",
    "60311": "Hessisches Amt für Versorgung und Soziales Frankfurt am Main",
    "55116": "Elterngeldstelle – Kreisfreie Stadt Mainz",
    "70173": "L-Bank",
    "80331": "ZBFS",
    "66111": "Landesamt für Soziales Saarland",
    "10115": "Jugendamt Ihres Bezirks",
    "14467": "Elterngeldstelle – Kreisfreie Stadt Potsdam",
    "18055": "LAGuS",
    "01067": "Elterngeldstelle – Kreisfreie Stadt Dresden",
    "39104": "Elterngeldstelle – Kreisfreie Stadt Magdeburg",
    "99084": "Elterngeldstelle – Kreisfreie Stadt Erfurt",
}


@pytest.mark.anforderung("ANF-LAND-01")
@pytest.mark.parametrize("plz,stelle", sorted(ELTERNGELD_STELLE.items()))
def test_elterngeld_zeigt_stelle_im_land(plane, plz, stelle):
    e = plane(familie(), plz=plz).eintrag("elterngeld")
    assert stelle in e.zustaendigkeit.name
    assert e.abdeckung is Abdeckung.ERFASST
    assert e.variante.id != "elterngeld_bund"


@pytest.mark.anforderung("ANF-LAND-01")
def test_elterngeld_ohne_gemeinde_nennt_kreis_allgemein(plane):
    e = plane(familie(), plz=None, land="NW").eintrag("elterngeld")
    assert e.zustaendigkeit.name == "Elterngeldstelle – Ihr Landkreis bzw. Ihre kreisfreie Stadt"
    assert "Nordrhein-Westfalen" in e.zustaendigkeit.beschreibung


@pytest.mark.anforderung("ANF-LAND-02")
def test_hessen_und_schleswig_holstein_je_kreis(kb):
    for land, praefix in (("06", "havs_"), ("01", "lasg_sh_")):
        kreise = [g for g in kb.gebiete.values() if g.ebene is Ebene.KREIS and g.parent_id == land]
        for k in kreise:
            varianten = [v for v in kb.varianten_von("elterngeld") if v.gebiet_id == k.id]
            assert len(varianten) == 1, k.name
            assert varianten[0].zustaendigkeit_id.startswith(praefix)
            assert varianten[0].quellen  # geerbt von der Landesvariante


@pytest.mark.anforderung("ANF-LAND-03", "ANF-DAT-11")
def test_landesleistungen_in_allen_laendern_dokumentiert(kb):
    for land in gebiete.laender(kb):
        assert landesabdeckung(kb, land, "geburt") is Abdeckung.ERFASST, land.name
        nachweis = kb.landesabdeckung[(land.id, "geburt")]
        eigene = kb.landesleistungen(land.id, "geburt")
        assert (nachweis.landesleistungen == "erfasst") == bool(eigene), land.name
    assert kb.landesleistungen("09", "geburt") == ["bayerisches_familiengeld"]
    assert kb.landesleistungen("14", "geburt") == ["landeserziehungsgeld_sn"]


@pytest.mark.anforderung("ANF-LAND-03")
def test_landeserziehungsgeld_sachsen(plane):
    b = plane(familie(), plz="01067")
    e = b.eintrag("landeserziehungsgeld_sn")
    assert e.ergebnis.value == "unklar"  # Einkommen und Kita-Platz sind nicht regelbasiert prüfbar
    assert "Kreisfreie Stadt Dresden" in e.zustaendigkeit.name
    assert e.leistung.voraussetzungen == ("elterngeld",)
    assert plane(familie(kind_lebt_im_haushalt="nein"), plz="01067").eintrag("landeserziehungsgeld_sn").ergebnis.value == "nein"
    assert "landeserziehungsgeld_sn" not in plane(familie(), plz="80331").ergebnisse()


@pytest.mark.anforderung("ANF-DAT-11")
def test_konsistenz_landesabdeckung(kb):
    from buergerai.modell import Landesabdeckung

    test_kb = Wissensbasis(**{k: dict(getattr(kb, k)) for k in
                              ("gebiete", "leistungen", "varianten", "quellen", "zustaendigkeiten", "fakten", "landesabdeckung")})
    test_kb.landesabdeckung[("11", "geburt")] = Landesabdeckung("11", "geburt", "erfasst", date(2026, 1, 1), ("bmfsfj_elterngeldstellen",))
    test_kb.landesabdeckung[("09", "geburt")] = Landesabdeckung("09", "geburt", "keine", date(2026, 1, 1), ())
    test_kb.landesabdeckung[("09178", "geburt")] = Landesabdeckung("09178", "geburt", "vielleicht", date(2026, 1, 1), ("x",))
    fehler = "\n".join(test_kb.konsistenz_pruefen())
    assert "Abdeckung 11/geburt: 'erfasst', aber keine Landesleistung" in fehler
    assert "Abdeckung 09/geburt: 'keine', aber Landesleistungen vorhanden: bayerisches_familiengeld" in fehler
    assert "Abdeckung 09/geburt: braucht mindestens eine Quelle" in fehler
    assert "Abdeckung 09178/geburt: Gebiet muss ein Land sein" in fehler


@pytest.mark.anforderung("ANF-LAND-04")
def test_szenario_je_land(kb):
    from buergerai import szenarien

    laender = set()
    for s in szenarien.alle(kb):
        kette = gebiete.aufloesen(kb, s.anfrage.plz, s.anfrage.gemeinde, s.anfrage.land)
        laender.update(g.kuerzel for g in kette if g.ebene is Ebene.LAND)
    assert laender == {l.kuerzel for l in gebiete.laender(kb)}


# ------------------------------------------------------------------ Kreise / Platzhalter
@pytest.mark.anforderung("ANF-DAT-12")
def test_platzhalter_in_zustaendigkeiten(kb):
    z = Zustaendigkeit("x", "Jugendamt – {kreis}", "Für {gemeinde} in {land}")
    voll = zustaendigkeit_fuer_ort(z, gebiete.aufloesen(kb, plz="85354"))
    assert voll.name == "Jugendamt – Landkreis Freising"
    assert voll.beschreibung == "Für Freising in Bayern"
    nur_land = zustaendigkeit_fuer_ort(z, gebiete.aufloesen(kb, land="BY"))
    assert nur_land.name == "Jugendamt – Ihr Landkreis bzw. Ihre kreisfreie Stadt"
    test_kb = Wissensbasis(**{k: dict(getattr(kb, k)) for k in ("gebiete", "quellen", "zustaendigkeiten")})
    test_kb.zustaendigkeiten["kaputt"] = Zustaendigkeit("kaputt", "Amt {ort}", "{kreis")
    fehler = "\n".join(test_kb.konsistenz_pruefen())
    assert "unbekannter Platzhalter {ort}" in fehler and "ungültiger Platzhalter" in fehler


@pytest.mark.anforderung("ANF-KRS-01")
def test_jugendamt_mit_kreisname_und_erfasste_kreise(plane):
    unverheiratet = familie(eltern_verheiratet="nein")
    koeln = plane(unverheiratet, plz="50667").eintrag("vaterschaftsanerkennung")
    assert koeln.zustaendigkeit.name == "Jugendamt – Kreisfreie Stadt Köln"
    assert koeln.abdeckung is Abdeckung.ALLGEMEIN
    muenchen = plane(unverheiratet, plz="80331")
    for lid in ("vaterschaftsanerkennung", "sorgeerklaerung"):
        assert muenchen.eintrag(lid).zustaendigkeit.id == "stadtjugendamt_muenchen"
        assert muenchen.eintrag(lid).abdeckung is Abdeckung.ERFASST
    freising = plane(unverheiratet, plz="85354")
    assert freising.eintrag("sorgeerklaerung").zustaendigkeit.id == "jugendamt_lk_freising"
    # Nachbarlandkreis Erding: nur allgemein
    assert plane(unverheiratet, plz="85445").eintrag("sorgeerklaerung").abdeckung is Abdeckung.ALLGEMEIN


def test_cli_abdeckung(capsys):
    assert main(["--keine-farbe", "abdeckung"]) == 0
    out = capsys.readouterr().out
    assert "SN Sachsen" in out and "Landesleistungen: Sächsisches Landeserziehungsgeld" in out
    assert "BY Bayern" in out and "Landesleistungen: Bayerisches Familiengeld" in out
    assert "nicht recherchiert" not in out
    # Landesleistungen anderer Länder erscheinen nicht
    berlin = out[out.index("BE Berlin"):out.index("BB Brandenburg")]
    assert "Familiengeld" not in berlin and "Landeserziehungsgeld" not in berlin
