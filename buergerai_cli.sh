#!/bin/bash
# BuergerAI - Command Line Interface Wrapper
# 
# Einfacher Wrapper für den Python-CLI-Befehl
# 
# Usage:
#   ./buergerai_cli.sh                    # Interaktiver Modus
#   ./buergerai_cli.sh --plz 80331 --situationen Schwangerschaft
#   ./buergerai_cli.sh --help             # Hilfe anzeigen

# Projektverzeichnis
PROJECT_DIR="/workspace/github__uhrigjanis__BuergerAi"

# PYTHONPATH setzen
export PYTHONPATH="$PROJECT_DIR/src:$PYTHONPATH"

# Python-CLI aufrufen
exec python -m buergerai "$@"
