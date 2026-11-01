"""LLM-Adapter, Konfiguration und Fake-Modell (#74). Kein Netz: Mistral wird lokal nachgestellt."""

import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from buergerai import llm
from buergerai.cli import main
from buergerai.llm.basis import FEHLERARTEN
from buergerai.llm.mistral import MistralLLM

PROBE = Path(__file__).parent / "daten" / "llm" / "probe.json"
GEHEIM = "GEHEIMER-FREITEXT-4711"
SCHLUESSEL = "sk-test-SCHLUESSEL-0815"
SCHEMA = {
    "type": "object",
    "properties": {"lebenslagen": {"type": "array", "items": {"type": "string"}}},
    "required": ["lebenslagen"],
    "additionalProperties": False,
}


# ------------------------------------------------------------------ Mistral nachgestellt


def _antwort(inhalt, grund="stop"):
    return 200, {}, {"choices": [{"message": {"role": "assistant", "content": inhalt}, "finish_reason": grund}],
                     "usage": {"prompt_tokens": 12, "completion_tokens": 3}}


class _Server:
    """Lokaler Ersatz für die Mistral-API: spielt vorbereitete Antworten nacheinander ab."""

    def __init__(self, antworten):
        self.antworten = list(antworten)
        self.anfragen = []
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                laenge = int(self.headers.get("Content-Length", 0))
                server.anfragen.append({"headers": dict(self.headers),
                                        "body": json.loads(self.rfile.read(laenge))})
                status, header, body = server.antworten.pop(0)
                if status == "schlafen":
                    time.sleep(header)
                    status, header, body = _antwort('{"lebenslagen": []}')
                self.send_response(status)
                for k, v in header.items():
                    self.send_header(k, v)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(body).encode())

            def log_message(self, *args):
                pass

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/v1/chat/completions"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def schliessen(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def mistral(monkeypatch):
    # Kein Proxy für den lokalen Server
    for name in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(name, raising=False)
    server_liste = []
    gewartet = []

    def bauen(*antworten, timeout=5.0, versuche=3):
        server = _Server(antworten)
        server_liste.append(server)
        konfig = llm.Konfiguration("mistral", "mistral-small-latest", schluessel=SCHLUESSEL, timeout=timeout,
                                   versuche=versuche, url=server.url)
        return MistralLLM(konfig, schlafen=gewartet.append), server, gewartet

    yield bauen
    for s in server_liste:
        s.schliessen()


# ------------------------------------------------------------------ Konfiguration


@pytest.mark.anforderung("ANF-LLM-02")
def test_ohne_anbieter_ist_die_llm_schicht_aus():
    assert llm.aus_umgebung({}) is None
    assert llm.aus_umgebung({"BUERGERAI_LLM_ANBIETER": "  "}) is None
    assert llm.llm_aus_umgebung({}) is None


@pytest.mark.anforderung("ANF-LLM-02")
def test_mistral_konfiguration():
    k = llm.aus_umgebung({"BUERGERAI_LLM_ANBIETER": "Mistral", "MISTRAL_API_KEY": SCHLUESSEL,
                          "BUERGERAI_LLM_TIMEOUT": "7.5", "BUERGERAI_LLM_VERSUCHE": "2"})
    assert (k.anbieter, k.modell, k.timeout, k.versuche) == ("mistral", "mistral-small-latest", 7.5, 2)
    assert SCHLUESSEL not in repr(k) and SCHLUESSEL not in k.beschreibung()
    assert "Schlüssel gesetzt" in k.beschreibung()
    k = llm.aus_umgebung({"BUERGERAI_LLM_ANBIETER": "mistral", "MISTRAL_API_KEY": "x",
                          "BUERGERAI_LLM_MODELL": "mistral-medium-latest"})
    assert k.modell == "mistral-medium-latest"


@pytest.mark.anforderung("ANF-LLM-02")
@pytest.mark.parametrize("env, meldung", [
    ({"BUERGERAI_LLM_ANBIETER": "openai"}, "unbekannt"),
    ({"BUERGERAI_LLM_ANBIETER": "mistral"}, "MISTRAL_API_KEY fehlt"),
    ({"BUERGERAI_LLM_ANBIETER": "fake"}, "BUERGERAI_LLM_FAKE_DATEI fehlt"),
    ({"BUERGERAI_LLM_ANBIETER": "mistral", "MISTRAL_API_KEY": "x", "BUERGERAI_LLM_TIMEOUT": "schnell"}, "Zahl"),
    ({"BUERGERAI_LLM_ANBIETER": "mistral", "MISTRAL_API_KEY": "x", "BUERGERAI_LLM_VERSUCHE": "0"}, "größer als 0"),
])
def test_fehlerhafte_konfiguration(env, meldung, caplog):
    with pytest.raises(llm.LLMKonfigurationsfehler, match=meldung):
        llm.aus_umgebung(env)
    # In der Anwendung schaltet eine fehlerhafte Konfiguration die LLM-Schicht aus
    with caplog.at_level(logging.WARNING, logger="buergerai.llm"):
        assert llm.llm_aus_umgebung(env) is None
    assert "konfiguration" in caplog.text


@pytest.mark.anforderung("ANF-LLM-02")
def test_cli_llm(capsys, monkeypatch):
    monkeypatch.delenv("BUERGERAI_LLM_ANBIETER", raising=False)
    assert main(["--keine-farbe", "llm"]) == 0
    assert "LLM-Schicht aus" in capsys.readouterr().out
    assert main(["--keine-farbe", "llm", "--probe"]) == 1
    capsys.readouterr()
    monkeypatch.setenv("BUERGERAI_LLM_ANBIETER", "fake")
    monkeypatch.setenv("BUERGERAI_LLM_FAKE_DATEI", str(PROBE))
    assert main(["--keine-farbe", "llm", "--probe"]) == 0
    assert "✓ Antwort im Schema" in capsys.readouterr().out
    monkeypatch.setenv("BUERGERAI_LLM_ANBIETER", "mistral")
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    assert main(["--keine-farbe", "llm"]) == 2
    assert "MISTRAL_API_KEY fehlt" in capsys.readouterr().out


# ------------------------------------------------------------------ FakeLLM


@pytest.mark.anforderung("ANF-LLM-03")
def test_fake_liefert_vorbereitete_antworten():
    fake = llm.FakeLLM.aus_datei(PROBE)
    assert fake.strukturiert("sys", "Ich bin schwanger", SCHEMA, aufgabe="router") == {"lebenslagen": ["geburt"]}
    assert "Elterngeld" in fake.text("sys", "Bericht", aufgabe="antwort")
    assert [(a["art"], a["aufgabe"], a["eingabe"]) for a in fake.aufrufe] == [
        ("strukturiert", "router", "Ich bin schwanger"), ("text", "antwort", "Bericht")]
    with pytest.raises(llm.LLMTimeout):
        fake.strukturiert("sys", "Zeitüberschreitung bitte", SCHEMA, aufgabe="router")
    with pytest.raises(llm.LLMUngueltigeAusgabe, match="keine vorbereitete Antwort"):
        fake.strukturiert("sys", "Wir ziehen um", SCHEMA, aufgabe="router")


@pytest.mark.anforderung("ANF-LLM-03")
def test_fake_prueft_schema_und_eintraege():
    fake = llm.FakeLLM([{"antwort": {"falsch": 1}}, {"aufgabe": "text", "antwort": {"kein": "text"}}])
    with pytest.raises(llm.LLMUngueltigeAusgabe, match="Pflichtfelder fehlen: lebenslagen"):
        fake.strukturiert("s", "e", SCHEMA, aufgabe="router")
    with pytest.raises(llm.LLMUngueltigeAusgabe, match="Felder außerhalb"):
        llm.FakeLLM([{"antwort": {"lebenslagen": [], "extra": 1}}]).strukturiert("s", "e", SCHEMA, aufgabe="router")
    assert llm.FakeLLM([{"antwort": '{"lebenslagen": []}'}]).strukturiert("s", "e", SCHEMA, aufgabe="r") == {
        "lebenslagen": []}
    with pytest.raises(llm.LLMUngueltigeAusgabe, match="kein gültiges JSON"):
        llm.FakeLLM([{"antwort": "kein json"}]).strukturiert("s", "e", SCHEMA, aufgabe="r")
    with pytest.raises(llm.LLMUngueltigeAusgabe, match="Text erwartet"):
        fake.text("s", "e", aufgabe="text")
    with pytest.raises(llm.LLMKonfigurationsfehler):
        llm.FakeLLM([{"fehler": "explodiert"}])
    with pytest.raises(llm.LLMKonfigurationsfehler):
        llm.FakeLLM([{"aufgabe": "router"}])
    with pytest.raises(llm.LLMKonfigurationsfehler, match="nicht lesbar"):
        llm.FakeLLM.aus_datei(PROBE.parent / "gibt_es_nicht.json")


# ------------------------------------------------------------------ Mistral-Adapter


@pytest.mark.anforderung("ANF-LLM-04")
def test_mistral_anfrage_und_antwort(mistral):
    m, server, _ = mistral(_antwort('{"lebenslagen": ["geburt"]}'), _antwort("Hallo"))
    assert m.strukturiert("System", "Ich bin schwanger", SCHEMA, aufgabe="router", max_tokens=200) == {
        "lebenslagen": ["geburt"]}
    anfrage = server.anfragen[0]
    assert anfrage["headers"]["Authorization"] == f"Bearer {SCHLUESSEL}"
    body = anfrage["body"]
    assert body["model"] == "mistral-small-latest" and body["temperature"] == 0 and body["max_tokens"] == 200
    assert body["messages"] == [{"role": "system", "content": "System"}, {"role": "user", "content": "Ich bin schwanger"}]
    assert body["response_format"] == {"type": "json_schema",
                                       "json_schema": {"name": "router", "schema": SCHEMA, "strict": True}}
    assert m.text("System", "Bericht", aufgabe="antwort") == "Hallo"
    assert "response_format" not in server.anfragen[1]["body"]


@pytest.mark.anforderung("ANF-LLM-04")
def test_mistral_wiederholt_bei_rate_limit(mistral):
    m, server, gewartet = mistral((429, {"Retry-After": "2"}, {}), (503, {}, {}), _antwort('{"lebenslagen": []}'))
    assert m.strukturiert("s", "e", SCHEMA, aufgabe="router") == {"lebenslagen": []}
    assert len(server.anfragen) == 3
    assert gewartet == [2.0, 2.0]  # Retry-After, dann 2 ** (2 - 1)


@pytest.mark.anforderung("ANF-LLM-04")
@pytest.mark.parametrize("antworten, fehler, versuche", [
    ([(429, {}, {})] * 3, llm.LLMRateLimit, 3),
    ([(500, {}, {})] * 2, llm.LLMDienstfehler, 2),
    ([(401, {}, {"message": GEHEIM})], llm.LLMKonfigurationsfehler, 1),
    ([(422, {}, {"message": GEHEIM})], llm.LLMDienstfehler, 1),
    ([_antwort("kein json")], llm.LLMUngueltigeAusgabe, 1),
    ([_antwort('{"lebenslagen": [')], llm.LLMUngueltigeAusgabe, 1),
    ([_antwort('{"lebenslagen": []}', grund="length")], llm.LLMUngueltigeAusgabe, 1),
    ([_antwort('{"lebenslagen": []}', grund="content_filter")], llm.LLMAblehnung, 1),
    ([_antwort("")], llm.LLMUngueltigeAusgabe, 1),
    ([(200, {}, {"keine": "choices"})], llm.LLMUngueltigeAusgabe, 1),
])
def test_mistral_einheitliche_fehler(mistral, antworten, fehler, versuche):
    m, server, gewartet = mistral(*antworten, versuche=versuche)
    with pytest.raises(fehler) as info:
        m.strukturiert("s", "e", SCHEMA, aufgabe="router")
    assert GEHEIM not in str(info.value)
    assert len(server.anfragen) == len(antworten)
    assert len(gewartet) == (versuche - 1 if fehler in (llm.LLMRateLimit, llm.LLMDienstfehler) and versuche > 1 else 0)


@pytest.mark.anforderung("ANF-LLM-04")
def test_mistral_timeout(mistral):
    m, _, _ = mistral(("schlafen", 1.0, None), timeout=0.2)
    with pytest.raises(llm.LLMTimeout):
        m.strukturiert("s", "e", SCHEMA, aufgabe="router")


@pytest.mark.anforderung("ANF-LLM-04")
def test_mistral_ohne_verbindung():
    konfig = llm.Konfiguration("mistral", "m", schluessel="x", timeout=1, versuche=1,
                               url="http://127.0.0.1:9/v1/chat/completions")
    with pytest.raises(llm.LLMDienstfehler, match="keine Verbindung"):
        MistralLLM(konfig).text("s", "e", aufgabe="antwort")
    with pytest.raises(llm.LLMKonfigurationsfehler):
        MistralLLM(llm.Konfiguration("mistral", "m"))


def test_wartezeit_begrenzt():
    assert MistralLLM._wartezeit("120", 1) == 30.0
    assert MistralLLM._wartezeit("bald", 3) == 4.0
    assert MistralLLM._wartezeit(None, 10) == 30.0


# ------------------------------------------------------------------ Fallback


@pytest.mark.anforderung("ANF-LLM-05")
@pytest.mark.parametrize("art", sorted(FEHLERARTEN))
def test_fallback_bei_jedem_llm_fehler(art):
    fake = llm.FakeLLM([{"aufgabe": "router", "fehler": art}])
    e = llm.mit_fallback(fake, lambda m: m.strukturiert("s", "e", SCHEMA, aufgabe="router"),
                         lambda: {"lebenslagen": ["aus_stichwortsuche"]})
    assert (e.wert, e.quelle, e.fehler) == ({"lebenslagen": ["aus_stichwortsuche"]}, "fallback", art)


@pytest.mark.anforderung("ANF-LLM-05")
def test_fallback_ohne_llm_und_erfolg():
    e = llm.mit_fallback(None, lambda m: pytest.fail("darf nicht aufgerufen werden"), lambda: "formular")
    assert (e.wert, e.quelle, e.fehler) == ("formular", "fallback", "aus")
    fake = llm.FakeLLM([{"antwort": {"lebenslagen": ["geburt"]}}])
    e = llm.mit_fallback(fake, lambda m: m.strukturiert("s", "e", SCHEMA, aufgabe="router"), lambda: None)
    assert (e.wert, e.quelle, e.fehler) == ({"lebenslagen": ["geburt"]}, "llm", None)


@pytest.mark.anforderung("ANF-LLM-05")
def test_programmfehler_werden_nicht_verschluckt():
    def kaputt(m):
        raise KeyError("Bug im Aufrufer")

    with pytest.raises(KeyError):
        llm.mit_fallback(llm.FakeLLM([]), kaputt, lambda: None)


@pytest.mark.anforderung("ANF-LLM-05")
def test_fallback_bei_mistral_fehler(mistral):
    m, _, _ = mistral((429, {}, {}), versuche=1)
    e = llm.mit_fallback(m, lambda x: x.strukturiert("s", "e", SCHEMA, aufgabe="router"), lambda: "stichwortsuche")
    assert (e.wert, e.fehler) == ("stichwortsuche", "rate_limit")


# ------------------------------------------------------------------ Logs ohne Freitexte


@pytest.mark.anforderung("ANF-LLM-06")
def test_logs_ohne_freitexte_und_schluessel(mistral, caplog):
    m, _, _ = mistral(_antwort(json.dumps({"lebenslagen": [GEHEIM]})), (429, {}, {"message": GEHEIM}),
                      (422, {}, {"message": GEHEIM}), _antwort(GEHEIM), versuche=2)
    fake = llm.FakeLLM([{"aufgabe": "router", "enthaelt": GEHEIM, "antwort": {"lebenslagen": [GEHEIM]}},
                        {"aufgabe": "antwort", "fehler": "ablehnung"}])
    with caplog.at_level(logging.DEBUG):
        m.strukturiert(f"System {GEHEIM}", f"Freitext {GEHEIM}", SCHEMA, aufgabe="router")
        for aufruf in (lambda: m.strukturiert("s", f"Freitext {GEHEIM}", SCHEMA, aufgabe="router"),
                       lambda: m.strukturiert("s", f"Freitext {GEHEIM}", SCHEMA, aufgabe="router")):
            with pytest.raises(llm.LLMFehler) as info:
                aufruf()
            assert GEHEIM not in str(info.value)
        fake.strukturiert("s", f"Freitext {GEHEIM}", SCHEMA, aufgabe="router")
        llm.mit_fallback(fake, lambda x: x.text("s", f"Freitext {GEHEIM}", aufgabe="antwort"), lambda: "ok")
    assert caplog.records, "jeder Aufruf wird protokolliert"
    assert GEHEIM not in caplog.text and SCHLUESSEL not in caplog.text
    assert "aufgabe=router" in caplog.text and "tokens_ein=12" in caplog.text and "ergebnis=dienst" in caplog.text


# ------------------------------------------------------------------ .env


@pytest.mark.anforderung("ANF-LLM-07")
def test_env_datei_lesen(tmp_path):
    from buergerai.llm.konfiguration import env_datei_lesen

    datei = tmp_path / ".env"
    datei.write_text(
        "# Kommentar\n\nBUERGERAI_LLM_ANBIETER=mistral\nexport MISTRAL_API_KEY = 'sk-mit # raute'\n"
        'BUERGERAI_LLM_MODELL="mistral-small-latest"\nBUERGERAI_LLM_TIMEOUT=30 # Sekunden\n'
        f"kaputte zeile {GEHEIM}\n1FALSCH=x\nLEER=\n", encoding="utf-8")
    assert env_datei_lesen(datei) == {
        "BUERGERAI_LLM_ANBIETER": "mistral", "MISTRAL_API_KEY": "sk-mit # raute",
        "BUERGERAI_LLM_MODELL": "mistral-small-latest", "BUERGERAI_LLM_TIMEOUT": "30", "LEER": ""}


@pytest.mark.anforderung("ANF-LLM-07")
def test_env_datei_wird_gelesen_umgebung_hat_vorrang(tmp_path, monkeypatch, caplog):
    datei = tmp_path / "meine.env"
    datei.write_text(f"BUERGERAI_LLM_ANBIETER=mistral\nMISTRAL_API_KEY={SCHLUESSEL}\nBUERGERAI_LLM_TIMEOUT=30\n"
                     f"ungueltig {GEHEIM}\n", encoding="utf-8")
    monkeypatch.setenv("BUERGERAI_ENV_DATEI", str(datei))
    for name in ("BUERGERAI_LLM_ANBIETER", "MISTRAL_API_KEY", "BUERGERAI_LLM_MODELL", "BUERGERAI_LLM_VERSUCHE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("BUERGERAI_LLM_TIMEOUT", "5")
    with caplog.at_level(logging.DEBUG, logger="buergerai.llm"):
        k = llm.aus_umgebung()
    assert (k.anbieter, k.schluessel, k.timeout) == ("mistral", SCHLUESSEL, 5.0)
    assert llm.env_datei_finden() == datei
    assert "zeile=4" in caplog.text and GEHEIM not in caplog.text and SCHLUESSEL not in caplog.text


@pytest.mark.anforderung("ANF-LLM-07")
def test_env_im_aktuellen_ordner(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("BUERGERAI_ENV_DATEI")
    for name in ("BUERGERAI_LLM_ANBIETER", "MISTRAL_API_KEY", "BUERGERAI_LLM_FAKE_DATEI"):
        monkeypatch.delenv(name, raising=False)
    (tmp_path / ".env").write_text(f"BUERGERAI_LLM_ANBIETER=fake\nBUERGERAI_LLM_FAKE_DATEI={PROBE}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert main(["--keine-farbe", "llm", "--probe"]) == 0
    out = capsys.readouterr().out
    assert "Anbieter fake" in out and f"Werte aus {tmp_path / '.env'}" in out


@pytest.mark.anforderung("ANF-LLM-07")
def test_platzhalter_aus_der_vorlage_wird_erkannt():
    from buergerai.llm.konfiguration import REPO, env_datei_lesen

    vorlage = env_datei_lesen(REPO / ".env.beispiel")
    with pytest.raises(llm.LLMKonfigurationsfehler, match="Platzhalter"):
        llm.aus_umgebung(vorlage)


@pytest.mark.anforderung("ANF-LLM-07")
def test_env_wird_nicht_eingecheckt():
    from buergerai.llm.konfiguration import REPO

    regeln = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in regeln and ".env.*" in regeln and "!.env.beispiel" in regeln
    assert (REPO / ".env.beispiel").is_file()


# ------------------------------------------------------------------ TLS-Zertifikate


@pytest.fixture
def https_server(tmp_path, monkeypatch):
    """Lokaler HTTPS-Server mit selbst erzeugtem Zertifikat, wie Mistral hinter einem Firmen-Proxy."""
    import shutil
    import ssl
    import subprocess

    if not shutil.which("openssl"):
        pytest.skip("openssl nicht installiert")
    for name in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(name, raising=False)
    zert, schluessel = tmp_path / "zert.pem", tmp_path / "schluessel.pem"
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj", "/CN=127.0.0.1",
                    "-addext", "subjectAltName=IP:127.0.0.1", "-keyout", str(schluessel), "-out", str(zert)],
                   check=True, capture_output=True)
    server = _Server([_antwort('{"lebenslagen": []}')])
    kontext = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    kontext.load_cert_chain(zert, schluessel)
    server.httpd.socket = kontext.wrap_socket(server.httpd.socket, server_side=True)
    yield server.url.replace("http://", "https://"), zert
    server.schliessen()


@pytest.mark.anforderung("ANF-LLM-08")
def test_unbekanntes_zertifikat_klare_meldung(https_server):
    url, _ = https_server
    m = MistralLLM(llm.Konfiguration("mistral", "m", schluessel="x", timeout=5, versuche=1, url=url))
    with pytest.raises(llm.LLMDienstfehler, match="TLS-Zertifikat nicht prüfbar.*BUERGERAI_LLM_CA_DATEI"):
        m.strukturiert("s", "e", SCHEMA, aufgabe="router")


@pytest.mark.anforderung("ANF-LLM-08")
def test_eigene_zertifikatsdatei(https_server):
    url, zert = https_server
    k = llm.aus_umgebung({"BUERGERAI_LLM_ANBIETER": "mistral", "MISTRAL_API_KEY": "x", "BUERGERAI_LLM_URL": url,
                          "BUERGERAI_LLM_CA_DATEI": str(zert)})
    assert f"Zertifikate aus {zert}" in k.beschreibung()
    assert MistralLLM(k).strukturiert("s", "e", SCHEMA, aufgabe="router") == {"lebenslagen": []}


@pytest.mark.anforderung("ANF-LLM-08")
def test_ungueltige_zertifikatsdatei(tmp_path):
    with pytest.raises(llm.LLMKonfigurationsfehler, match="nicht gefunden"):
        llm.aus_umgebung({"BUERGERAI_LLM_ANBIETER": "mistral", "MISTRAL_API_KEY": "x",
                          "BUERGERAI_LLM_CA_DATEI": str(tmp_path / "fehlt.pem")})
    kaputt = tmp_path / "kaputt.pem"
    kaputt.write_text("kein Zertifikat", encoding="utf-8")
    with pytest.raises(llm.LLMKonfigurationsfehler, match="keine gültigen Zertifikate"):
        MistralLLM(llm.Konfiguration("mistral", "m", schluessel="x", ca_datei=str(kaputt)))
