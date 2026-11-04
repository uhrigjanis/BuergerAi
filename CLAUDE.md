# Hinweise für Claude Code

- Arbeit an der Web-Oberfläche (`src/buergerai/web/static/`) folgt der Design-Richtlinie [`docs/design/ClaudeDesign.md`](docs/design/ClaudeDesign.md). Die Umsetzung und die Abweichungen für Barrierefreiheit stehen in ADR 0006, Nachtrag #99.
- Farben nur als Tokens in `:root` von `style.css`. Sonst überall `var(--…)` (Test: `tests/test_web_design.py`).
- Kein Framework, kein Build-Schritt, keine externen Ressourcen (ADR 0006). Keine Laufzeit-Abhängigkeiten (ADR 0002).
- Tests: `python -m pytest`. Browser-Rauchtest: `PYTHONPATH=src:tests python scripts/web_rauchtest.py` (in GitHub der Check „Web-Oberfläche“, `.github/workflows/web.yml`).
