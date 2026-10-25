"""Performance in Zielgröße (ADR 0008, ANF-DAT-14).

Die echten Daten sind noch klein. Damit Regressionen auffallen, bevor die
Lebenslagen aus #41 erfasst sind, wird eine synthetische Wissensbasis in der
Zielgröße erzeugt: etwa 500 Leistungen, 5.000 Varianten und 600 Fakten in
16 Lebenslagen, zusätzlich zu den echten Daten und allen Gebieten.
"""

from __future__ import annotations

import json
import shutil
import time
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from buergerai.planer import Anfrage, planen
from buergerai.szenarien import fakten_parsen
from buergerai.wissensbasis import STANDARD_DATENVERZEICHNIS, Wissensbasis

LEBENSLAGEN = 16
LEISTUNGEN = 490
FAKTEN = 583  # mit den 17 echten Fakten: 600
LAENDER = [f"{i:02d}" for i in range(1, 17)]
MIT_LANDESVARIANTEN = 280  # 280 Leistungen x 16 Länder + 490 Bundesvarianten ≈ 5.000 Varianten


def _modul() -> dict[str, Any]:
    fakten = []
    for i in range(FAKTEN):
        if i % 3 == 0:
            fakten.append({"id": f"last.f{i}", "typ": "ja_nein", "frage": f"Frage {i}?"})
        elif i % 3 == 1:
            fakten.append({"id": f"last.f{i}", "typ": "zahl", "frage": f"Zahl {i}?"})
        else:
            fakten.append({"id": f"last.f{i}", "typ": "auswahl", "frage": f"Auswahl {i}?",
                           "optionen": [{"wert": "a", "text": "A"}, {"wert": "b", "text": "B"}]})

    def bedingung(fid: int) -> dict[str, Any]:
        if fid % 3 == 0:
            return {"fakt": f"last.f{fid}", "op": "==", "wert": True, "text": f"Bedingung {fid}"}
        if fid % 3 == 1:
            return {"fakt": f"last.f{fid}", "op": "<=", "wert": 1000, "text": f"Bedingung {fid}"}
        return {"fakt": f"last.f{fid}", "op": "in", "wert": ["a"], "text": f"Bedingung {fid}"}

    leistungen, varianten = [], []
    for i in range(LEISTUNGEN):
        lagen = [f"last_{i % LEBENSLAGEN}"] + ([f"last_{(i + 1) % LEBENSLAGEN}"] if i % 10 == 0 else [])
        leistungen.append({"id": f"last_l{i}", "name": f"Leistung {i}", "kurz": "Synthetisch", "lebenslagen": lagen,
                           "verwaltungsebene": "land" if i < MIT_LANDESVARIANTEN else "bund", "fuer": "haushalt",
                           "voraussetzungen": [f"last_l{i - 16}"] if i >= 16 and i % 5 == 0 else []})
        teile = [bedingung((i * 7 + k) % FAKTEN) for k in range(6)]
        regel = {"alle": [teile[0], {"eine": teile[1:3]}, {"nicht": teile[3], "text": "Nicht erfüllt"}, *teile[4:]]}
        varianten.append({"id": f"last_v{i}_de", "leistung_id": f"last_l{i}", "gebiet_id": "DE", "regel": regel,
                          "zustaendigkeit_id": "last_stelle", "quellen": ["last_quelle"],
                          "verfahren": {"unterlagen": ["Ausweis"], "schritte": ["Antrag stellen"],
                                        "fristen": [{"text": "Binnen 3 Monaten", "bezug": "last.datum", "monate": 3}]}})
        if i < MIT_LANDESVARIANTEN:
            for land in LAENDER:
                varianten.append({"id": f"last_v{i}_{land}", "leistung_id": f"last_l{i}", "gebiet_id": land,
                                  "erbt_von": f"last_v{i}_de", "zustaendigkeit_id": "last_stelle"})
    fakten.append({"id": "last.datum", "typ": "datum", "frage": "Datum?"})
    return {
        "fachmodul": {"id": "last", "name": "Lasttest", "beschreibung": "Synthetisch"},
        "lebenslagen": [
            {"id": f"last_{i}", "name": f"Lage {i}", "typ": "situation", "beschreibung": "Synthetisch",
             "einstiegsfragen": [f"last.f{i * 3}"]}
            for i in range(LEBENSLAGEN)
        ],
        "fakten": fakten,
        "quellen": [{"id": "last_quelle", "titel": "Synthetisch", "url": None, "typ": "behoerde", "herausgeber": None,
                     "pruefstatus": "ungeprueft", "geprueft_am": None, "geprueft_von": None}],
        "zustaendigkeiten": [{"id": "last_stelle", "name": "Stelle – {land}"}],
        "leistungen": leistungen,
        "varianten": varianten,
    }


@pytest.fixture(scope="module")
def zielgroesse(tmp_path_factory) -> Path:
    ziel = tmp_path_factory.mktemp("last") / "data"
    shutil.copytree(STANDARD_DATENVERZEICHNIS, ziel)
    (ziel / "fachmodule" / "last").mkdir(parents=True)
    (ziel / "fachmodule" / "last" / "modul.json").write_text(json.dumps(_modul(), ensure_ascii=False), encoding="utf-8")
    return ziel


def _bestzeit(funktion, wiederholungen: int) -> tuple[float, Any]:
    """Kürzeste Laufzeit aus mehreren Läufen (robust gegen kurze Störungen auf CI-Rechnern)."""
    beste, ergebnis = float("inf"), None
    for _ in range(wiederholungen):
        start = time.perf_counter()
        ergebnis = funktion()
        beste = min(beste, time.perf_counter() - start)
    return beste, ergebnis


@pytest.mark.anforderung("ANF-DAT-14")
def test_zielgroesse_laden_und_planen(zielgroesse):
    dauer_laden, kb = _bestzeit(lambda: Wissensbasis.laden(zielgroesse), 2)
    assert len(kb.leistungen) >= 500 and len(kb.varianten) >= 5000 and len(kb.fakten) >= 600
    assert dauer_laden < 2.0, f"Laden dauerte {dauer_laden:.2f} s"

    lagen = ["geburt", "last_1", "last_2"]
    leer = Anfrage(fakten={}, plz="80331", lebenslagen=lagen, stichtag=date(2026, 10, 24))
    teilweise = Anfrage(
        fakten=fakten_parsen(kb, {f"last.f{i}": ("ja" if i % 3 == 0 else 5 if i % 3 == 1 else "a") for i in range(0, 300, 2)}
                             | {"kind_geboren": "nein", "errechneter_termin": "2026-12-15", "last.datum": "2026-10-01"}),
        plz="34225", lebenslagen=lagen, stichtag=date(2026, 10, 24),
    )
    for anfrage in (leer, teilweise):
        dauer, bericht = _bestzeit(lambda: planen(kb, anfrage), 5)
        assert len(bericht.eintraege) > 70  # 13 Geburt + rund 66 synthetische Leistungen
        assert dauer < 0.020, f"Bericht dauerte {dauer * 1000:.1f} ms"
