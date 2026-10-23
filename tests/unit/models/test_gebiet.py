"""
Unit tests for Gebiet model
"""

import pytest
from datetime import date

from buergerai.models import Gebiet, GebietsEbene


class TestGebiet:
    """Tests für das Gebiet-Modell"""
    
    def test_create_bund(self):
        """Test: Erstellen des Bundes"""
        bund = Gebiet(
            id="bund",
            name="Deutschland",
            ebene=GebietsEbene.BUND,
            ags="00"
        )
        
        assert bund.id == "bund"
        assert bund.name == "Deutschland"
        assert bund.ebene == GebietsEbene.BUND
        assert bund.ags == "00"
        assert bund.parent_id is None
    
    def test_create_land(self):
        """Test: Erstellen eines Bundeslandes"""
        bayern = Gebiet(
            id="bayern",
            name="Bayern",
            ebene=GebietsEbene.LAND,
            ags="09",
            parent_id="bund"
        )
        
        assert bayern.id == "bayern"
        assert bayern.name == "Bayern"
        assert bayern.ebene == GebietsEbene.LAND
        assert bayern.ags == "09"
        assert bayern.parent_id == "bund"
    
    def test_create_gemeinde(self):
        """Test: Erstellen einer Gemeinde"""
        muenchen = Gebiet(
            id="muenchen",
            name="München",
            ebene=GebietsEbene.GEMEINDE,
            ags="09176112",
            parent_id="bayern",
            plz_bereich=["80331", "80333", "80335"]
        )
        
        assert muenchen.id == "muenchen"
        assert muenchen.name == "München"
        assert muenchen.ebene == GebietsEbene.GEMEINDE
        assert muenchen.ags == "09176112"
        assert muenchen.parent_id == "bayern"
        assert "80331" in muenchen.plz_bereich
    
    def test_bund_cannot_have_parent(self):
        """Test: Bund darf keinen parent_id haben"""
        with pytest.raises(ValueError, match="Bund darf kein parent_id haben"):
            Gebiet(
                id="bund",
                name="Deutschland",
                ebene=GebietsEbene.BUND,
                ags="00",
                parent_id="some_parent"
            )
    
    def test_bund_must_have_ags_00(self):
        """Test: Bund muss AGS '00' haben"""
        with pytest.raises(ValueError, match="Bund muss AGS '00' haben"):
            Gebiet(
                id="bund",
                name="Deutschland",
                ebene=GebietsEbene.BUND,
                ags="01"
            )
    
    def test_ist_gueltig_current(self):
        """Test: Gültigkeit für aktuelles Datum"""
        gebiet = Gebiet(
            id="test",
            name="Test",
            ebene=GebietsEbene.LAND,
            ags="99",
            gueltig_ab=date(2020, 1, 1)
        )
        
        assert gebiet.ist_gueltig() is True
    
    def test_ist_gueltig_future(self):
        """Test: Gültigkeit für zukünftiges Datum"""
        gebiet = Gebiet(
            id="test",
            name="Test",
            ebene=GebietsEbene.LAND,
            ags="99",
            gueltig_ab=date(2050, 1, 1)
        )
        
        assert gebiet.ist_gueltig() is False
    
    def test_ist_gueltig_past(self):
        """Test: Gültigkeit für vergangenes Datum"""
        gebiet = Gebiet(
            id="test",
            name="Test",
            ebene=GebietsEbene.LAND,
            ags="99",
            gueltig_ab=date(2000, 1, 1),
            gueltig_bis=date(2020, 1, 1)
        )
        
        assert gebiet.ist_gueltig() is False
    
    def test_ist_gueltig_specific_date(self):
        """Test: Gültigkeit für spezifisches Datum"""
        gebiet = Gebiet(
            id="test",
            name="Test",
            ebene=GebietsEbene.LAND,
            ags="99",
            gueltig_ab=date(2020, 1, 1),
            gueltig_bis=date(2025, 12, 31)
        )
        
        assert gebiet.ist_gueltig(date(2022, 6, 15)) is True
        assert gebiet.ist_gueltig(date(2019, 12, 31)) is False
        assert gebiet.ist_gueltig(date(2026, 1, 1)) is False
    
    def test_get_hierarchie_pfad(self):
        """Test: Hierarchie-Pfad abrufen"""
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
            parent_id="bund"
        )
        
        muenchen = Gebiet(
            id="muenchen",
            name="München",
            ebene=GebietsEbene.GEMEINDE,
            ags="09176112",
            parent_id="bayern"
        )
        
        alle_gebiete = [bund, bayern, muenchen]
        
        hierarchie = muenchen.get_hierarchie_pfad(alle_gebiete)
        
        assert len(hierarchie) == 3
        assert hierarchie[0].id == "bund"
        assert hierarchie[1].id == "bayern"
        assert hierarchie[2].id == "muenchen"
