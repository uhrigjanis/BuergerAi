"""Zitat- und Zahlen-Abgleich gegen den Quelltext (#63) – ohne Netz, mit Beispieldateien."""

from __future__ import annotations

import io
import zipfile
from datetime import date
from pathlib import Path

import pytest

from buergerai import abgleich as ab
from buergerai import quellenpruefung as qp
from buergerai import quelltext as qt
from buergerai.cli import main

DATEN = Path(__file__).parent / "daten" / "quelltext"
BEEG_XML = (DATEN / "beeg_auszug.xml").read_bytes()
BAYFAMGG_HTML = (DATEN / "bayfamgg_9a.html").read_bytes()


def als_zip(xml: bytes) -> bytes:
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w") as z:
        z.writestr("BJNR274810006.xml", xml)
    return puffer.getvalue()


class FakeNetz:
    """Abrufer ohne Netz: liefert hinterlegte Inhalte und zählt Abrufe."""

    def __init__(self, inhalte: dict[str, tuple[bytes, str]]):
        self.inhalte = inhalte
        self.abrufe: list[str] = []

    def __call__(self, url: str) -> tuple[bytes, str]:
        self.abrufe.append(url)
        if url not in self.inhalte:
            raise qt.AbrufFehler("Tunnel connection failed: 403 Forbidden")
        return self.inhalte[url]


NETZ = {
    "https://www.gesetze-im-internet.de/beeg/xml.zip": (als_zip(BEEG_XML), "application/zip"),
    "https://www.gesetze-bayern.de/Content/Document/BayFamGG-9a": (BAYFAMGG_HTML, "text/html; charset=utf-8"),
    "https://example.org/merkblatt.pdf": (b"%PDF-1.7 ...", "application/pdf"),
}


@pytest.mark.anforderung("ANF-QS-06")
@pytest.mark.parametrize("url,erwartet", [
    ("https://www.gesetze-im-internet.de/beeg/__1.html", ("beeg", "§ 1")),
    ("https://gesetze-im-internet.de/bgb/__1626a.html", ("bgb", "§ 1626a")),
    ("https://www.gesetze-im-internet.de/beeg/", ("beeg", None)),
    ("https://www.gesetze-im-internet.de/gg/art_9.html", ("gg", "Art 9")),
    ("https://www.gesetze-bayern.de/Content/Document/BayFamGG-9a", None),
])
def test_gii_ziel(url, erwartet):
    assert qt.gii_ziel(url) == erwartet


@pytest.mark.anforderung("ANF-QS-06")
def test_gesetz_als_xml():
    abschnitte, stand, kuerzel = qt.gii_xml_lesen(als_zip(BEEG_XML))
    assert kuerzel == "BEEG" and stand == "Zuletzt geändert durch Art. 1 G v. 1.1.2026 I Nr. 1"
    assert set(abschnitte) == {"§ 1", "§ 7"}
    assert "32 Wochenstunden" in abschnitte["§ 1"] and "Berechtigte" in abschnitte["§ 1"]
    assert "99 999" not in abschnitte["§ 1"], "Fußnoten zählen nicht zum Text"
    # Aufzählungen bleiben lesbar
    assert "1. einen Wohnsitz" in abschnitte["§ 1"]


@pytest.mark.anforderung("ANF-QS-06")
def test_holen_mit_zwischenspeicher(tmp_path):
    netz = FakeNetz(NETZ)
    speicher = qt.Zwischenspeicher(netz, tmp_path)
    q1 = qt.holen("https://www.gesetze-im-internet.de/beeg/__1.html", speicher)
    q7 = qt.holen("https://www.gesetze-im-internet.de/beeg/__7.html", speicher)
    assert (q1.status, q1.abschnitt_name) == (qt.OK, "§ 1 BEEG") and "175 000" in q1.pruefbereich
    assert "drei Lebensmonate" in q7.pruefbereich and "175 000" not in q7.pruefbereich
    assert len(netz.abrufe) == 1, "ein Gesetz wird nur einmal geladen"

    # Neuer Prozess: aus dem Plattenspeicher, ohne Netz
    zweiter = FakeNetz({})
    q = qt.holen("https://www.gesetze-im-internet.de/beeg/__1.html", qt.Zwischenspeicher(zweiter, tmp_path))
    assert q.status == qt.OK and not zweiter.abrufe

    fehlt = qt.holen("https://www.gesetze-im-internet.de/beeg/__99.html", speicher)
    assert fehlt.abschnitt is None and "nicht im XML" in fehlt.meldung and fehlt.pruefbereich == fehlt.text

    html = qt.holen("https://www.gesetze-bayern.de/Content/Document/BayFamGG-9a", speicher)
    assert html.status == qt.OK and "unbeachtlich" in html.text
    assert "darf hier nicht zählen" not in html.text and ".a{}" not in html.text
    assert qt.holen("https://example.org/merkblatt.pdf", speicher).status == qt.MANUELL
    weg = qt.holen("https://www.zbfs.bayern.de/x", speicher)
    assert weg.status == qt.NICHT_ERREICHBAR and "403" in weg.meldung


@pytest.mark.anforderung("ANF-QS-06")
def test_html_unbekannter_zeichensatz():
    assert "unbeachtlich" in qt.html_text(BAYFAMGG_HTML, "text/html; charset=gibtsnicht")
    assert "Grüße" in qt.html_text("<p>Grüße</p>".encode("latin-1"), "text/html; charset=ISO-8859-1")


@pytest.mark.anforderung("ANF-QS-06")
def test_zitate_aus_protokoll():
    text = (qp.PROTOKOLL_VERZEICHNIS / "bayfamgg_9a.md").read_text(encoding="utf-8")
    zitate = ab.zitate_aus_protokoll(text)
    assert [z.zeile for z in zitate] == [1, 3, 3]
    assert zitate[1].text.startswith("Anträge auf Familiengeld")
    # „…“ ist eine Lücke: zwei Teilstücke
    assert len(zitate[2].teilstuecke()) == 2
    # Anführungszeichen in der Ergebnis-Spalte zählen nicht
    assert not any(z.text == "unbeachtlich" for z in zitate)


@pytest.mark.anforderung("ANF-QS-06")
@pytest.mark.parametrize("zitat,gefunden", [
    ("Anträge auf Familiengeld für Kinder, die ab dem 1. Januar 2025 geboren wurden, sind unbeachtlich.", True),
    # Silbentrennung, geschütztes Leerzeichen, typografische Zeichen
    ("des Bayerischen Familiengeldgesetzes (BayFamGG) in der am 30. Dezember 2025 geltenden Fassung", True),
    ("Hinsichtlich vor dem 1. Januar 2025 geborener Kinder … weiter anzuwenden.", True),
    ("ab dem 1. September 2026 geboren wurden, sind unbeachtlich", False),
    ("Hinsichtlich vor dem 1. Januar 2025 … am 30. Dezember 2024 geltenden Fassung", False),
])
def test_zitat_gefunden(zitat, gefunden):
    text = qt.html_text(BAYFAMGG_HTML, "text/html; charset=utf-8")
    assert ab.zitat_gefunden(ab.Zitat(1, zitat), text) is gefunden


@pytest.mark.anforderung("ANF-QS-06")
@pytest.mark.parametrize("wert,text,gefunden", [
    (175000, "von mehr als 175 000 Euro", True),
    (175000, "von mehr als 175.000 Euro", True),
    (175000, "von mehr als 1 175 000 Euro", False),
    (32, "32 Wochenstunden", True),
    (32, "320 Stunden", False),
    (date(2025, 1, 1), "ab dem 1. Januar 2025 geboren", True),
    (date(2025, 1, 1), "ab dem 01.01.2025", True),
    (date(2025, 1, 1), "ab dem 1. Januar 2026", False),
    (("tage", 7), "binnen einer Woche anzuzeigen", True),
    (("tage", 7), "innerhalb von sieben Tagen", True),
    (("monate", 3), "die letzten drei Lebensmonate vor", True),
    (("monate", 6), "die letzten drei Lebensmonate vor", False),
    (("wochen", 7), "spätestens sieben Wochen vor Beginn", True),
    (13.5, "bis zu 13,50 Euro", True),
])
def test_zahl_gefunden(wert, text, gefunden):
    assert ab.zahl_gefunden(ab.Zahl(wert, "test"), text) is gefunden


@pytest.mark.anforderung("ANF-QS-06")
def test_zahlen_der_quelle(kb):
    werte = {z.wert for z in ab.zahlen_der_quelle(kb, "beeg_1")}
    assert {32, 175000, date(2025, 4, 1)} <= werte
    assert 200000 in {z.wert for z in ab.zahlen_der_quelle(kb, "beeg_28")}, "Übergangsgrenze steht in § 28 BEEG"
    assert True not in werte and False not in werte
    assert ("tage", 7) in {z.wert for z in ab.zahlen_der_quelle(kb, "pstg_18")}
    assert {250, 300} <= {z.wert for z in ab.zahlen_der_quelle(kb, "bayfamgg_3")}


@pytest.mark.anforderung("ANF-QS-06")
def test_abgleich_und_protokoll(kb, tmp_path):
    protokolle = tmp_path / "pruefprotokolle"
    protokolle.mkdir()
    (protokolle / "bayfamgg_9a.md").write_text(
        (qp.PROTOKOLL_VERZEICHNIS / "bayfamgg_9a.md").read_text(encoding="utf-8"), encoding="utf-8")
    speicher = qt.Zwischenspeicher(FakeNetz(NETZ))
    a = ab.abgleichen(kb, "bayfamgg_9a", qt.holen(kb.quellen["bayfamgg_9a"].url, speicher), protokolle)
    assert len(a.zitate) == 3 and not a.fehlende_zitate
    assert a.zusammenfassung().startswith("Zitate 3/3")

    assert ab.in_protokoll_schreiben(a, date(2026, 10, 29), protokolle)
    assert ab.in_protokoll_schreiben(a, date(2026, 10, 30), protokolle), "zweiter Lauf ersetzt den Abschnitt"
    text = (protokolle / "bayfamgg_9a.md").read_text(encoding="utf-8")
    assert text.count(ab.ABSCHNITT) == 1 and "Stand 30.10.2026" in text and "Stand 29.10.2026" not in text
    assert "## Abweichungen und Folgeaktionen" in text, "übrige Abschnitte bleiben"

    # Ein falsches Zitat fällt auf
    falsch = text.replace("ab dem 1. Januar 2025 geboren", "ab dem 1. September 2026 geboren")
    (protokolle / "bayfamgg_9a.md").write_text(falsch, encoding="utf-8")
    b = ab.abgleichen(kb, "bayfamgg_9a", qt.holen(kb.quellen["bayfamgg_9a"].url, speicher), protokolle)
    assert [z.zeile for z in b.fehlende_zitate] == [3]


@pytest.mark.anforderung("ANF-QS-06")
def test_cli_abgleich(capsys, monkeypatch, tmp_path):
    monkeypatch.setattr(qt, "http_abruf", FakeNetz(NETZ))
    # Nur das Protokoll von bayfamgg_9a; beeg_1 wird ohne Protokoll gegen den gekürzten Testauszug geprüft
    protokolle = tmp_path / "pruefprotokolle"
    protokolle.mkdir()
    (protokolle / "bayfamgg_9a.md").write_text(
        (qp.PROTOKOLL_VERZEICHNIS / "bayfamgg_9a.md").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(qp, "PROTOKOLL_VERZEICHNIS", protokolle)
    bericht = tmp_path / "bericht.md"
    code = main(["--keine-farbe", "quellen", "--abgleich", "bayfamgg_9a", "beeg_1", "--ohne-cache",
                 "--bericht", str(bericht)])
    out = capsys.readouterr().out
    assert code == 0, out
    assert "bayfamgg_9a: Zitate 3/3" in out and "beeg_1: kein Protokoll" in out
    assert "Abschnitt: § 1 BEEG" in out
    assert "| `bayfamgg_9a` |" in bericht.read_text(encoding="utf-8")

    monkeypatch.setattr(qt, "http_abruf", FakeNetz({}))
    assert main(["--keine-farbe", "quellen", "--abgleich", "bayfamgg_9a", "--ohne-cache"]) == 2
    assert "Keine Quelle erreichbar" in capsys.readouterr().out


@pytest.mark.anforderung("ANF-QS-06")
def test_stummer_host_wird_nur_einmal_abgewartet():
    aufrufe: list[str] = []

    def zeitueberschreitung(url: str):
        aufrufe.append(url)
        raise qt.AbrufFehler("timed out", netz=True)

    speicher = qt.Zwischenspeicher(zeitueberschreitung)
    for p in ("__1", "__7", "__16"):
        q = qt.holen(f"https://www.gesetze-im-internet.de/beeg/{p}.html", speicher)
        assert q.status == qt.NICHT_ERREICHBAR
    q = qt.holen("https://www.gesetze-im-internet.de/bgb/__1592.html", speicher)
    assert "übersprungen" in q.meldung
    assert len(aufrufe) == 1, "ein Host, der nicht antwortet, kostet nur eine Wartezeit"


@pytest.mark.anforderung("ANF-QS-06")
def test_http_fehler_sperrt_den_host_nicht():
    speicher = qt.Zwischenspeicher(FakeNetz(NETZ))
    assert qt.holen("https://www.gesetze-bayern.de/gibt-es-nicht", speicher).status == qt.NICHT_ERREICHBAR
    assert qt.holen("https://www.gesetze-bayern.de/Content/Document/BayFamGG-9a", speicher).status == qt.OK


@pytest.mark.anforderung("ANF-QS-06")
def test_ungueltige_url_stuerzt_nicht_ab():
    q = qt.holen("example.org/ohne-schema.html", qt.Zwischenspeicher())  # scheitert ohne Netz
    assert q.status == qt.NICHT_ERREICHBAR and "ungültige URL" in q.meldung


@pytest.mark.anforderung("ANF-QS-06")
def test_negative_frist_ohne_vorzeichen(kb):
    wochen = [z for z in ab.zahlen_der_quelle(kb, "familienportal_mutterschaft") if isinstance(z.wert, tuple)]
    assert wochen and all(z.wert[1] > 0 for z in wochen)


@pytest.mark.anforderung("ANF-QS-06")
def test_senkrechter_strich_im_zitat():
    """Review #66: ein | im Zitat darf die Tabellenzeile nicht zerlegen (Gerüst schreibt \\|)."""
    assert qp.tabellenzellen("| 1 | a \\| b | `x` |  | ✅ |") == ["1", "a | b", "`x`", "", "✅"]
    text = ("## Verwendungen in der Wissensbasis (1)\n\n"
            "| # | Verwendung | Fundstelle | Wortlaut der Quelle (Zitat, Absatz) | Ergebnis |\n"
            "|---|---|---|---|---|\n"
            "| 1 | Betrag | `x` | Abs. 1: „Spalte A \\| Spalte B des Tarifs“ | ✅ |\n")
    zitate = ab.zitate_aus_protokoll(text)
    assert [z.text for z in zitate] == ["Spalte A | Spalte B des Tarifs"]
    assert qp.protokoll_lesen(text) == qp.Protokollstand(zeilen=1, ohne_ergebnis=0, abweichungen=0, hinweise=0)
