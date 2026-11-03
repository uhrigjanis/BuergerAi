"""Browser-Rauchtest der Web-Oberfläche (#99): Handy (420 px) und Desktop, hell und dunkel.

Nicht Teil von pytest/CI, weil Playwright keine Projekt-Abhängigkeit ist (ADR 0002).

    python -m pip install playwright pytest   # einmalig; nutzt das installierte Google Chrome
    PYTHONPATH=src:tests python scripts/web_rauchtest.py [--ausgabe ordner] [--chromium]

Prüft je Variante: keine Fehler in der Konsole, keine CSP-Verstöße, kein waagrechtes Scrollen,
Eingabezeile (Knopf erst mit Text gefüllt, Einwilligung beim Tippen), Checkliste, Schublade und
Details. Dazu ein Durchlauf nur mit der Tastatur. Screenshots landen im Ausgabeordner.
"""

import argparse
import sys
import threading
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from buergerai.web.server import erstellen
from buergerai.wissensbasis import Wissensbasis
from test_web_freitext import TEXT, fake_llm

VARIANTEN = [
    ("desktop", {"width": 1280, "height": 900}),
    ("handy", {"width": 420, "height": 860}),
]


def server_starten():
    server = erstellen(Wissensbasis.laden(), "127.0.0.1", 0, llm=fake_llm())
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def beobachten(seite, fehler):
    seite.on("console", lambda m: fehler.append(f"Konsole: {m.text}") if m.type == "error" else None)
    seite.on("pageerror", lambda e: fehler.append(f"Seitenfehler: {e}"))
    seite.add_init_script("document.addEventListener('securitypolicyviolation',"
                          " (e) => console.error('CSP: ' + e.violatedDirective + ' ' + e.blockedURI));")


def kein_querscrollen(seite, wo, fehler):
    breit = seite.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    if breit > 0:
        fehler.append(f"{wo}: {breit}px waagrecht zu breit")


def durchlauf(browser, basis, name, groesse, schema, ausgabe):
    fehler = []
    kontext = browser.new_context(viewport=groesse, color_scheme=schema, device_scale_factor=2)
    seite = kontext.new_page()
    beobachten(seite, fehler)
    bild = lambda teil: seite.screenshot(path=str(ausgabe / f"{name}-{schema}-{teil}.png"), full_page=True)  # noqa: E731

    seite.goto(basis + "/")
    expect(seite.locator("#start-titel")).to_have_text("Was ist bei Ihnen los?")
    expect(seite.locator(".kachel").first).to_be_visible()  # /api/meta geladen
    senden = seite.locator("#text-senden")
    expect(senden).not_to_have_class("senden bereit")
    expect(seite.locator("#einwilligung")).to_be_hidden()
    kein_querscrollen(seite, "Start", fehler)
    bild("1-start")

    # Eingabezeile: Text → Knopf gefüllt, Einwilligung sichtbar, wächst mit dem Text
    hoehe = seite.locator("#freitext").bounding_box()["height"]
    seite.locator("#freitext").fill(TEXT)
    seite.locator("#freitext").dispatch_event("input")
    expect(senden).to_have_class("senden bereit")
    expect(seite.locator("#einwilligung")).to_be_visible()
    if seite.locator("#freitext").bounding_box()["height"] <= hoehe and name == "handy":
        fehler.append("Eingabezeile wächst nicht mit dem Text")
    seite.locator("#einwilligung-ja").check()
    senden.click()
    expect(seite.locator("#verstanden")).to_be_visible()
    expect(seite.locator("#verstanden-text mark").first).to_be_visible()
    kein_querscrollen(seite, "Verstanden", fehler)
    bild("2-verstanden")

    seite.locator("#plz").fill("85354")
    seite.locator("#ort-senden").click()
    expect(seite.locator("#arbeit")).to_be_visible()
    expect(seite.locator("#frage-karte h2")).to_be_visible()
    expect(seite.get_by_role("button", name="Weiß nicht")).to_be_visible()
    expect(seite.locator(".zeile-leistung").first).to_be_visible()
    kein_querscrollen(seite, "Checkliste", fehler)
    seite.wait_for_timeout(300)  # Einblenden abwarten
    bild("3-checkliste")

    # Schublade: öffnet als Dialog, Escape schließt, Fokus zurück auf den Knopf
    seite.locator("#schublade-auf").click()
    expect(seite.locator("#schublade")).to_be_visible()
    seite.wait_for_timeout(300)
    seite.screenshot(path=str(ausgabe / f"{name}-{schema}-4-schublade.png"))
    seite.keyboard.press("Escape")
    expect(seite.locator("#schublade")).to_be_hidden()
    if seite.evaluate("document.activeElement.id") != "schublade-auf":
        fehler.append("Fokus nach Schließen der Schublade nicht auf dem Knopf")

    # Details einer Leistung
    seite.locator(".zeile-name").first.click()
    expect(seite.locator("#detail")).to_be_visible()
    seite.wait_for_timeout(300)
    seite.screenshot(path=str(ausgabe / f"{name}-{schema}-5-detail.png"))
    seite.keyboard.press("Escape")

    # Druckansicht: Behördenmappe statt Oberfläche
    seite.evaluate("window.print = () => {}")
    seite.locator("#drucken").click()
    seite.emulate_media(media="print")
    if not seite.locator("#druck h1").is_visible() or seite.locator("#arbeit").is_visible():
        fehler.append("Druckansicht zeigt nicht die Behördenmappe")
    seite.emulate_media(media="screen")
    kontext.close()
    return fehler


def tastatur(browser, basis):
    """Kompletter Einstieg und eine Antwort nur mit Tab, Leertaste und Enter."""
    fehler = []
    kontext = browser.new_context(viewport={"width": 1280, "height": 900})
    seite = kontext.new_page()
    beobachten(seite, fehler)
    seite.goto(basis + "/")
    seite.locator(".kachel").first.wait_for()

    def tab_bis(pruefung, wo, maximal=60):
        for _ in range(maximal):
            seite.keyboard.press("Tab")
            if seite.evaluate(pruefung):
                ring = seite.evaluate("getComputedStyle(document.activeElement).outlineStyle + '|' + "
                                      "getComputedStyle(document.activeElement).borderColor")
                return ring
        fehler.append(f"Tastatur: {wo} nicht erreichbar")
        return None

    tab_bis("document.activeElement.id === 'freitext'", "Eingabezeile")
    if tab_bis("document.activeElement.dataset.lebenslage === 'geburt'", "Kachel Geburt") is not None:
        ring = seite.evaluate("getComputedStyle(document.activeElement).outlineStyle")
        if ring in ("none", ""):
            fehler.append("Tastatur: Kachel ohne sichtbaren Fokusring")
        seite.keyboard.press("Space")
    tab_bis("document.activeElement.id === 'plz'", "Postleitzahl")
    seite.keyboard.type("80331")
    seite.keyboard.press("Enter")
    seite.locator("#arbeit").wait_for(state="visible")
    seite.locator("#schublade-auf").focus()
    seite.keyboard.press("Enter")
    if not seite.locator("#schublade").is_visible():
        fehler.append("Tastatur: Schublade öffnet nicht mit Enter")
    seite.keyboard.press("Escape")
    vorher = seite.locator("#frage-titel").inner_text()
    tab_bis("document.activeElement.textContent === 'Weiß nicht'", "Weiß nicht")
    seite.keyboard.press("Enter")
    seite.wait_for_function("(t) => document.querySelector('#frage-titel').innerText !== t", arg=vorher)
    kontext.close()
    return fehler


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ausgabe", default="rauchtest-bilder")
    p.add_argument("--chromium", action="store_true", help="Playwright-Chromium statt Google Chrome")
    args = p.parse_args()
    ausgabe = Path(args.ausgabe)
    ausgabe.mkdir(parents=True, exist_ok=True)
    server, basis = server_starten()
    alle = {}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel=None if args.chromium else "chrome")
            for name, groesse in VARIANTEN:
                for schema in ("light", "dark"):
                    alle[f"{name}/{schema}"] = durchlauf(browser, basis, name, groesse, schema, ausgabe)
            alle["tastatur"] = tastatur(browser, basis)
            browser.close()
    finally:
        server.shutdown()
    ok = True
    for name, fehler in alle.items():
        print(f"{'OK    ' if not fehler else 'FEHLER'} {name}")
        for f in fehler:
            print(f"         {f}")
        ok = ok and not fehler
    print(f"Screenshots: {ausgabe.resolve()}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
