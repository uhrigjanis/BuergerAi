"""Tests der Web-Oberfläche: API-Logik direkt und der HTTP-Server über einen echten Port."""

import json
from pathlib import Path
import threading
import urllib.error
import urllib.request

import pytest

from buergerai import __version__
from buergerai import szenarien as szenarien_mod
from buergerai.modell import Ebene, Gebiet
from buergerai.planer import planen
from buergerai.web import api
from buergerai.web.server import erstellen
from buergerai.wissensbasis import Wissensbasis

STICHTAG = "2026-10-24"


def anfrage(**fakten):
    return {"plz": "80331", "stichtag": STICHTAG, "fakten": fakten}


# ------------------------------------------------------------------ API-Logik
@pytest.mark.anforderung("ANF-WEB-02")
def test_ort_gemeinde(kb):
    antwort = api.ort(kb, {"plz": "85354"})
    assert antwort["status"] == "ok"
    assert [g["name"] for g in antwort["hierarchie"]][0] == "Freising"


@pytest.mark.anforderung("ANF-WEB-02")
def test_ort_unbekannt_bietet_laender(kb):
    with pytest.raises(api.ApiFehler) as info:
        api.ort(kb, {"plz": "80001"})  # Postfach-PLZ
    assert info.value.status == 409
    daten = info.value.json()
    assert daten["status"] == "unbekannt"
    assert {"kuerzel": "BE", "name": "Berlin", "abdeckung": "erfasst"} in daten["laender"]
    assert api.ort(kb, {"plz": "80001", "land": "BY"})["text"] == "Bayern → Deutschland"


@pytest.mark.anforderung("ANF-WEB-02")
def test_ort_mehrdeutig_bietet_gemeinden(kb):
    test_kb = Wissensbasis(gebiete=dict(kb.gebiete))
    test_kb.gebiete["09999998"] = Gebiet("09999998", "Nachbarort", Ebene.GEMEINDE, "09178", plz=("85354",))
    with pytest.raises(api.ApiFehler) as info:
        api.ort(test_kb, {"plz": "85354"})
    assert info.value.json()["status"] == "mehrdeutig"
    assert {g["name"] for g in info.value.json()["gemeinden"]} == {"Freising", "Nachbarort"}
    assert {g["kreis"] for g in info.value.json()["gemeinden"]} == {"Landkreis Freising"}
    assert api.ort(test_kb, {"plz": "85354", "gemeinde": "09999998"})["hierarchie"][0]["name"] == "Nachbarort"


@pytest.mark.anforderung("ANF-WEB-02", "ANF-WEB-07")
def test_ort_ungueltig(kb):
    with pytest.raises(api.ApiFehler) as info:
        api.ort(kb, {"plz": "1234"})
    assert info.value.status == 400 and "fünf Ziffern" in info.value.meldung


@pytest.mark.anforderung("ANF-WEB-03")
def test_fragen_passend_zum_typ(kb):
    b = api.bericht(kb, anfrage())
    fragen = {f["id"]: f for f in b["fragen"]}
    assert b["fragen"][0]["id"] == "kind_geboren"
    assert fragen["kind_geboren"]["typ"] == "ja_nein"
    # nur fragen, was nötig ist: Geburtsdatum erst nach der Antwort auf "geboren?"
    assert "geburtsdatum" not in fragen and "errechneter_termin" not in fragen
    b = api.bericht(kb, anfrage(kind_geboren=False))
    assert b["fragen"][0]["id"] == "errechneter_termin" and b["fragen"][0]["typ"] == "datum"


@pytest.mark.anforderung("ANF-WEB-03")
def test_auswahlfrage_mit_optionen_und_person(kb):
    b = api.bericht(kb, anfrage(kind_geboren=False, errechneter_termin="2026-12-15", partner_im_haushalt=True))
    alle = {f["id"]: f for f in b["fragen"]}
    kv = alle["mutter.krankenversicherung"]
    assert kv["typ"] == "auswahl" and kv["person"] == "mutter" and kv["person_name"] == "Mutter"
    assert {"wert": "privat", "text": "privat"} in kv["optionen"]
    assert "die Mutter" in kv["frage"] and "{wer}" not in kv["frage"]


@pytest.mark.anforderung("ANF-WEB-03", "ANF-ENG-04")
def test_weiss_nicht_wird_nicht_erneut_gefragt(kb):
    b = api.bericht(kb, anfrage(kind_geboren=False, errechneter_termin="2026-12-15", partner_im_haushalt="unbekannt"))
    assert "partner_im_haushalt" not in [f["id"] for f in b["fragen"]]
    angabe = next(a for a in b["angaben"] if a["id"] == "partner_im_haushalt")
    assert angabe["wert"] == "unbekannt"


@pytest.mark.anforderung("ANF-WEB-04")
def test_angaben_aendern_und_inaktiv(kb):
    vorher = api.bericht(kb, anfrage(kind_geboren=False, errechneter_termin="2026-12-15"))
    nachher = api.bericht(kb, anfrage(kind_geboren=True, errechneter_termin="2026-12-15", geburtsdatum="2026-10-20"))
    assert vorher["kind"].startswith("errechneter Termin")
    assert nachher["kind"] == "geboren am 20.10.2026"
    termin = next(a for a in nachher["angaben"] if a["id"] == "errechneter_termin")
    assert termin["aktiv"] is False  # gilt nach der Geburt nicht mehr


@pytest.mark.anforderung("ANF-WEB-04")
def test_auswahl_wird_lesbar_angezeigt(kb):
    b = api.bericht(kb, anfrage(**{"mutter.krankenversicherung": "gesetzlich_familienversichert"}))
    angabe = next(a for a in b["angaben"] if a["id"] == "mutter.krankenversicherung")
    assert angabe["anzeige"] == "gesetzlich, familienversichert"


@pytest.mark.anforderung("ANF-WEB-05")
def test_checkliste_mit_fristen_unterlagen_anleitung(kb):
    s = api.szenario(kb, "muenchen_verheiratet_angestellt")
    b = api.bericht(kb, s)
    ga = next(l for l in b["leistungen"] if l["id"] == "geburtsanzeige")
    assert ga["ergebnis"] == "ja"
    assert ga["zustaendigkeit"]["name"].startswith("Standesamt München")
    assert ga["verfahren"]["unterlagen"] and ga["verfahren"]["schritte"]
    assert ga["fristen"][0]["datum"] and ga["fristen"][0]["art_text"] == "spätestens"
    assert ga["quellen"] and all(q["pruefstatus"] for q in ga["quellen"])
    eg = next(l for l in b["leistungen"] if l["id"] == "elterngeld")
    assert [p["name"] for p in eg["personen"]] == ["Mutter", "Anderer Elternteil"]
    assert all(g["ergebnis"] == "ja" and g["text"] for p in eg["personen"] for g in p["gruende"])
    # Zeitplan sortiert und ohne Leistungen mit Ergebnis "nein"
    daten = [t["datum"] for t in b["zeitplan"]]
    assert daten == sorted(daten) and daten
    nein = {l["id"] for l in b["leistungen"] if l["ergebnis"] == "nein"}
    assert not nein & {t["leistung_id"] for t in b["zeitplan"]}
    # Reihenfolge wie im Terminal: Voraussetzungen zuerst
    ids = [l["id"] for l in b["leistungen"]]
    assert ids.index("geburtsanzeige") < ids.index("elterngeld")


@pytest.mark.anforderung("ANF-WEB-05")
def test_begruendung_zeigt_fehlende_angabe(kb):
    b = api.bericht(kb, anfrage())
    eg = next(l for l in b["leistungen"] if l["id"] == "elterngeld")
    gruende = [g for p in eg["personen"] for g in p["gruende"]]
    assert any("fehlt" in g for g in gruende)


@pytest.mark.anforderung("ANF-WEB-06")
def test_kalender(kb):
    ics = api.kalender(kb, api.szenario(kb, "muenchen_verheiratet_angestellt"))
    assert ics.startswith("BEGIN:VCALENDAR\r\n") and ics.endswith("END:VCALENDAR\r\n")
    assert ics.count("BEGIN:VEVENT") == len(api.bericht(kb, api.szenario(kb, "muenchen_verheiratet_angestellt"))["zeitplan"])
    assert "SUMMARY:Geburt anzeigen" in ics
    assert all(len(z.encode("utf-8")) <= 75 for z in ics.split("\r\n"))


@pytest.mark.anforderung("ANF-WEB-07")
@pytest.mark.parametrize("daten, teil", [
    ([], "JSON-Objekt"),
    ({"plz": "80331", "fakten": {"gibtsnicht": "ja"}}, "Unbekannter Fakt"),
    ({"plz": "80331", "fakten": {"kind_geboren": "vielleicht"}}, "ja"),
    ({"plz": "80331", "fakten": {"wohnsitz_land": "BY"}}, "automatisch"),
    ({"plz": "80331", "fakten": {"kind_geboren": {"x": 1}}}, "Angaben"),
    ({"plz": "80331", "stichtag": "24.10.2026"}, "Stichtag"),
    ({"plz": "80331", "stichtag": "20261024"}, "Stichtag"),
    ({"plz": "80331", "stichtag": "2026-W43"}, "Stichtag"),
    ({"plz": "80331", "stichtag": "2026-W43-3"}, "Stichtag"),
    ({"plz": "80331", "stichtag": "2026-02-30"}, "Stichtag"),
    ({"plz": 80331}, "Ungültiger Wert"),
    ({"plz": "80331", "lebenslagen": ["mondreise"]}, "Unbekannte Lebenslage"),
    ({"plz": "80331", "lebenslagen": "geburt"}, "Liste"),
    ({"plz": "80331", "lebenslagen": [1]}, "Liste"),
])
def test_ungueltige_eingaben(kb, daten, teil):
    with pytest.raises(api.ApiFehler) as info:
        api.bericht(kb, daten)
    assert info.value.status == 400 and teil in info.value.meldung


@pytest.mark.anforderung("ANF-WEB-08")
def test_gleiche_ergebnisse_wie_terminal(kb):
    for s in szenarien_mod.alle(kb):
        web = {l["id"]: l["ergebnis"] for l in api.bericht(kb, api.szenario(kb, s.id))["leistungen"]}
        assert web == planen(kb, s.anfrage).ergebnisse(), s.id
        for leistung, erwartet in s.erwartet.items():
            assert web.get(leistung) == erwartet, (s.id, leistung)


@pytest.mark.anforderung("ANF-WEB-09")
def test_szenario_format_rundreise(kb, tmp_path):
    """Im Browser gespeicherte Angaben lassen sich im Terminal laden und umgekehrt."""
    daten = api.szenario(kb, "freising_unverheiratet_privat")
    datei = tmp_path / "ich.json"
    datei.write_text(json.dumps({"name": "x", **daten}), encoding="utf-8")
    geladen = szenarien_mod.laden(kb, datei)
    assert planen(kb, geladen.anfrage).ergebnisse() == {
        l["id"]: l["ergebnis"] for l in api.bericht(kb, daten)["leistungen"]
    }


@pytest.mark.anforderung("ANF-MOD-02", "ANF-WEB-09")
def test_lebenslagen_in_der_api(kb):
    meta = api.meta(kb)
    assert [l["id"] for l in meta["lebenslagen"]] == ["ausbildung_studium", "behinderung", "geburt", "geringes_einkommen", "wohneigentum", "heirat", "jobverlust", "pflege", "schule", "selbststaendig", "todesfall", "umzug"]
    assert meta["lebenslagen"][2]["modul"] == "Familie und Kinder"
    # ohne Angabe: Geburt; mit Angabe: dasselbe Ergebnis
    ohne = api.bericht(kb, anfrage())
    mit = api.bericht(kb, {**anfrage(), "lebenslagen": ["geburt", "geburt"]})
    assert ohne["lebenslagen"] == mit["lebenslagen"] == [{"id": "geburt", "name": "Geburt"}]
    assert [l["id"] for l in ohne["leistungen"]] == [l["id"] for l in mit["leistungen"]]
    assert all(l["lebenslagen"] == ["geburt"] for l in ohne["leistungen"])
    assert {f["gruppe"] for f in ohne["fragen"]} <= {"Allgemein", "Familie und Kinder"}
    # Berlin: Landesleistungen anderer Länder werden genannt
    berlin = api.bericht(kb, {"plz": "10115", "stichtag": STICHTAG, "fakten": {}})
    assert {"name": "Sächsisches Landeserziehungsgeld", "laender": ["Sachsen"]} in berlin["nur_andere_laender"]
    # Szenarien und gespeicherte Angaben tragen die Lebenslagen
    assert api.szenario(kb, "nur_plz")["lebenslagen"] == ["geburt"]


@pytest.mark.anforderung("ANF-WEB-09", "ANF-WEB-07")
def test_szenario_unbekannt(kb):
    for name in ("gibtsnicht", "../pyproject", "a/b", "nur_plä", "nur_plz\u0430", "NUR_PLZ"):
        with pytest.raises(api.ApiFehler) as info:
            api.szenario(kb, name)
        assert info.value.status == 404


# ------------------------------------------------------------------ HTTP-Server
@pytest.fixture(scope="module")
def basis():
    server = erstellen(Wissensbasis.laden(), "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def http(url, daten=None, typ="application/json"):
    body = None if daten is None else (daten if isinstance(daten, bytes) else json.dumps(daten).encode())
    req = urllib.request.Request(url, data=body, headers={"Content-Type": typ} if body is not None else {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


@pytest.mark.anforderung("ANF-WEB-01")
def test_server_liefert_oberflaeche(basis):
    status, kopf, inhalt = http(basis + "/")
    assert status == 200 and kopf["Content-Type"].startswith("text/html")
    assert "Content-Security-Policy" in kopf
    assert b"app.js" in inhalt and "BürgerAI" in inhalt.decode()
    for datei in ("/app.js", "/style.css"):
        assert http(basis + datei)[0] == 200


@pytest.mark.anforderung("ANF-WEB-01")
def test_server_api(basis):
    status, _, inhalt = http(basis + "/api/meta")
    meta = json.loads(inhalt)
    assert status == 200 and any(s["id"] == "nur_plz" for s in meta["szenarien"])
    status, _, inhalt = http(basis + "/api/bericht", anfrage())
    assert status == 200 and json.loads(inhalt)["fragen"]
    status, kopf, inhalt = http(basis + "/api/kalender", api.szenario(Wissensbasis.laden(), "nur_plz"))
    assert status == 200 and kopf["Content-Type"].startswith("text/calendar")
    status, _, inhalt = http(basis + "/api/ort", {"plz": "80001"})
    assert status == 409 and json.loads(inhalt)["status"] == "unbekannt"


@pytest.mark.anforderung("ANF-WEB-07")
def test_server_lehnt_ab(basis):
    assert http(basis + "/../pyproject.toml")[0] == 404
    assert http(basis + "/static/../api.py")[0] == 404
    assert http(basis + "/api/unbekannt", {})[0] == 404
    assert http(basis + "/api/bericht", b"kein json")[0] == 400
    assert http(basis + "/api/bericht", {"plz": "80331"}, typ="text/plain")[0] == 415
    assert http(basis + "/api/bericht", b"x" * (70 * 1024))[0] == 413
    status, _, inhalt = http(basis + "/api/bericht", {"plz": "80331", "fakten": {"x": 1}})
    assert status == 400 and "Unbekannter Fakt" in json.loads(inhalt)["fehler"]


# ------------------------------------------------------------------ Oberfläche (statisch geprüft)
STATIC = Path(__file__).resolve().parents[1] / "src" / "buergerai" / "web" / "static"


@pytest.mark.anforderung("ANF-WEB-01")
def test_oberflaeche_version_passt_zum_server():
    """Veraltete Dateien im Browser fallen auf: Version in app.js und index.html = Paketversion."""
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert f'const VERSION = "{__version__}";' in js
    assert f'app.js?v={__version__}' in html and f'style.css?v={__version__}' in html


@pytest.mark.anforderung("ANF-WEB-03")
def test_inhalte_nur_ueber_null_sicheren_helfer():
    """replaceChildren zeigt null als Text "null" an; nur der Helfer fuellen() darf es aufrufen."""
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    code = [z for z in js.splitlines() if not z.strip().startswith("//")]
    aufrufe = [z.strip() for z in code if "replaceChildren(" in z]
    assert aufrufe == ["ziel.replaceChildren(...kinder.flat(Infinity).filter((k) => k !== null && k !== undefined && k !== false));"]


@pytest.mark.anforderung("ANF-WEB-10")
def test_lebenslagen_waehlen_und_aendern(kb):
    """Die Oberfläche schickt die gewählten Lebenslagen mit; beim Wechsel bleiben alle Angaben erhalten."""
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert 'id="lebenslagen-wahl"' in html and 'id="lebenslagen-wahl-arbeit"' in html
    assert "daten.lebenslagen = zustand.lebenslagen" in js and "Bitte mindestens eine Lebenslage wählen." in js
    fakten = {"kind_geboren": False, "errechneter_termin": "2026-12-15", "umzug.hund": True}
    nur_geburt = api.bericht(kb, {"plz": "80331", "stichtag": STICHTAG, "fakten": fakten})
    beide = api.bericht(kb, {"plz": "80331", "stichtag": STICHTAG, "fakten": fakten, "lebenslagen": ["geburt", "umzug"]})
    assert {a["id"] for a in nur_geburt["angaben"]} == {a["id"] for a in beide["angaben"]} == set(fakten)
    assert "hundesteuer_anmelden" not in {l["id"] for l in nur_geburt["leistungen"]}
    assert "hundesteuer_anmelden" in {l["id"] for l in beide["leistungen"]}
    assert beide["fragen"][0]["id"] == "partner_im_haushalt"  # Einstiegsfragen beider Lebenslagen zuerst
    assert [f["id"] for f in beide["fragen"]][1:3] == ["umzug.einzugsdatum", "umzug.ort_alt"]
    assert next(f for f in beide["fragen"] if f["id"] == "umzug.ort_alt")["typ"] == "ort"
