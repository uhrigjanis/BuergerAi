"""
Unit tests for AnspruchsExperte
"""

import pytest
from datetime import date

from buergerai.models import (
    Leistungsvariante, Abdeckungsstatus, Anspruchsregel, Bedingung, Operator
)
from buergerai.core.experten import AnspruchsExperte
from buergerai.knowledge_base import KnowledgeBase


class TestAnspruchsExperte:
    """Tests für den AnspruchsExperten"""
    
    @pytest.fixture
    def mock_kb(self):
        """Mock Knowledge Base mit Testdaten"""
        kb = KnowledgeBase()
        
        # Test-Regel
        regel = Anspruchsregel(
            id="regel1",
            name="Elterngeld-Berechtigung",
            beschreibung="Prüft die Berechtigung für Elterngeld"
        )
        
        # Bedingungen hinzufügen
        regel.add_bedingung(Bedingung(
            feld="haushalt.antragstellerin.alter",
            operator=Operator.GREATER_EQUAL,
            wert=18,
            beschreibung="Mindestens 18 Jahre alt"
        ))
        
        regel.add_bedingung(Bedingung(
            feld="situation.schwangerschaft.vorhanden",
            operator=Operator.EQUAL,
            wert=True,
            beschreibung="Schwangerschaft vorhanden"
        ))
        
        # Variante mit Regel
        variante_mit_regel = Leistungsvariante(
            id="elterngeld_bund",
            leistung_id="elterngeld",
            gebiet_id="bund",
            anspruchsregel_id="regel1",
            abdeckungsstatus=Abdeckungsstatus.VERIFIZIERT
        )
        
        # Variante ohne Regel
        variante_ohne_regel = Leistungsvariante(
            id="kindergeld_bund",
            leistung_id="kindergeld",
            gebiet_id="bund",
            abdeckungsstatus=Abdeckungsstatus.UNBEKANNT
        )
        
        kb.leistung_repo._regeln = {"regel1": regel}
        kb.leistung_repo._varianten = {
            "elterngeld_bund": variante_mit_regel,
            "kindergeld_bund": variante_ohne_regel
        }
        kb.leistung_repo._loaded = True
        
        return kb
    
    def test_pruefe_anspruch_erfüllt(self, mock_kb):
        """Test: Anspruch erfüllt"""
        experte = AnspruchsExperte(mock_kb)
        
        variante = mock_kb.get_varianten_for_leistung("elterngeld")[0]
        
        profil = {
            "haushalt": {
                "antragstellerin": {
                    "alter": 25
                }
            },
            "situation": {
                "schwangerschaft": {
                    "vorhanden": True
                }
            }
        }
        
        ergebnis = experte.pruefe_anspruch(variante, profil)
        
        assert ergebnis["ergebnis"] == "ja"
        assert len(ergebnis["begründung"]) == 1
        assert "Alle Bedingungen sind erfüllt" in ergebnis["begründung"][0]
    
    def test_pruefe_anspruch_nicht_erfüllt(self, mock_kb):
        """Test: Anspruch nicht erfüllt"""
        experte = AnspruchsExperte(mock_kb)
        
        variante = mock_kb.get_varianten_for_leistung("elterngeld")[0]
        
        profil = {
            "haushalt": {
                "antragstellerin": {
                    "alter": 17  # Zu jung
                }
            },
            "situation": {
                "schwangerschaft": {
                    "vorhanden": True
                }
            }
        }
        
        ergebnis = experte.pruefe_anspruch(variante, profil)
        
        assert ergebnis["ergebnis"] == "nein"
        assert len(ergebnis["begründung"]) == 1
        assert "Mindestens 18 Jahre alt" in ergebnis["begründung"][0]
    
    def test_pruefe_anspruch_keine_regel(self, mock_kb):
        """Test: Keine Anspruchsregel definiert"""
        experte = AnspruchsExperte(mock_kb)
        
        variante = mock_kb.get_varianten_for_leistung("kindergeld")[0]
        
        profil = {}
        
        ergebnis = experte.pruefe_anspruch(variante, profil)
        
        assert ergebnis["ergebnis"] == "unklar"
        assert len(ergebnis["begründung"]) == 1
        assert "Keine Anspruchsregel für diese Variante definiert" in ergebnis["begründung"][0]
    
    def test_pruefe_alle_varianten(self, mock_kb):
        """Test: Alle Varianten prüfen"""
        experte = AnspruchsExperte(mock_kb)
        
        varianten = list(mock_kb.get_all_varianten())
        
        profil = {
            "haushalt": {
                "antragstellerin": {
                    "alter": 25
                }
            },
            "situation": {
                "schwangerschaft": {
                    "vorhanden": True
                }
            }
        }
        
        ergebnisse = experte.prüfe_alle_varianten(varianten, profil)
        
        assert len(ergebnisse) == 2
        
        # Elterngeld sollte erfüllt sein
        elterngeld_ergebnis = next(
            (e for e in ergebnisse if e["leistung_id"] == "elterngeld"),
            None
        )
        assert elterngeld_ergebnis is not None
        assert elterngeld_ergebnis["ergebnis"] == "ja"
        
        # Kindergeld sollte unklar sein
        kindergeld_ergebnis = next(
            (e for e in ergebnisse if e["leistung_id"] == "kindergeld"),
            None
        )
        assert kindergeld_ergebnis is not None
        assert kindergeld_ergebnis["ergebnis"] == "unklar"
    
    def test_get_anspruchsregel(self, mock_kb):
        """Test: Anspruchsregel holen"""
        experte = AnspruchsExperte(mock_kb)
        
        regel = experte.get_anspruchsregel("regel1")
        
        assert regel is not None
        assert regel.name == "Elterngeld-Berechtigung"
    
    def test_get_anspruchsregel_not_found(self, mock_kb):
        """Test: Anspruchsregel nicht gefunden"""
        experte = AnspruchsExperte(mock_kb)
        
        regel = experte.get_anspruchsregel("nonexistent")
        
        assert regel is None
    
    def test_create_bedingung(self):
        """Test: Bedingung erstellen"""
        experte = AnspruchsExperte()
        
        bedingung = experte.create_bedingung(
            feld="alter",
            operator=Operator.GREATER_EQUAL,
            wert=18,
            beschreibung="Mindestens 18 Jahre alt"
        )
        
        assert bedingung.feld == "alter"
        assert bedingung.operator == Operator.GREATER_EQUAL
        assert bedingung.wert == 18
        assert bedingung.beschreibung == "Mindestens 18 Jahre alt"
    
    def test_pruefe_manuelle_bedingung(self):
        """Test: Bedingung manuell prüfen"""
        experte = AnspruchsExperte()
        
        bedingung = experte.create_bedingung(
            feld="alter",
            operator=Operator.GREATER_EQUAL,
            wert=18
        )
        
        assert experte.prüfe_manuelle_bedingung(bedingung, 25) is True
        assert experte.prüfe_manuelle_bedingung(bedingung, 17) is False
