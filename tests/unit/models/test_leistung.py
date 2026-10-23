"""
Unit tests for Leistung model
"""

import pytest
from datetime import date

from buergerai.models import Leistung, Leistungskategorie, Leistungstag


class TestLeistung:
    """Tests für das Leistung-Modell"""
    
    def test_create_leistung(self):
        """Test: Erstellen einer Leistung"""
        leistung = Leistung(
            id="elterngeld",
            name="Elterngeld",
            beschreibung="Finanzielle Unterstützung für Eltern",
            kurzbeschreibung="Geld für Eltern"
        )
        
        assert leistung.id == "elterngeld"
        assert leistung.name == "Elterngeld"
        assert leistung.beschreibung == "Finanzielle Unterstützung für Eltern"
        assert leistung.kurzbeschreibung == "Geld für Eltern"
    
    def test_add_kategorie(self):
        """Test: Kategorie hinzufügen"""
        leistung = Leistung(
            id="elterngeld",
            name="Elterngeld"
        )
        
        kategorie = Leistungskategorie(
            id="familie",
            name="Familie",
            beschreibung="Familienleistungen"
        )
        
        leistung.add_kategorie(kategorie)
        
        assert len(leistung.kategorien) == 1
        assert leistung.kategorien[0].name == "Familie"
    
    def test_add_duplicate_kategorie(self):
        """Test: Doppelte Kategorie nicht hinzufügen"""
        leistung = Leistung(
            id="elterngeld",
            name="Elterngeld"
        )
        
        kategorie = Leistungskategorie(
            id="familie",
            name="Familie"
        )
        
        leistung.add_kategorie(kategorie)
        leistung.add_kategorie(kategorie)
        
        assert len(leistung.kategorien) == 1
    
    def test_add_tag(self):
        """Test: Tag hinzufügen"""
        leistung = Leistung(
            id="elterngeld",
            name="Elterngeld"
        )
        
        tag = Leistungstag(
            id="geburt",
            name="Geburt"
        )
        
        leistung.add_tag(tag)
        
        assert len(leistung.tags) == 1
        assert leistung.tags[0].name == "Geburt"
    
    def test_add_duplicate_tag(self):
        """Test: Doppelten Tag nicht hinzufügen"""
        leistung = Leistung(
            id="elterngeld",
            name="Elterngeld"
        )
        
        tag = Leistungstag(
            id="geburt",
            name="Geburt"
        )
        
        leistung.add_tag(tag)
        leistung.add_tag(tag)
        
        assert len(leistung.tags) == 1
    
    def test_leistung_with_multiple_categories_and_tags(self):
        """Test: Leistung mit mehreren Kategorien und Tags"""
        leistung = Leistung(
            id="elterngeld",
            name="Elterngeld"
        )
        
        kategorien = [
            Leistungskategorie(id="familie", name="Familie"),
            Leistungskategorie(id="soziales", name="Soziales")
        ]
        
        tags = [
            Leistungstag(id="geburt", name="Geburt"),
            Leistungstag(id="schwangerschaft", name="Schwangerschaft")
        ]
        
        for kat in kategorien:
            leistung.add_kategorie(kat)
        
        for tag in tags:
            leistung.add_tag(tag)
        
        assert len(leistung.kategorien) == 2
        assert len(leistung.tags) == 2
