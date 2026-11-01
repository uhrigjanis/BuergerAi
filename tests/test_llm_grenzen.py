"""Grenzen der LLM-Schicht, die schon vor dem Adapter gelten (ADR 0009)."""

import ast
import re
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]
SRC = WURZEL / "src" / "buergerai"
LLM_PAKET = SRC / "llm"
ANBIETER = {"anthropic", "mistralai", "google", "vertexai", "boto3", "openai", "ollama", "httpx", "httpx2", "requests"}


def _importe(baum):
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            yield knoten, [a.name.split(".")[0] for a in knoten.names]
        elif isinstance(knoten, ast.ImportFrom) and knoten.module and knoten.level == 0:
            yield knoten, [knoten.module.split(".")[0]]


@pytest.mark.anforderung("ANF-LLM-01")
def test_keine_laufzeitabhaengigkeiten():
    text = (WURZEL / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r"^dependencies\s*=\s*\[\s*\]", text, re.M), "dependencies muss leer bleiben (ADR 0002, ADR 0009)"


@pytest.mark.anforderung("ANF-LLM-01")
def test_anbieterpakete_nur_im_adapter_und_nicht_beim_laden():
    falsch = []
    for datei in sorted(SRC.rglob("*.py")):
        baum = ast.parse(datei.read_text(encoding="utf-8"))
        oben = {id(k) for k in baum.body}
        im_adapter = LLM_PAKET in datei.parents
        for knoten, namen in _importe(baum):
            for name in namen:
                if name not in ANBIETER:
                    continue
                if not im_adapter or id(knoten) in oben:
                    falsch.append(f"{datei.relative_to(WURZEL)}:{knoten.lineno} {name}")
    assert falsch == []
