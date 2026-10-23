"""
Unit tests for Anspruch model
"""

import pytest
from datetime import date

from buergerai.models import (
    Bedingung, Operator, Anspruchsregel
)


class TestBedingung:
    """Tests für das Bedingung-Modell"""
    
    def test_equal_operator(self):
        """Test: Gleichheitsoperator"""
        bedingung = Bedingung(
            feld="alter",
            operator=Operator.EQUAL,
            wert=30
        )
        
        assert bedingung.prüfe(30) is True
        assert bedingung.prüfe(25) is False
        assert bedingung.prüfe(35) is False
    
    def test_not_equal_operator(self):
        """Test: Ungleichheitsoperator"""
        bedingung = Bedingung(
            feld="status",
            operator=Operator.NOT_EQUAL,
            wert="verheiratet"
        )
        
        assert bedingung.prüfe("ledig") is True
        assert bedingung.prüfe("verheiratet") is False
    
    def test_greater_than_operator(self):
        """Test: Größer-als-Operator"""
        bedingung = Bedingung(
            feld="einkommen",
            operator=Operator.GREATER_THAN,
            wert=50000
        )
        
        assert bedingung.prüfe(50001) is True
        assert bedingung.prüfe(50000) is False
        assert bedingung.prüfe(49999) is False
    
    def test_greater_equal_operator(self):
        """Test: Größer-gleich-Operator"""
        bedingung = Bedingung(
            feld="einkommen",
            operator=Operator.GREATER_EQUAL,
            wert=50000
        )
        
        assert bedingung.prüfe(50000) is True
        assert bedingung.prüfe(50001) is True
        assert bedingung.prüfe(49999) is False
    
    def test_less_than_operator(self):
        """Test: Kleiner-als-Operator"""
        bedingung = Bedingung(
            feld="alter",
            operator=Operator.LESS_THAN,
            wert=18
        )
        
        assert bedingung.prüfe(17) is True
        assert bedingung.prüfe(18) is False
        assert bedingung.prüfe(19) is False
    
    def test_less_equal_operator(self):
        """Test: Kleiner-gleich-Operator"""
        bedingung = Bedingung(
            feld="anzahl_kinder",
            operator=Operator.LESS_EQUAL,
            wert=2
        )
        
        assert bedingung.prüfe(2) is True
        assert bedingung.prüfe(1) is True
        assert bedingung.prüfe(3) is False
    
    def test_in_operator(self):
        """Test: In-Operator"""
        bedingung = Bedingung(
            feld="familienstand",
            operator=Operator.IN,
            wert=["verheiratet", "verpartnert"]
        )
        
        assert bedingung.prüfe("verheiratet") is True
        assert bedingung.prüfe("verpartnert") is True
        assert bedingung.prüfe("ledig") is False
    
    def test_not_in_operator(self):
        """Test: Not-In-Operator"""
        bedingung = Bedingung(
            feld="familienstand",
            operator=Operator.NOT_IN,
            wert=["verheiratet", "verpartnert"]
        )
        
        assert bedingung.prüfe("ledig") is True
        assert bedingung.prüfe("geschieden") is True
        assert bedingung.prüfe("verheiratet") is False
    
    def test_contains_operator(self):
        """Test: Contains-Operator"""
        bedingung = Bedingung(
            feld="beschreibung",
            operator=Operator.CONTAINS,
            wert="Schwangerschaft"
        )
        
        assert bedingung.prüfe("Ich bin schwangerschaft") is True
        assert bedingung.prüfe("Ich bin Schwangerschaft") is True
        assert bedingung.prüfe("Ich bin nicht schwanger") is False
    
    def test_is_null_operator(self):
        """Test: Is-Null-Operator"""
        bedingung = Bedingung(
            feld="partner",
            operator=Operator.IS_NULL,
            wert=None
        )
        
        assert bedingung.prüfe(None) is True
        assert bedingung.prüfe("vorhanden") is False
    
    def test_is_not_null_operator(self):
        """Test: Is-Not-Null-Operator"""
        bedingung = Bedingung(
            feld="partner",
            operator=Operator.IS_NOT_NULL,
            wert=None
        )
        
        assert bedingung.prüfe("vorhanden") is True
        assert bedingung.prüfe(None) is False
    
    def test_type_mismatch(self):
        """Test: Typen passen nicht zusammen"""
        bedingung = Bedingung(
            feld="alter",
            operator=Operator.GREATER_THAN,
            wert=30
        )
        
        # String kann nicht mit Integer verglichen werden
        assert bedingung.prüfe("dreißig") is False


class TestAnspruchsregel:
    """Tests für das Anspruchsregel-Modell"""
    
    def test_create_regel(self):
        """Test: Erstellen einer Regel"""
        regel = Anspruchsregel(
            id="regel1",
            name="Elterngeld-Berechtigung",
            beschreibung="Prüft die Berechtigung für Elterngeld"
        )
        
        assert regel.id == "regel1"
        assert regel.name == "Elterngeld-Berechtigung"
        assert regel.beschreibung == "Prüft die Berechtigung für Elterngeld"
    
    def test_add_bedingung(self):
        """Test: Bedingung hinzufügen"""
        regel = Anspruchsregel(
            id="regel1",
            name="Test-Regel"
        )
        
        bedingung = Bedingung(
            feld="alter",
            operator=Operator.GREATER_EQUAL,
            wert=18
        )
        
        regel.add_bedingung(bedingung)
        
        assert len(regel.bedingungen) == 1
    
    def test_pruefe_alle_bedingungen_erfüllt(self):
        """Test: Alle Bedingungen erfüllt"""
        regel = Anspruchsregel(
            id="regel1",
            name="Test-Regel"
        )
        
        regel.add_bedingung(Bedingung(
            feld="alter",
            operator=Operator.GREATER_EQUAL,
            wert=18
        ))
        
        regel.add_bedingung(Bedingung(
            feld="einkommen",
            operator=Operator.LESS_EQUAL,
            wert=100000
        ))
        
        profil = {"alter": 25, "einkommen": 50000}
        
        erfüllt, nicht_erfüllt = regel.prüfe_alle_bedingungen(profil)
        
        assert erfüllt is True
        assert len(nicht_erfüllt) == 0
    
    def test_pruefe_alle_bedingungen_nicht_erfüllt(self):
        """Test: Nicht alle Bedingungen erfüllt"""
        regel = Anspruchsregel(
            id="regel1",
            name="Test-Regel"
        )
        
        regel.add_bedingung(Bedingung(
            feld="alter",
            operator=Operator.GREATER_EQUAL,
            wert=18,
            beschreibung="Mindestens 18 Jahre alt"
        ))
        
        regel.add_bedingung(Bedingung(
            feld="einkommen",
            operator=Operator.LESS_EQUAL,
            wert=100000,
            beschreibung="Einkommen unter 100.000 €"
        ))
        
        profil = {"alter": 17, "einkommen": 50000}
        
        erfüllt, nicht_erfüllt = regel.prüfe_alle_bedingungen(profil)
        
        assert erfüllt is False
        assert len(nicht_erfüllt) == 1
        assert "Mindestens 18 Jahre alt" in nicht_erfüllt[0]
    
    def test_ist_gueltig(self):
        """Test: Gültigkeit der Regel"""
        regel_gueltig = Anspruchsregel(
            id="regel1",
            name="Test-Regel",
            gueltig_ab=date(2020, 1, 1)
        )
        
        regel_abgelaufen = Anspruchsregel(
            id="regel2",
            name="Test-Regel",
            gueltig_ab=date(2020, 1, 1),
            gueltig_bis=date(2022, 12, 31)
        )
        
        assert regel_gueltig.ist_gueltig() is True
        assert regel_abgelaufen.ist_gueltig() is False
    
    def test_pruefe_mit_leerem_profil(self):
        """Test: Prüfung mit leerem Profil"""
        regel = Anspruchsregel(
            id="regel1",
            name="Test-Regel"
        )
        
        regel.add_bedingung(Bedingung(
            feld="alter",
            operator=Operator.GREATER_EQUAL,
            wert=18
        ))
        
        profil = {}
        
        erfüllt, nicht_erfüllt = regel.prüfe_alle_bedingungen(profil)
        
        assert erfüllt is False
        assert len(nicht_erfüllt) == 1
