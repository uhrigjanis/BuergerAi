"""Abnahme-Befehl und Link-Prüfung (#62)."""

from __future__ import annotations

import http.server
import json
import shutil
import threading
import urllib.request
from datetime import date
from pathlib import Path

import pytest

from buergerai import gebietsimport as gi
from buergerai import linkpruefung as lp
from buergerai import quellenpruefung as qp
from buergerai import quelltext as qt
from buergerai.cli import main
from buergerai.modell import Pruefstatus
from buergerai.wissensbasis import STANDARD_DATENVERZEICHNIS, Wissensbasis

AM = date(2026, 10, 29)

PROTOKOLL_OK = """# Prüfprotokoll: {id}

- Quelle: Test
- Geprüft von: Claude (Recherche) · Abnahme: <Name, Datum>

## Verwendungen in der Wissensbasis (2)

| # | Verwendung in der Wissensbasis | Fundstelle | Wortlaut der Quelle (Zitat, Absatz) | Ergebnis |
|---|---|---|---|---|
| 1 | a | `x` `y` | „…“ | {e1} |
| 2 | b | `x` `y` | „…“ | {e2} |

## Abweichungen und Folgeaktionen

- …
"""


@pytest.fixture
def umgebung(tmp_path):
    """Kopie von Daten und Protokollen; gibt (Datenverzeichnis, Protokollverzeichnis) zurück."""
    daten = tmp_path / "data"
    shutil.copytree(STANDARD_DATENVERZEICHNIS, daten)
    protokolle = tmp_path / "pruefprotokolle"
    shutil.copytree(qp.PROTOKOLL_VERZEICHNIS, protokolle)
    return daten, protokolle


def protokoll(protokolle: Path, qid: str, e1: str = "✅", e2: str = "✅") -> None:
    (protokolle / f"{qid}.md").write_text(PROTOKOLL_OK.format(id=qid, e1=e1, e2=e2), encoding="utf-8")


def notiz_verlinken(daten: Path, datei: str, qid: str) -> None:
    """Hängt den Protokoll-Link an die Notiz, ohne die Formatierung der Datei zu ändern."""
    pfad = daten / datei
    inhalt = json.loads(pfad.read_text(encoding="utf-8"))
    alt = next(q for q in inhalt["quellen"] if q["id"] == qid)["notiz"]
    text = pfad.read_text(encoding="utf-8")
    alt_json = json.dumps(alt, ensure_ascii=False)
    assert alt_json in text
    pfad.write_text(text.replace(alt_json, json.dumps(alt + f" docs/pruefprotokolle/{qid}.md", ensure_ascii=False)),
                    encoding="utf-8")


def geaenderte_zeilen(vorher: str, nachher: str) -> list[tuple[str, str]]:
    a, b = vorher.splitlines(), nachher.splitlines()
    assert len(a) == len(b), "Zeilenzahl darf sich nicht ändern"
    return [(x, y) for x, y in zip(a, b) if x != y]


@pytest.mark.anforderung("ANF-QS-04")
def test_abnahme_setzt_nur_die_prueffelder(umgebung):
    daten, protokolle = umgebung
    datei = daten / "laender" / "by" / "geburt.json"
    vorher = datei.read_text(encoding="utf-8")
    kb = Wissensbasis.laden(daten)

    assert qp.abnehmen(kb, "bayfamgg_9a", "Janis Uhrig", AM, protokolle=protokolle) == datei
    diff = geaenderte_zeilen(vorher, datei.read_text(encoding="utf-8"))
    assert [n.strip() for _, n in diff] == [
        '"pruefstatus": "verifiziert",', '"geprueft_am": "2026-10-29",', '"geprueft_von": "Janis Uhrig",']

    q = Wissensbasis.laden(daten).quellen["bayfamgg_9a"]
    assert (q.pruefstatus, q.geprueft_am, q.geprueft_von) == (Pruefstatus.VERIFIZIERT, AM, "Janis Uhrig")
    text = (protokolle / "bayfamgg_9a.md").read_text(encoding="utf-8")
    assert "Abnahme: Janis Uhrig, 29.10.2026" in text and "<Name, Datum>" not in text


@pytest.mark.anforderung("ANF-QS-04")
def test_abnahme_in_handformatierter_und_generierter_datei(umgebung):
    daten, protokolle = umgebung
    faelle = [("kommunen/09162000/geburt.json", "muenchen_geburtsurkunde"),
              ("generiert/gebiete.json", "destatis_kreise")]
    for datei, qid in faelle:
        notiz_verlinken(daten, datei, qid)
        protokoll(protokolle, qid)
        vorher = (daten / datei).read_text(encoding="utf-8")
        kb = Wissensbasis.laden(daten)
        qp.abnehmen(kb, qid, "Janis Uhrig", AM, protokolle=protokolle)
        nachher = (daten / datei).read_text(encoding="utf-8")
        diff = geaenderte_zeilen(vorher, nachher) if vorher.count("\n") == nachher.count("\n") else None
        # ungeprüfte Quellen haben noch kein geprueft_am: dann kommen genau zwei Zeilen hinzu
        if diff is None:
            assert nachher.count("\n") == vorher.count("\n") + 2
        assert Wissensbasis.laden(daten).quellen[qid].pruefstatus is Pruefstatus.VERIFIZIERT
        # Der Rest der Datei bleibt inhaltlich gleich
        a, b = json.loads(vorher), json.loads(nachher)
        a["quellen"] = [q for q in a["quellen"] if q["id"] != qid]
        b["quellen"] = [q for q in b["quellen"] if q["id"] != qid]
        assert a == b


@pytest.mark.anforderung("ANF-QS-02", "ANF-QS-04")
@pytest.mark.parametrize(
    "qid,von,vorbereiten,meldung",
    [
        ("bayfamgg_9a", "Claude (Websuche)", None, "nur ein Mensch"),
        ("bayfamgg_9a", "  ", None, "Name fehlt"),
        ("fim_by_elterngeld", "Janis Uhrig", None, "Kein verlinktes Prüfprotokoll"),
        ("fim_by_elterngeld", "Janis Uhrig", "nur_datei", "Kein verlinktes Prüfprotokoll"),
        ("bayfamgg_9a", "Janis Uhrig", ("❌", "✅"), "Abweichung"),
        ("bayfamgg_9a", "Janis Uhrig", ("✅", ""), "ohne Ergebnis"),
        ("bayfamgg_3", "Janis Uhrig", None, "--trotz-hinweisen"),
    ],
)
def test_abnahme_verweigert(umgebung, qid, von, vorbereiten, meldung):
    daten, protokolle = umgebung
    if vorbereiten == "nur_datei":
        protokoll(protokolle, qid)  # Datei da, aber nicht in der Notiz verlinkt
    elif vorbereiten:
        protokoll(protokolle, qid, *vorbereiten)
    datei = daten / "laender" / "by" / "geburt.json"
    vorher = datei.read_text(encoding="utf-8")
    with pytest.raises(qp.AbnahmeFehler, match=meldung):
        qp.abnehmen(Wissensbasis.laden(daten), qid, von, AM, protokolle=protokolle)
    assert datei.read_text(encoding="utf-8") == vorher


@pytest.mark.anforderung("ANF-QS-04")
def test_abnahme_trotz_hinweisen_und_zuruecksetzen(umgebung):
    daten, protokolle = umgebung
    qp.abnehmen(Wissensbasis.laden(daten), "bayfamgg_3", "Janis Uhrig", AM, trotz_hinweisen=True,
                protokolle=protokolle)
    kb = Wissensbasis.laden(daten)
    assert kb.quellen["bayfamgg_3"].pruefstatus is Pruefstatus.VERIFIZIERT

    qp.zuruecksetzen(kb, "bayfamgg_3", date(2026, 11, 2), protokolle=protokolle)
    q = Wissensbasis.laden(daten).quellen["bayfamgg_3"]
    assert q.pruefstatus is Pruefstatus.TEILWEISE
    text = (protokolle / "bayfamgg_3.md").read_text(encoding="utf-8")
    assert "Abnahme: zurückgenommen am 02.11.2026 (vorher Janis Uhrig, 29.10.2026)" in text
    with pytest.raises(qp.AbnahmeFehler, match="nicht verifiziert"):
        qp.zuruecksetzen(Wissensbasis.laden(daten), "bayfamgg_3", AM, protokolle=protokolle)


@pytest.mark.anforderung("ANF-QS-04")
def test_protokoll_lesen():
    stand = qp.protokoll_lesen(PROTOKOLL_OK.format(id="x", e1="✅ passt", e2="⚠️ unklar"))
    assert stand == qp.Protokollstand(zeilen=2, ohne_ergebnis=0, abweichungen=0, hinweise=1)
    assert qp.protokoll_lesen(PROTOKOLL_OK.format(id="x", e1="", e2="❌")).ohne_ergebnis == 1


@pytest.mark.anforderung("ANF-QS-04")
def test_cli_abnahme(umgebung, capsys, monkeypatch):
    daten, protokolle = umgebung
    monkeypatch.setattr(qp, "PROTOKOLL_VERZEICHNIS", protokolle)
    assert main(["--keine-farbe", "--daten", str(daten), "quellen", "--abnehmen", "bayfamgg_9a"]) == 2
    assert "--von" in capsys.readouterr().err
    assert main(["--keine-farbe", "--daten", str(daten), "quellen", "--abnehmen", "bayfamgg_3",
                 "--von", "Janis Uhrig"]) == 1
    assert "Abnahme nicht möglich" in capsys.readouterr().err
    # Ohne Netz: der Fingerabdruck (#64) wird übersprungen, die Abnahme gelingt trotzdem
    monkeypatch.setattr(qt, "http_abruf", lambda url: (_ for _ in ()).throw(qt.AbrufFehler("kein Netz", netz=True)))
    code = main(["--keine-farbe", "--daten", str(daten), "quellen", "--abnehmen", "bayfamgg_9a",
                 "--von", "Janis Uhrig", "--am", "29.10.2026", "--ohne-cache"])
    out = capsys.readouterr().out
    assert code == 0 and "verifiziert von Janis Uhrig am 29.10.2026" in out
    assert main(["--keine-farbe", "--daten", str(daten), "quellen", "--zuruecksetzen", "bayfamgg_9a"]) == 0


@pytest.mark.anforderung("ANF-QS-04")
def test_gebietsimport_behaelt_abnahme_nur_fuer_gleiche_version():
    neu = gi.quellen_json(gi.QUELLE_KREISE, "plz@neu", "31.12.2018")
    alt = gi.quellen_json(gi.QUELLE_KREISE, "plz@alt", "31.12.2018")
    for q in alt:
        q.update(pruefstatus="verifiziert", geprueft_am="2026-10-29", geprueft_von="Janis Uhrig",
                 notiz="geprüft, docs/pruefprotokolle/x.md")
    hinweise = gi.pruefung_uebernehmen(neu, alt)
    kreise = next(q for q in neu if q["id"] == gi.QUELLE_KREISE)
    plz = next(q for q in neu if q["id"] == gi.QUELLE_PLZ)
    assert kreise["pruefstatus"] == "verifiziert" and kreise["geprueft_von"] == "Janis Uhrig"
    assert plz["pruefstatus"] == "ungeprueft" and "geprueft_von" not in plz, "neue Datenversion"
    assert len(hinweise) == 1 and gi.QUELLE_PLZ in hinweise[0]


# ------------------------------------------------------------- Link-Prüfung
class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        port = self.server.server_address[1]
        ziele = {"/um": f"http://127.0.0.1:{port}/ok", "/fremd": f"http://localhost:{port}/ok"}
        if self.path == "/ok":
            self.send_response(200)
        elif self.path in ziele:
            self.send_response(302)
            self.send_header("Location", ziele[self.path])
        else:
            self.send_response(404)
        self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_address[1]}"
    s.shutdown()


@pytest.mark.anforderung("ANF-QS-05")
def test_linkpruefung(server):
    ohne_proxy = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    frei = f"http://127.0.0.1:{_freier_port()}/x"
    urls = [f"{server}/ok", f"{server}/um", f"{server}/fremd", f"{server}/fehlt", frei, f"{server}/ok"]
    ergebnisse = {e.url: e for e in lp.pruefe_urls(urls, timeout=5, oeffner=ohne_proxy)}
    assert len(ergebnisse) == 5, "jede URL nur einmal"
    assert ergebnisse[f"{server}/ok"].status == lp.OK
    assert ergebnisse[f"{server}/um"].status == lp.OK, "Umleitung auf denselben Host ist in Ordnung"
    assert ergebnisse[f"{server}/fremd"].status == lp.UMLEITUNG
    assert ergebnisse[f"{server}/fehlt"].status == lp.FEHLER and ergebnisse[f"{server}/fehlt"].code == 404
    assert ergebnisse[frei].status == lp.NICHT_ERREICHBAR
    assert not lp.kein_netz(list(ergebnisse.values()))
    assert lp.kein_netz([ergebnisse[frei]] * 9 + [ergebnisse[f"{server}/fehlt"]])


@pytest.mark.anforderung("ANF-QS-05")
def test_url_kodieren():
    assert lp.url_kodieren("https://x.de/Eigentumsförderung.pdf") == "https://x.de/Eigentumsf%C3%B6rderung.pdf"
    bereits = "https://x.de/Merkbl%C3%A4tter/a.pdf?x=1&y=%20z"
    assert lp.url_kodieren(bereits) == bereits


@pytest.mark.anforderung("ANF-QS-05")
def test_linkpruefung_umlaut(server):
    ohne_proxy = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    # Umlaut im Pfad: kein Absturz, sondern normale 404 vom Server
    assert lp.pruefe_url(f"{server}/Förderung.pdf", oeffner=ohne_proxy).code == 404


@pytest.mark.anforderung("ANF-QS-05")
def test_linkpruefung_bot_schutz():
    class Antwort:
        status = 200

        def geturl(self):
            return "https://validate.perfdrive.com/?ssa=1"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Oeffner:
        def open(self, anfrage, timeout):
            return Antwort()

    e = lp.pruefe_url("https://www.foerderdatenbank.de/x.html", oeffner=Oeffner())
    assert e.status == lp.NICHT_ERREICHBAR and "Bot-Schutz" in e.meldung


@pytest.mark.anforderung("ANF-QS-05")
def test_linkpruefung_ungueltige_url():
    e = lp.pruefe_url("example.org/ohne-schema.pdf")  # scheitert ohne Netz
    assert e.status == lp.FEHLER and "ungültige URL" in e.meldung


def _freier_port() -> int:
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.anforderung("ANF-QS-05")
def test_cli_links(capsys, monkeypatch):
    def fake(ergebnis_fuer):
        monkeypatch.setattr(lp, "pruefe_urls", lambda urls, **_: [ergebnis_fuer(u) for u in dict.fromkeys(urls)])

    fake(lambda u: lp.Linkergebnis(u, lp.OK, 200, u))
    assert main(["--keine-farbe", "quellen", "--links", "--phase1"]) == 0
    assert "ok: " in capsys.readouterr().out

    fake(lambda u: lp.Linkergebnis(u, lp.FEHLER, 404, meldung="HTTP 404") if "beeg/__1" in u
         else lp.Linkergebnis(u, lp.OK, 200, u))
    assert main(["--keine-farbe", "quellen", "--links", "--phase1"]) == 1
    out = capsys.readouterr().out
    assert "[fehler] beeg_1" in out and "HTTP 404" in out

    fake(lambda u: lp.Linkergebnis(u, lp.NICHT_ERREICHBAR, meldung="Tunnel connection failed: 403"))
    assert main(["--keine-farbe", "quellen", "--links"]) == 2
    assert "sperrender Proxy" in capsys.readouterr().out
