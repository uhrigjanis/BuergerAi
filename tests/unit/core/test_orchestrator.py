"""
Unit tests for Orchestrator
"""

import pytest
from datetime import date

from buergerai.models import (
    Gebiet, GebietsEbene, Leistung, Leistungskategorie, Leistungstag,
    Leistungsvariante, Abdeckungsstatus, Anspruchsregel, Bedingung, Operator,
    Verfahren, Zustaendigkeit
)
from buergerai.core import Orchestrator
from buergerai.knowledge_base import KnowledgeBase


class TestOrchestrator:
    """Tests für den Orchestrator"""
    
    @pytest.fixture
    def mock_kb(self):
        """Mock Knowledge Base mit Testdaten"""
        kb = KnowledgeBase()
        
        # Gebiete
        bund = Gebiet(
            id="bund",
            name="Deutschland",
            ebene=GebietsEbene.BUND,
            ags="00"
        )
        
        bayern = Gebiet(
            id="bayern",
            name="Bayern",
            ebene=GebietsEbene.LAND,
            ags="09",
            parent_id="bund",
            plz_bereich=["8", "9"]
        )
        
        muenchen = Gebiet(
            id="muenchen",
            name="München",
            ebene=GebietsEbene.GEMEINDE,
            ags="09176112",
            parent_id="bayern",
            plz_bereich=["80331", "80333"]
        )
        
        # Leistungen
        familien_kategorie = Leistungskategorie(
            id="familie",
            name="Familie"
        )
        
        geburt_tag = Leistungstag(id="geburt", name="Geburt")
        schwangerschaft_tag = Leistungstag(id="schwangerschaft", name="Schwangerschaft")
        
        elterngeld = Leistung(
            id="elterngeld",
            name="Elterngeld",
            beschreibung="Finanzielle Unterstützung für Eltern",
            kategorien=[familien_kategorie],
            tags=[geburt_tag, schwangerschaft_tag]
        )
        
        kindergeld = Leistung(
            id="kindergeld",
            name="Kindergeld",
            beschreibung="Finanzielle Unterstützung für Kinder",
            kategorien=[familien_kategorie],
            tags=[geburt_tag]
        )
        
        # Varianten
        elterngeld_bund = Leistungsvariante(
            id="elterngeld_bund",
            leistung_id="elterngeld",
            gebiet_id="bund",
            abdeckungsstatus=Abdeckungsstatus.VERIFIZIERT
        )
        
        kindergeld_bund = Leistungsvariante(
            id="kindergeld_bund",
            leistung_id="kindergeld",
            gebiet_id="bund",
            abdeckungsstatus=Abdeckungsstatus.VERIFIZIERT
        )
        
        # Regeln
        regel_elterngeld = Anspruchsregel(
            id="regel_elterngeld",
            name="Elterngeld-Berechtigung"
        )
        regel_elterngeld.add_bedingung(Bedingung(
            feld="situation.schwangerschaft.vorhanden",
            operator=Operator.EQUAL,
            wert=True,
            beschreibung="Schwangerschaft vorhanden"
        ))
        
        # Verfahren
        verfahren_elterngeld = Verfahren(
            id="verfahren_elterngeld",
            formular_link="https://example.com/elterngeld",
            bearbeitungsdauer_tage=20,
            frist_tage=7
        )
        
        # Zuständigkeit
        zustaendigkeit_elterngeld = Zustaendigkeit(
            id="zustaendigkeit_elterngeld",
            behoerde_name="Familienkasse Bayern"
        )
        
        # Daten einfügen
        kb.gebiet_repo._gebiete = {
            "bund": bund,
            "bayern": bayern,
            "muenchen": muenchen
        }
        kb.gebiet_repo._plz_index = {
            "80331": "muenchen",
            "80333": "muenchen"
        }
        kb.gebiet_repo._ags_index = {
            "00": "bund",
            "09": "bayern",
            "09176112": "muenchen"
        }
        kb.gebiet_repo._loaded = True
        
        kb.leistung_repo._leistungen = {
            "elterngeld": elterngeld,
            "kindergeld": kindergeld
        }
        kb.leistung_repo._varianten = {
            "elterngeld_bund": elterngeld_bund,
            "kindergeld_bund": kindergeld_bund
        }
        kb.leistung_repo._regeln = {
            "regel_elterngeld": regel_elterngeld
        }
        kb.leistung_repo._verfahren = {
            "verfahren_elterngeld": verfahren_elterngeld
        }
        kb.leistung_repo._zustaendigkeiten = {
            "zustaendigkeit_elterngeld": zustaendigkeit_elterngeld
        }
        kb.leistung_repo._leistung_varianten_index = {
            "elterngeld": ["elterngeld_bund"],
            "kindergeld": ["kindergeld_bund"]
        }
        kb.leistung_repo._gebiet_varianten_index = {
            "bund": ["elterngeld_bund", "kindergeld_bund"]
        }
        kb.leistung_repo._leistung_tags_index = {
            "Geburt": {"elterngeld", "kindergeld"},
            "Schwangerschaft": {"elterngeld"}
        }
        kb.leistung_repo._loaded = True
        
        return kb
    
    def test_process_request(self, mock_kb):
        """Test: Anfrage verarbeiten"""
        orchestrator = Orchestrator(knowledge_base=mock_kb)
        
        checkliste = orchestrator.process_request(
            session_id="session1",
            plz="80331",
            lebenssituationen=["Schwangerschaft"]
        )
        
        assert len(checkliste) >= 1
        
        # Sollte Elterngeld enthalten
        leistung_names = [e["leistung_name"] for e in checkliste]
        assert "Elterngeld" in leistung_names
    
    def test_process_request_with_profil_updates(self, mock_kb):
        """Test: Anfrage mit Profil-Updates verarbeiten"""
        orchestrator = Orchestrator(knowledge_base=mock_kb)
        
        profil_updates = {
            "situation": {
                "schwangerschaft": {
                    "vorhanden": True
                }
            }
        }
        
        checkliste = orchestrator.process_request(
            session_id="session1",
            plz="80331",
            lebenssituationen=["Schwangerschaft"],
            profil_updates=profil_updates
        )
        
        assert len(checkliste) >= 1
    
    def test_process_request_with_details(self, mock_kb):
        """Test: Anfrage mit Details verarbeiten"""
        orchestrator = Orchestrator(knowledge_base=mock_kb)
        
        result = orchestrator.process_request_with_details(
            session_id="session1",
            plz="80331",
            lebenssituationen=["Schwangerschaft"]
        )
        
        assert "checkliste" in result
        assert "zusammenfassung" in result
        assert "profil" in result
        assert "hierarchie" in result
        
        assert len(result["checkliste"]) >= 1
        assert len(result["hierarchie"]) == 3  # Bund, Bayern, München
    
    def test_get_checkliste_markdown(self, mock_kb):
        """Test: Checkliste als Markdown holen"""
        orchestrator = Orchestrator(knowledge_base=mock_kb)
        
        markdown = orchestrator.get_checkliste_markdown(
            session_id="session1",
            plz="80331",
            lebenssituationen=["Schwangerschaft"]
        )
        
        assert len(markdown) > 0
        assert "#" in markdown  # Titel
        assert "Elterngeld" in markdown
    
    def test_validate_request_valid(self, mock_kb):
        """Test: Gültige Anfrage validieren"""
        orchestrator = Orchestrator(knowledge_base=mock_kb)
        
        result = orchestrator.validate_request(
            plz="80331",
            lebenssituationen=["Schwangerschaft"]
        )
        
        assert result["gueltig"] is True
        assert len(result["fehler"]) == 0
    
    def test_validate_request_invalid_plz(self, mock_kb):
        """Test: Ungültige PLZ validieren"""
        orchestrator = Orchestrator(knowledge_base=mock_kb)
        
        result = orchestrator.validate_request(
            plz="99999",
            lebenssituationen=["Schwangerschaft"]
        )
        
        assert result["gueltig"] is False
        assert len(result["fehler"]) == 1
    
    def test_validate_request_no_situations(self, mock_kb):
        """Test: Keine Lebenssituationen validieren"""
        orchestrator = Orchestrator(knowledge_base=mock_kb)
        
        result = orchestrator.validate_request(
            plz="80331",
            lebenssituationen=[]
        )
        
        assert result["gueltig"] is False
        assert len(result["fehler"]) == 1
