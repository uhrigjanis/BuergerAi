#!/usr/bin/env bash
# Legt eine virtuelle Umgebung an, installiert BürgerAI (editierbar), pytest und
# pyflakes und führt einmal dieselben Prüfungen aus wie die CI (.github/workflows/tests.yml).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python3 -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10+ nötig"'
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e ".[dev]"
echo "== Datenprüfung";      .venv/bin/buergerai daten
echo "== Szenarien";         .venv/bin/buergerai szenarien --pruefen
echo "== Anforderungen";     .venv/bin/buergerai anforderungen | tail -1
echo "== pyflakes";          .venv/bin/python -m pyflakes src tests scripts
echo "== Tests";             .venv/bin/python -m pytest
echo
echo "Fertig. Web-Oberfläche: ./bai web   ·   Terminal-Dialog: ./bai   (oder: source .venv/bin/activate && buergerai)"
