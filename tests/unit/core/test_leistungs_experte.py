"""
Unit tests for LeistungsExperte
"""

import pytest
from datetime import date

from buergerai.models import (
    Leistung, Leistungskategorie, Leistungstag, Leistungsvariante,
    Abdeckungsstatus
)
from buergerai.core.experten import LeistungsExperte
from buergerai.knowledge_base import KnowledgeBase


class TestLeistungsExperte:
    """Tests für den LeistungsExperten"""
    
    @pytest.fixture
    def mock_kb(self):
        """Mock Knowledge Base mit Testdaten"""
        kb = KnowledgeBase()
        
        # Testdaten manuell einfügen
        familien_kategorie = Leistungskategorie(
            id="familie",
            name="Familie",
            beschreibung="Familienleistungen"
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
        
        elterngeld_bayern = Leistungsvariante(
            id="elterngeld_bayern",
            leistung_id="elterngeld",
            gebiet_id="bayern",
            abdeckungsstatus=Abdeckungsstatus.LANDESEBENE
        )
        
        kindergeld_bund = Leistungsvariante(
            id="kindergeld_bund",
            leistung_id="kindergeld",
            gebiet_id="bund",
            abdeckungsstatus=Abdeckungsstatus.VERIFIZIERT
        )
        
        # In die Knowledge Base einfügen
        kb.leistung_repo._leistungen = {
            "elterngeld": elterngeld,
            "kindergeld": kindergeld
        }
        kb.leistung_repo._varianten = {
            "elterngeld_bund": elterngeld_bund,
            "elterngeld_bayern": elterngeld_bayern,
            "kindergeld_bund": kindergeld_bund
        }
        kb.leistung_repo._leistung_varianten_index = {
            "elterngeld": ["elterngeld_bund", "elterngeld_bayern"],
            "kindergeld": ["kindergeld_bund"]
        }
        kb.leistung_repo._gebiet_varianten_index = {
            "bund": ["elterngeld_bund", "kindergeld_bund"],
            "bayern": ["elterngeld_bayern"]
        }
        kb.leistung_repo._leistung_tags_index = {
            "Geburt": {"elterngeld", "kindergeld"},
            "Schwangerschaft": {"elterngeld"}
        }
        kb.leistung_repo._loaded = True
        
        return kb
    
    def test_suche_leistungen_by_tag(self, mock_kb):
        """Test: Leistungen nach Tag suchen"""
        experte = LeistungsExperte(mock_kb)
        
        varianten = experte.suche_leistungen(["Geburt"])
        
        assert len(varianten) == 3  # elterngeld_bund, elterngeld_bayern, kindergeld_bund
    
    def test_suche_leistungen_by_multiple_tags(self, mock_kb):
        """Test: Leistungen nach mehreren Tags suchen"""
        experte = LeistungsExperte(mock_kb)
        
        varianten = experte.suche_leistungen(["Geburt", "Schwangerschaft"])
        
        # Nur Elterngeld hat beide Tags
        assert len(varianten) == 2  # elterngeld_bund, elterngeld_bayern
    
    def test_get_leistung_by_id(self, mock_kb):
        """Test: Leistung für ID holen"""
        experte = LeistungsExperte(mock_kb)
        
        leistung = experte.get_leistung_by_id("elterngeld")
        
        assert leistung is not None
        assert leistung.name == "Elterngeld"
    
    def test_get_leistung_by_name(self, mock_kb):
        """Test: Leistung für Namen holen"""
        experte = LeistungsExperte(mock_kb)
        
        leistung = experte.get_leistung_by_name("Elterngeld")
        
        assert leistung is not None
        assert leistung.id == "elterngeld"
    
    def test_get_varianten_for_leistung(self, mock_kb):
        """Test: Varianten für Leistung holen"""
        experte = LeistungsExperte(mock_kb)
        
        varianten = experte.get_varianten_for_leistung("elterngeld")
        
        assert len(varianten) == 2
        assert varianten[0].id in ["elterngeld_bund", "elterngeld_bayern"]
    
    def test_get_varianten_for_gebiet(self, mock_kb):
        """Test: Varianten für Gebiet holen"""
        experte = LeistungsExperte(mock_kb)
        
        varianten = experte.get_varianten_for_gebiet("bund")
        
        assert len(varianten) == 2
    
    def test_filter_by_abdeckungsstatus(self, mock_kb):
        """Test: Varianten nach Abdeckungsstatus filtern"""
        experte = LeistungsExperte(mock_kb)
        
        alle_varianten = experte.get_all_varianten()
        
        verifiziert = experte.filter_by_abdeckungsstatus(
            alle_varianten, Abdeckungsstatus.VERIFIZIERT
        )
        
        assert len(verifiziert) == 2  # elterngeld_bund, kindergeld_bund
    
    def test_filter_gueltig(self, mock_kb):
        """Test: Varianten nach Gültigkeit filtern"""
        experte = LeistungsExperte(mock_kb)
        
        alle_varianten = experte.get_all_varianten()
        
        gueltig = experte.filter_gueltig(alle_varianten)
        
        assert len(gueltig) == 3  # Alle sind gültig
    
    def test_get_leistung_tags(self, mock_kb):
        """Test: Tags einer Leistung holen"""
        experte = LeistungsExperte(mock_kb)
        
        leistung = experte.get_leistung_by_id("elterngeld")
        tags = experte.get_leistung_tags(leistung)
        
        assert len(tags) == 2
        assert "Geburt" in tags
        assert "Schwangerschaft" in tags
    
    def test_get_leistung_kategorien(self, mock_kb):
        """Test: Kategorien einer Leistung holen"""
        experte = LeistungsExperte(mock_kb)
        
        leistung = experte.get_leistung_by_id("elterngeld")
        kategorien = experte.get_leistung_kategorien(leistung)
        
        assert len(kategorien) == 1
        assert "Familie" in kategorien
