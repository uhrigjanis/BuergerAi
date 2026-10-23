"""
Unit tests for Leistungsvariante model
"""

import pytest
from datetime import date

from buergerai.models import (
    Leistungsvariante, Abdeckungsstatus
)


class TestLeistungsvariante:
    """Tests für das Leistungsvariante-Modell"""
    
    def test_create_variante(self):
        """Test: Erstellen einer Leistungsvariante"""
        variante = Leistungsvariante(
            id="elterngeld_bayern",
            leistung_id="elterngeld",
            gebiet_id="bayern",
            abdeckungsstatus=Abdeckungsstatus.VERIFIZIERT
        )
        
        assert variante.id == "elterngeld_bayern"
        assert variante.leistung_id == "elterngeld"
        assert variante.gebiet_id == "bayern"
        assert variante.abdeckungsstatus == Abdeckungsstatus.VERIFIZIERT
    
    def test_ist_gueltig_current(self):
        """Test: Gültigkeit für aktuelles Datum"""
        variante = Leistungsvariante(
            id="test",
            leistung_id="test",
            gebiet_id="test",
            gueltig_ab=date(2020, 1, 1)
        )
        
        assert variante.ist_gueltig() is True
    
    def test_ist_gueltig_future(self):
        """Test: Gültigkeit für zukünftiges Datum"""
        variante = Leistungsvariante(
            id="test",
            leistung_id="test",
            gebiet_id="test",
            gueltig_ab=date(2050, 1, 1)
        )
        
        assert variante.ist_gueltig() is False
    
    def test_ist_gueltig_past(self):
        """Test: Gültigkeit für vergangenes Datum"""
        variante = Leistungsvariante(
            id="test",
            leistung_id="test",
            gebiet_id="test",
            gueltig_ab=date(2000, 1, 1),
            gueltig_bis=date(2020, 1, 1)
        )
        
        assert variante.ist_gueltig() is False
    
    def test_ist_gueltig_specific_date(self):
        """Test: Gültigkeit für spezifisches Datum"""
        variante = Leistungsvariante(
            id="test",
            leistung_id="test",
            gebiet_id="test",
            gueltig_ab=date(2020, 1, 1),
            gueltig_bis=date(2025, 12, 31)
        )
        
        assert variante.ist_gueltig(date(2022, 6, 15)) is True
        assert variante.ist_gueltig(date(2019, 12, 31)) is False
        assert variante.ist_gueltig(date(2026, 1, 1)) is False
    
    def test_ist_vollstaendig(self):
        """Test: Vollständigkeitsprüfung"""
        variante_verifiziert = Leistungsvariante(
            id="test1",
            leistung_id="test",
            gebiet_id="test",
            abdeckungsstatus=Abdeckungsstatus.VERIFIZIERT
        )
        
        variante_unbekannt = Leistungsvariante(
            id="test2",
            leistung_id="test",
            gebiet_id="test",
            abdeckungsstatus=Abdeckungsstatus.UNBEKANNT
        )
        
        assert variante_verifiziert.ist_vollstaendig() is True
        assert variante_unbekannt.ist_vollstaendig() is False
    
    def test_hat_anspruchsregel(self):
        """Test: Prüfung auf Anspruchsregel"""
        variante_mit_regel = Leistungsvariante(
            id="test1",
            leistung_id="test",
            gebiet_id="test",
            anspruchsregel_id="regel1"
        )
        
        variante_ohne_regel = Leistungsvariante(
            id="test2",
            leistung_id="test",
            gebiet_id="test"
        )
        
        assert variante_mit_regel.hat_anspruchsregel() is True
        assert variante_ohne_regel.hat_anspruchsregel() is False
    
    def test_hat_zustaendigkeit(self):
        """Test: Prüfung auf Zuständigkeit"""
        variante_mit_zustaendigkeit = Leistungsvariante(
            id="test1",
            leistung_id="test",
            gebiet_id="test",
            zustaendigkeit_id="zustaendigkeit1"
        )
        
        variante_ohne_zustaendigkeit = Leistungsvariante(
            id="test2",
            leistung_id="test",
            gebiet_id="test"
        )
        
        assert variante_mit_zustaendigkeit.hat_zustaendigkeit() is True
        assert variante_ohne_zustaendigkeit.hat_zustaendigkeit() is False
    
    def test_hat_verfahren(self):
        """Test: Prüfung auf Verfahren"""
        variante_mit_verfahren = Leistungsvariante(
            id="test1",
            leistung_id="test",
            gebiet_id="test",
            verfahrens_id="verfahren1"
        )
        
        variante_ohne_verfahren = Leistungsvariante(
            id="test2",
            leistung_id="test",
            gebiet_id="test"
        )
        
        assert variante_mit_verfahren.hat_verfahren() is True
        assert variante_ohne_verfahren.hat_verfahren() is False
    
    def test_variante_with_quellen(self):
        """Test: Variante mit Quellen"""
        variante = Leistungsvariante(
            id="test",
            leistung_id="test",
            gebiet_id="test",
            quellen=["quelle1", "quelle2"]
        )
        
        assert len(variante.quellen) == 2
        assert "quelle1" in variante.quellen
        assert "quelle2" in variante.quellen
