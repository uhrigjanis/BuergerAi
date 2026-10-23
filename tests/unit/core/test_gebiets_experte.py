"""
Unit tests for GebietsExperte
"""

import pytest
from datetime import date

from buergerai.models import Gebiet, GebietsEbene
from buergerai.core.experten import GebietsExperte
from buergerai.knowledge_base import KnowledgeBase


class TestGebietsExperte:
    """Tests für den GebietsExperten"""
    
    @pytest.fixture
    def mock_kb(self):
        """Mock Knowledge Base mit Testdaten"""
        kb = KnowledgeBase()
        
        # Testdaten manuell einfügen
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
            plz_bereich=["80331", "80333", "80335"]
        )
        
        # In die Knowledge Base einfügen
        kb.gebiet_repo._gebiete = {
            "bund": bund,
            "bayern": bayern,
            "muenchen": muenchen
        }
        kb.gebiet_repo._plz_index = {
            "80331": "muenchen",
            "80333": "muenchen",
            "80335": "muenchen"
        }
        kb.gebiet_repo._ags_index = {
            "00": "bund",
            "09": "bayern",
            "09176112": "muenchen"
        }
        kb.gebiet_repo._loaded = True
        
        return kb
    
    def test_resolve_hierarchie_muenchen(self, mock_kb):
        """Test: Hierarchie für München auflösen"""
        experte = GebietsExperte(mock_kb)
        
        hierarchie = experte.resolve_hierarchie("80331")
        
        assert len(hierarchie) == 3
        assert hierarchie[0].id == "bund"
        assert hierarchie[1].id == "bayern"
        assert hierarchie[2].id == "muenchen"
    
    def test_resolve_hierarchie_unknown_plz(self, mock_kb):
        """Test: Hierarchie für unbekannte PLZ"""
        experte = GebietsExperte(mock_kb)
        
        hierarchie = experte.resolve_hierarchie("99999")
        
        # Sollte Fallback auf Bund sein
        assert len(hierarchie) == 1
        assert hierarchie[0].id == "bund"
    
    def test_get_gebiet_by_plz(self, mock_kb):
        """Test: Gebiet für PLZ holen"""
        experte = GebietsExperte(mock_kb)
        
        gebiet = experte.get_gebiet_by_plz("80331")
        
        assert gebiet is not None
        assert gebiet.id == "muenchen"
    
    def test_get_gebiet_by_ags(self, mock_kb):
        """Test: Gebiet für AGS holen"""
        experte = GebieteExperte(mock_kb)
        
        gebiet = experte.get_gebiet_by_ags("09")
        
        assert gebiet is not None
        assert gebiet.id == "bayern"
    
    def test_get_gebiet_by_id(self, mock_kb):
        """Test: Gebiet für ID holen"""
        experte = GebietsExperte(mock_kb)
        
        gebiet = experte.get_gebiet_by_id("muenchen")
        
        assert gebiet is not None
        assert gebiet.id == "muenchen"
    
    def test_validate_plz_valid(self, mock_kb):
        """Test: Gültige PLZ validieren"""
        experte = GebietsExperte(mock_kb)
        
        assert experte.validate_plz("80331") is True
    
    def test_validate_plz_invalid(self, mock_kb):
        """Test: Ungültige PLZ validieren"""
        experte = GebietsExperte(mock_kb)
        
        assert experte.validate_plz("99999") is False
    
    def test_get_ebene(self, mock_kb):
        """Test: Ebene eines Gebiets holen"""
        experte = GebietsExperte(mock_kb)
        
        bund = experte.get_gebiet_by_id("bund")
        bayern = experte.get_gebiet_by_id("bayern")
        
        assert experte.get_ebene(bund) == GebietsEbene.BUND
        assert experte.get_ebene(bayern) == GebietsEbene.LAND
    
    def test_get_parent(self, mock_kb):
        """Test: Übergeordnetes Gebiet holen"""
        experte = GebietsExperte(mock_kb)
        
        muenchen = experte.get_gebiet_by_id("muenchen")
        parent = experte.get_parent(muenchen)
        
        assert parent is not None
        assert parent.id == "bayern"
    
    def test_get_parent_bund(self, mock_kb):
        """Test: Übergeordnetes Gebiet des Bundes"""
        experte = GebietsExperte(mock_kb)
        
        bund = experte.get_gebiet_by_id("bund")
        parent = experte.get_parent(bund)
        
        assert parent is None
    
    def test_get_all_gebiete(self, mock_kb):
        """Test: Alle Gebiete holen"""
        experte = GebietsExperte(mock_kb)
        
        alle_gebiete = experte.get_all_gebiete()
        
        assert len(alle_gebiete) == 3
    
    def test_get_by_ebene(self, mock_kb):
        """Test: Gebiete nach Ebene filtern"""
        experte = GebietsExperte(mock_kb)
        
        laender = experte.get_by_ebene(GebietsEbene.LAND)
        
        assert len(laender) == 1
        assert laender[0].id == "bayern"
