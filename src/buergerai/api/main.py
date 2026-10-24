"""
FastAPI Main Application for BuergerAi

API-Endpoints für die Frontend-Anbindung.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any, Optional
import uvicorn
import os

# Füge src zum Pfad hinzu
import sys
src_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from buergerai.core import Orchestrator
from buergerai.models import (
    Leistungsvariante, Gebiet
)

# App initialisieren
app = FastAPI(
    title="BuergerAI API",
    description="API für die Identifikation von Ansprüchen auf öffentliche Leistungen in Deutschland",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS-Middleware für Frontend-Anbindung
# Erlaube alle Ursprünge für Entwicklung, insbesondere GitHub Codespaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "https://*.githubpreview.dev",  # GitHub Codespaces
        "*",  # Erlaube alle Ursprünge (für Entwicklung)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Orchestrator initialisieren
orchestrator = Orchestrator()


# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Health Check Endpoint"""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "BuergerAI API"
    }


# ============================================================================
# Anfrage-Endpoints
# ============================================================================

class AnfrageRequest:
    """Request Model für eine BuergerAI-Anfrage"""
    
    def __init__(
        self,
        plz: str,
        lebenssituationen: List[str],
        profil: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ):
        self.plz = plz
        self.lebenssituationen = lebenssituationen
        self.profil = profil or {}
        self.session_id = session_id or "api_session"


@app.post("/api/anfrage")
async def process_anfrage(request: Request):
    """
    Verarbeitet eine Anfrage und gibt eine Checkliste zurück.
    
    Request Body:
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
    
    Returns:
        Checkliste mit allen relevanten Leistungen
    """
    try:
        body = await request.json()
        
        plz = body.get("plz")
        lebenssituationen = body.get("lebenssituationen", [])
        profil = body.get("profil", {})
        session_id = body.get("session_id", "api_session")
        
        if not plz:
            raise HTTPException(status_code=400, detail="PLZ ist erforderlich")
        
        if not lebenssituationen:
            raise HTTPException(status_code=400, detail="Mindestens eine Lebenssituation ist erforderlich")
        
        # Anfrage verarbeiten
        checkliste = orchestrator.process_request(
            session_id=session_id,
            plz=plz,
            lebenssituationen=lebenssituationen,
            profil_updates=profil
        )
        
        return JSONResponse(content={
            "erfolg": True,
            "checkliste": checkliste
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/anfrage/details")
async def process_anfrage_with_details(request: Request):
    """
    Verarbeitet eine Anfrage und gibt detaillierte Ergebnisse zurück.
    
    Returns:
        {
            "checkliste": [...],
            "zusammenfassung": {...},
            "profil": {...},
            "hierarchie": [...]
        }
    """
    try:
        body = await request.json()
        
        plz = body.get("plz")
        lebenssituationen = body.get("lebenssituationen", [])
        profil = body.get("profil", {})
        session_id = body.get("session_id", "api_session")
        
        if not plz:
            raise HTTPException(status_code=400, detail="PLZ ist erforderlich")
        
        if not lebenssituationen:
            raise HTTPException(status_code=400, detail="Mindestens eine Lebenssituation ist erforderlich")
        
        # Anfrage verarbeiten
        result = orchestrator.process_request_with_details(
            session_id=session_id,
            plz=plz,
            lebenssituationen=lebenssituationen,
            profil_updates=profil
        )
        
        return JSONResponse(content={
            "erfolg": True,
            **result
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/anfrage/markdown")
async def get_anfrage_markdown(
    plz: str,
    situationen: str = ""
):
    """
    Gibt die Checkliste als Markdown zurück.
    
    Query Parameters:
    - plz: Postleitzahl (z.B. 80331)
    - situationen: Komma-separierte Liste von Lebenssituationen (z.B. Schwangerschaft,Geburt)
    
    Returns:
        Markdown-String mit der Checkliste
    """
    try:
        lebenssituationen = [s.strip() for s in situationen.split(",") if s.strip()]
        
        if not lebenssituationen:
            raise HTTPException(status_code=400, detail="Mindestens eine Lebenssituation ist erforderlich")
        
        markdown = orchestrator.get_checkliste_markdown(
            session_id="api_session",
            plz=plz,
            lebenssituationen=lebenssituationen
        )
        
        return JSONResponse(content={
            "erfolg": True,
            "markdown": markdown
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Validierung-Endpoints
# ============================================================================

@app.post("/api/validate")
async def validate_anfrage(request: Request):
    """
    Validiert eine Anfrage.
    
    Request Body:
    {
        "plz": "80331",
        "lebenssituationen": ["Schwangerschaft"]
    }
    
    Returns:
        {
            "gueltig": true/false,
            "fehler": [...],
            "warnungen": [...]
        }
    """
    try:
        body = await request.json()
        
        plz = body.get("plz")
        lebenssituationen = body.get("lebenssituationen", [])
        
        result = orchestrator.validate_request(plz, lebenssituationen)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Gebiete-Endpoints
# ============================================================================

@app.get("/api/gebiete/plz/{plz}")
async def get_gebiet_by_plz(plz: str):
    """Holt das Gebiet für eine PLZ"""
    try:
        gebiet = orchestrator.gebiets_experte.get_gebiet_by_plz(plz)
        
        if not gebiet:
            raise HTTPException(status_code=404, detail=f"Kein Gebiet für PLZ {plz} gefunden")
        
        return JSONResponse(content={
            "erfolg": True,
            "gebiet": {
                "id": gebiet.id,
                "name": gebiet.name,
                "ebene": gebiet.ebene.value,
                "ags": gebiet.ags
            }
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gebiete/hierarchie/{plz}")
async def get_hierarchie(plz: str):
    """Holt die vollständige Gebietshierarchie für eine PLZ"""
    try:
        hierarchie = orchestrator.gebiets_experte.resolve_hierarchie(plz)
        
        return JSONResponse(content={
            "erfolg": True,
            "hierarchie": [
                {
                    "id": g.id,
                    "name": g.name,
                    "ebene": g.ebene.value,
                    "ags": g.ags
                }
                for g in hierarchie
            ]
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Leistungen-Endpoints
# ============================================================================

@app.get("/api/leistungen")
async def get_all_leistungen():
    """Holt alle Leistungen"""
    try:
        leistungen = orchestrator.leistungs_experte.get_all_leistungen()
        
        return JSONResponse(content={
            "erfolg": True,
            "leistungen": [
                {
                    "id": l.id,
                    "name": l.name,
                    "beschreibung": l.beschreibung,
                    "kurzbeschreibung": l.kurzbeschreibung,
                    "tags": [tag.name for tag in l.tags],
                    "kategorien": [kat.name for kat in l.kategorien]
                }
                for l in leistungen
            ]
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/leistungen/suche")
async def suche_leistungen(
    situationen: str = "",
    plz: Optional[str] = None
):
    """
    Sucht Leistungen nach Lebenssituationen.
    
    Query Parameters:
    - situationen: Komma-separierte Liste von Lebenssituationen
    - plz: Optionale PLZ für regionale Filterung
    """
    try:
        lebenssituationen = [s.strip() for s in situationen.split(",") if s.strip()]
        
        if not lebenssituationen:
            raise HTTPException(status_code=400, detail="Mindestens eine Lebenssituation ist erforderlich")
        
        # Hierarchie holen, falls PLZ angegeben
        hierarchie = None
        if plz:
            hierarchie = orchestrator.gebiets_experte.resolve_hierarchie(plz)
        
        varianten = orchestrator.leistungs_experte.suche_leistungen(
            lebenssituationen, hierarchie
        )
        
        return JSONResponse(content={
            "erfolg": True,
            "varianten": [
                {
                    "id": v.id,
                    "leistung_id": v.leistung_id,
                    "gebiet_id": v.gebiet_id,
                    "abdeckungsstatus": v.abdeckungsstatus.value,
                    "gueltig_ab": v.gueltig_ab.isoformat() if v.gueltig_ab else None,
                    "gueltig_bis": v.gueltig_bis.isoformat() if v.gueltig_bis else None
                }
                for v in varianten
            ]
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Server Start
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
