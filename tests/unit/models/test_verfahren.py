"""
Unit tests for Verfahren model
"""

import pytest

from buergerai.models import (
    Verfahren, Unterlage, Verfahrensschritt
)


class TestUnterlage:
    """Tests für das Unterlage-Modell"""
    
    def test_create_unterlage(self):
        """Test: Erstellen einer Unterlage"""
        unterlage = Unterlage(
            id="urkunde1",
            name="Geburtsurkunde",
            beschreibung="Offizielle Geburtsurkunde des Kindes",
            pflicht=True,
            reihenfolge=1
        )
        
        assert unterlage.id == "urkunde1"
        assert unterlage.name == "Geburtsurkunde"
        assert unterlage.beschreibung == "Offizielle Geburtsurkunde des Kindes"
        assert unterlage.pflicht is True
        assert unterlage.reihenfolge == 1


class TestVerfahrensschritt:
    """Tests für das Verfahrensschritt-Modell"""
    
    def test_create_schritt(self):
        """Test: Erstellen eines Verfahrensschritts"""
        schritt = Verfahrensschritt(
            id="schritt1",
            beschreibung="Antrag ausfüllen",
            geschatzte_dauer_minuten=30,
            reihenfolge=1
        )
        
        assert schritt.id == "schritt1"
        assert schritt.beschreibung == "Antrag ausfüllen"
        assert schritt.geschatzte_dauer_minuten == 30
        assert schritt.reihenfolge == 1


class TestVerfahren:
    """Tests für das Verfahren-Modell"""
    
    def test_create_verfahren(self):
        """Test: Erstellen eines Verfahrens"""
        verfahren = Verfahren(
            id="verfahren1",
            formular_link="https://example.com/formular",
            bearbeitungsdauer_tage=20,
            frist_tage=7,
            koste=12.50
        )
        
        assert verfahren.id == "verfahren1"
        assert verfahren.formular_link == "https://example.com/formular"
        assert verfahren.bearbeitungsdauer_tage == 20
        assert verfahren.frist_tage == 7
        assert verfahren.koste == 12.50
    
    def test_add_unterlage(self):
        """Test: Unterlage hinzufügen"""
        verfahren = Verfahren(id="verfahren1")
        
        unterlage1 = Unterlage(
            id="urkunde1",
            name="Geburtsurkunde",
            reihenfolge=1
        )
        
        unterlage2 = Unterlage(
            id="urkunde2",
            name="Personalausweis",
            reihenfolge=0
        )
        
        verfahren.add_unterlage(unterlage1)
        verfahren.add_unterlage(unterlage2)
        
        assert len(verfahren.unterlagen) == 2
        # Sollte nach Reihenfolge sortiert sein
        assert verfahren.unterlagen[0].name == "Personalausweis"
        assert verfahren.unterlagen[1].name == "Geburtsurkunde"
    
    def test_add_schritt(self):
        """Test: Verfahrensschritt hinzufügen"""
        verfahren = Verfahren(id="verfahren1")
        
        schritt1 = Verfahrensschritt(
            id="schritt1",
            beschreibung="Antrag ausfüllen",
            reihenfolge=1
        )
        
        schritt2 = Verfahrensschritt(
            id="schritt2",
            beschreibung="Unterlagen einreichen",
            reihenfolge=0
        )
        
        verfahren.add_schritt(schritt1)
        verfahren.add_schritt(schritt2)
        
        assert len(verfahren.schritte) == 2
        # Sollte nach Reihenfolge sortiert sein
        assert verfahren.schritte[0].beschreibung == "Unterlagen einreichen"
        assert verfahren.schritte[1].beschreibung == "Antrag ausfüllen"
    
    def test_get_gesamtdauer(self):
        """Test: Gesamtdauer berechnen"""
        verfahren = Verfahren(id="verfahren1")
        
        verfahren.add_schritt(Verfahrensschritt(
            id="schritt1",
            beschreibung="Antrag ausfüllen",
            geschatzte_dauer_minuten=30,
            reihenfolge=0
        ))
        
        verfahren.add_schritt(Verfahrensschritt(
            id="schritt2",
            beschreibung="Unterlagen einreichen",
            geschatzte_dauer_minuten=15,
            reihenfolge=1
        ))
        
        verfahren.add_schritt(Verfahrensschritt(
            id="schritt3",
            beschreibung="Warten auf Bearbeitung",
            reihenfolge=2
        ))
        
        assert verfahren.get_gesamtdauer_minuten() == 45
    
    def test_verfahren_with_all_attributes(self):
        """Test: Verfahren mit allen Attributen"""
        verfahren = Verfahren(
            id="verfahren1",
            formular_link="https://example.com/formular",
            bearbeitungsdauer_tage=30,
            frist_tage=14,
            koste=25.00
        )
        
        unterlage = Unterlage(
            id="urkunde1",
            name="Geburtsurkunde",
            pflicht=True
        )
        
        schritt = Verfahrensschritt(
            id="schritt1",
            beschreibung="Antrag ausfüllen",
            geschatzte_dauer_minuten=45
        )
        
        verfahren.add_unterlage(unterlage)
        verfahren.add_schritt(schritt)
        
        assert verfahren.formular_link is not None
        assert verfahren.bearbeitungsdauer_tage is not None
        assert verfahren.frist_tage is not None
        assert verfahren.koste is not None
        assert len(verfahren.unterlagen) == 1
        assert len(verfahren.schritte) == 1
