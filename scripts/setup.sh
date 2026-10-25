#!/usr/bin/env bash
# Legt eine virtuelle Umgebung an, installiert BürgerAI (editierbar) und pytest
# und führt einmal alle Prüfungen aus.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python3 -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10+ nötig"'
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e ".[dev]"
echo "== Datenprüfung";      .venv/bin/buergerai daten
echo "== Tests";             .venv/bin/python -m pytest
echo "== Szenarien";         .venv/bin/buergerai szenarien --pruefen
echo
echo "Fertig. Web-Oberfläche: ./bai web   ·   Terminal-Dialog: ./bai   (oder: source .venv/bin/activate && buergerai)"
