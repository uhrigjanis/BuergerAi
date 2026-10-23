# BuergerAI

Eine KI-gestützte Anwendung zur Identifikation von Ansprüchen auf öffentliche Leistungen in Deutschland. BuergerAI hilft Bürgern, alle Leistungen zu finden, die ihnen in ihrer aktuellen Lebenssituation zustehen.

## 📋 Übersicht

BuergerAI ist ein deterministisches, regelbasiertes System, das ohne LLM (Large Language Models) arbeitet. Es basiert auf offiziellen Daten und Regeln aus deutschen Behörden.

### Hauptmerkmale

- ✅ **Deterministische Logik**: Keine LLM-basierten Entscheidungen für die Anspruchsprüfung
- ✅ **Regionale Unterstützung**: Berücksichtigt Bundes-, Landes-, Kreis- und Gemeindeebene
- ✅ **Nachvollziehbarkeit**: Jedes Ergebnis ist mit Quellen und Gültigkeitszeiträumen verknüpft
- ✅ **Skalierbar**: Unterstützt 11.000+ Gemeinden in Deutschland
- ✅ **DSGVO-konform**: Keine dauerhafte Speicherung sensibler Daten
- ✅ **EU-Hosting**: Geeignet für europäische LLMs (Aleph Alpha, Mistral)

## 🚀 Schnellstart

### Voraussetzungen

- Python 3.10+
- Node.js 18+ (für Frontend-Entwicklung)
- pip (Python Package Manager)
- npm oder yarn (Node Package Manager)

### Installation

#### Backend

```bash
# Repository klonen
cd /workspace/github__uhrigjanis__BuergerAi

# Python-Abhängigkeiten installieren
pip install -e .
pip install fastapi uvicorn

# Umgebungsvariable setzen (für Entwicklung)
export PYTHONPATH=/workspace/github__uhrigjanis__BuergerAi/src
```

#### Frontend

```bash
# In das Frontend-Verzeichnis wechseln
cd frontend

# Node.js-Abhängigkeiten installieren
npm install

# Umgebungsvariable für API-URL setzen
cp .env.local.example .env.local
```

## 🏃‍♂️ Anwendung starten

### Backend (FastAPI) starten

```bash
cd /workspace/github__uhrigjanis__BuergerAi
export PYTHONPATH=/workspace/github__uhrigjanis__BuergerAi/src
uvicorn buergerai.api.main:app --reload --port 8000
```

Das Backend ist unter `http://localhost:8000` erreichbar.

- API-Dokumentation: `http://localhost:8000/api/docs`
- Health Check: `http://localhost:8000/api/health`

### Frontend (Next.js) starten

```bash
cd frontend
npm run dev
```

Das Frontend ist unter `http://localhost:3000` erreichbar.

## 🧪 Testen

### Backend-Tests

```bash
cd /workspace/github__uhrigjanis__BuergerAi
export PYTHONPATH=/workspace/github__uhrigjanis__BuergerAi/src
python -m pytest tests/unit/ -v
```

### Frontend-Tests

```bash
cd frontend
npm test
```

### Manuelles Testen über Terminal

#### CLI verwenden

```bash
# CLI-Hilfe anzeigen
export PYTHONPATH=/workspace/github__uhrigjanis__BuergerAi/src
python -m buergerai.cli --help

# Interaktiver Modus
python -m buergerai.cli

# Direkte Anfrage
python -m buergerai.cli --plz 80331 --situationen Schwangerschaft,Geburt

# Markdown-Ausgabe
python -m buergerai.cli --plz 80331 --situationen Schwangerschaft --format markdown

# JSON-Ausgabe
python -m buergerai.cli --plz 80331 --situationen Schwangerschaft --format json
```

#### API-Endpoints testen

```bash
# Health Check
curl http://localhost:8000/api/health

# Anfrage stellen
curl -X POST http://localhost:8000/api/anfrage \
  -H "Content-Type: application/json" \
  -d '{"plz": "80331", "lebenssituationen": ["Schwangerschaft", "Geburt"]}'

# Detaillierte Anfrage
curl -X POST http://localhost:8000/api/anfrage/details \
  -H "Content-Type: application/json" \
  -d '{"plz": "80331", "lebenssituationen": ["Schwangerschaft"]}'

# Gebietshierarchie abrufen
curl http://localhost:8000/api/gebiete/hierarchie/80331

# Leistungen suchen
curl "http://localhost:8000/api/leistungen/suche?situationen=Schwangerschaft"
```

## 📦 Projektstruktur

```
buergerai/
├── src/
│   └── buergerai/
│       ├── __init__.py
│       ├── models/              # Datenmodelle
│       │   ├── __init__.py
│       │   ├── gebiet.py        # Gebietsmodell (Bund, Land, Kreis, Gemeinde)
│       │   ├── leistung.py      # Leistungsmodell
│       │   ├── leistungsvariante.py
│       │   ├── anspruch.py      # Anspruchsregeln und Bedingungen
│       │   ├── verfahren.py     # Verfahrensmodell
│       │   ├── zustaendigkeit.py # Zuständigkeitsmodell
│       │   └── quelle.py        # Quellenmodell
│       │
│       ├── knowledge_base/     # Wissensbasis
│       │   ├── __init__.py
│       │   ├── knowledge_base.py
│       │   ├── gebiet_repository.py
│       │   └── leistung_repository.py
│       │
│       ├── core/                # Kernlogik
│       │   ├── __init__.py
│       │   ├── experten/         # Experten-Architektur
│       │   │   ├── __init__.py
│       │   │   ├── gebiets_experte.py
│       │   │   ├── leistungs_experte.py
│       │   │   ├── profil_experte.py
│       │   │   ├── anspruchs_experte.py
│       │   │   ├── verfahrens_experte.py
│       │   │   ├── abhaengigkeits_experte.py
│       │   │   └── ausgabe_experte.py
│       │   └── orchestrator.py   # Orchestrator
│       │
│       ├── api/                 # REST API
│       │   ├── __init__.py
│       │   └── main.py          # FastAPI-Anwendung
│       │
│       └── cli.py               # Command-Line Interface
│
├── data/                        # Testdaten
│   ├── gebiete/
│   │   └── bayern.json
│   ├── leistungen/
│   │   ├── leistungen.json
│   │   └── varianten.json
│   ├── regeln/
│   │   └── regeln.json
│   ├── verfahren/
│   │   └── verfahren.json
│   ├── zustaendigkeiten/
│   │   └── zustaendigkeiten.json
│   └── quellen/
│       └── quellen.json
│
├── frontend/                    # Next.js Frontend
│   ├── app/
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── __init__.py
│   │   ├── IntakeForm.tsx
│   │   └── ChecklistView.tsx
│   ├── lib/
│   │   ├── __init__.py
│   │   └── api.ts
│   ├── types/
│   │   └── index.ts
│   ├── package.json
│   ├── next.config.js
│   └── tsconfig.json
│
├── tests/                       # Tests
│   └── unit/
│       ├── models/
│       └── core/
│
├── Dockerfile                  # Docker-Konfiguration
├── Dockerfile.backend        # Backend-Dockerfile
├── Dockerfile.frontend        # Frontend-Dockerfile
├── docker-compose.yml          # Docker Compose
├── pyproject.toml              # Python-Projektkonfiguration
├── requirements.txt            # Python-Abhängigkeiten
└── README.md                   # Diese Datei
```

## 🎯 Phasenplan

### Phase 1: Wissenskern (abgeschlossen ✅)

- Datenmodelle implementiert
- Wissensbasis mit Repositories
- Experten-Architektur (7 Experten)
- Orchestrator für Workflow-Koordination
- CLI für Terminal-Nutzung
- Unit-Tests für alle Komponenten

### Phase 2: Nutzbarer Stand (in Arbeit 🚧)

- FastAPI-Backend mit REST-Endpoints
- Next.js-Frontend mit React und TypeScript
- Formular für PLZ- und Situations-Eingabe
- Checklisten-Ansicht mit Filterfunktionen
- Docker-Konfiguration für lokale Entwicklung

### Phase 3: Erweiterungen (geplant 📅)

- PostgreSQL-Datenbank für persistente Speicherung
- Neo4j für Graph-basierte Abhängigkeitsanalyse
- Optionale LLM-Integration (Aleph Alpha, Mistral)
- Erweitertes Profilmanagement
- Benutzerauthentifizierung (optional)

## 🔧 API-Dokumentation

### Endpoints

#### Health Check
```
GET /api/health
```

#### Anfragen
```
POST /api/anfrage              # Einfache Checkliste
POST /api/anfrage/details     # Detaillierte Ergebnisse
GET  /api/anfrage/markdown    # Markdown-Ausgabe
POST /api/validate            # Anfrage validieren
```

#### Gebiete
```
GET /api/gebiete/plz/{plz}     # Gebiet by PLZ
GET /api/gebiete/hierarchie/{plz}  # Komplette Hierarchie
```

#### Leistungen
```
GET /api/leistungen            # Alle Leistungen
GET /api/leistungen/suche     # Suche nach Situation
```

### Request-Format

```json
{
  "plz": "80331",
  "lebenssituationen": ["Schwangerschaft", "Geburt"],
  "profil": {
    "haushalt": {
      "antragstellerin": {
        "alter": 30,
        "einkommen_jaehrlich": 50000
      },
      "kinder": []
    },
    "situation": {
      "schwangerschaft": {"vorhanden": true},
      "geburt": {"vorhanden": true}
    }
  }
}
```

### Response-Format

```json
{
  "erfolg": true,
  "checkliste": [
    {
      "leistung_id": "elterngeld",
      "leistung_name": "Elterngeld",
      "variante_id": "elterngeld_bayern",
      "anspruch": "ja",
      "begründung": ["Schwangerschaft vorhanden"],
      "zustaendigkeit": {
        "behoerde_name": "Landratsamt München",
        "portal_link": "https://..."
      },
      "frist_tage": 30,
      "unterlagen": [...],
      "schritte": [...],
      "bearbeitungsdauer_tage": 14,
      "koste": 0,
      "quellen": ["§16 BEEG"],
      "abdeckungsstatus": "verifiziert"
    }
  ],
  "zusammenfassung": {
    "statistik": {
      "gesamt": 10,
      "anspruch_ja": 8,
      "anspruch_unklar": 1,
      "anspruch_nein": 1,
      "dringend": 2
    },
    "naechste_schritte": [...],
    "gesamt_bearbeitungsdauer_tage": 42
  },
  "hierarchie": [...]
}
```

## 📊 Unterstützte Lebenssituationen

- Schwangerschaft
- Geburt
- Heirat
- Trennung / Scheidung
- Tod
- Arbeitslosigkeit
- Erkrankung / Schwerbehinderung
- Pflege
- Umzug
- Ausbildung
- Renteneintritt
- Adoption
- Elternzeit
- Kinderbetreuung
- Wohnungssuche
- Insolvenz

## 🔒 Datenschutz

- **Keine Speicherung**: Alle Daten werden nur für die Dauer der Session gespeichert
- **Anonymisierung**: Keine persönlichen Daten werden dauerhaft gespeichert
- **DSGVO-konform**: Vollständige Einhaltung der DSGVO-Vorgaben
- **EU-Hosting**: Alle Daten bleiben in der EU

## 🤝 Mitwirken

### Beitragen

1. Repository forken
2. Feature-Branch erstellen (`git checkout -b feature/neue-funktion`)
3. Änderungen commiten (`git commit -m 'Neue Funktion hinzugefügt'`)
4. Pushen (`git push origin feature/neue-funktion`)
5. Pull Request erstellen

### Testen

- Alle Änderungen müssen mit Unit-Tests abgedeckt sein
- Backend: `pytest tests/unit/`
- Frontend: `npm test`

### Code-Qualität

- Black für Code-Formatierung
- isort für Import-Sortierung
- mypy für Typenprüfung

```bash
# Code formatieren
black src/ tests/

# Imports sortieren
isort src/ tests/

# Typen prüfen
mypy src/
```

## 📄 Lizenz

MIT License - Siehe [LICENSE](LICENSE) für Details.

## 📞 Kontakt

- **Repository**: [github.com/uhrigjanis/BuergerAi](https://github.com/uhrigjanis/BuergerAi)
- **Issues**: [GitHub Issues](https://github.com/uhrigjanis/BuergerAi/issues)

---

**BuergerAI** - Einfacher Zugang zu öffentlichen Leistungen in Deutschland
