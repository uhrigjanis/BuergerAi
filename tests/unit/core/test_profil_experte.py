"""
Unit tests for ProfilExperte
"""

import pytest
from datetime import date

from buergerai.core.experten import ProfilExperte


class TestProfilExperte:
    """Tests für den ProfilExperten"""
    
    @pytest.fixture
    def experte(self):
        """Erstellt einen ProfilExperten mit leerem Storage"""
        return ProfilExperte()
    
    def test_create_profil(self, experte):
        """Test: Profil erstellen"""
        profil = experte.create_profil("session1", "80331")
        
        assert profil["session_id"] == "session1"
        assert profil["plz"] == "80331"
        assert "haushalt" in profil
        assert "situation" in profil
    
    def test_create_profil_with_initial_data(self, experte):
        """Test: Profil mit Initialdaten erstellen"""
        initial_data = {
            "haushalt": {
                "antragstellerin": {
                    "alter": 30
                }
            }
        }
        
        profil = experte.create_profil("session1", "80331", initial_data)
        
        assert profil["haushalt"]["antragstellerin"]["alter"] == 30
    
    def test_get_profil(self, experte):
        """Test: Profil holen"""
        experte.create_profil("session1", "80331")
        
        profil = experte.get_profil("session1")
        
        assert profil is not None
        assert profil["session_id"] == "session1"
    
    def test_get_profil_not_found(self, experte):
        """Test: Profil nicht gefunden"""
        profil = experte.get_profil("nonexistent")
        
        assert profil is None
    
    def test_update_profil(self, experte):
        """Test: Profil aktualisieren"""
        experte.create_profil("session1", "80331")
        
        updates = {
            "haushalt": {
                "antragstellerin": {
                    "alter": 30
                }
            }
        }
        
        profil = experte.update_profil("session1", updates)
        
        assert profil["haushalt"]["antragstellerin"]["alter"] == 30
    
    def test_update_profil_not_found(self, experte):
        """Test: Profil aktualisieren - nicht gefunden"""
        updates = {"test": "value"}
        
        with pytest.raises(ValueError, match="Profil für Session nonexistent nicht gefunden"):
            experte.update_profil("nonexistent", updates)
    
    def test_delete_profil(self, experte):
        """Test: Profil löschen"""
        experte.create_profil("session1", "80331")
        
        result = experte.delete_profil("session1")
        
        assert result is True
        assert experte.get_profil("session1") is None
    
    def test_delete_profil_not_found(self, experte):
        """Test: Profil löschen - nicht gefunden"""
        result = experte.delete_profil("nonexistent")
        
        assert result is False
    
    def test_get_wert(self, experte):
        """Test: Wert aus Profil holen"""
        profil = {
            "haushalt": {
                "antragstellerin": {
                    "alter": 30
                }
            }
        }
        
        alter = experte.get_wert(profil, "haushalt.antragstellerin.alter")
        
        assert alter == 30
    
    def test_get_wert_not_found(self, experte):
        """Test: Wert nicht gefunden"""
        profil = {"haushalt": {}}
        
        alter = experte.get_wert(profil, "haushalt.antragstellerin.alter")
        
        assert alter is None
    
    def test_validate_profil_valid(self, experte):
        """Test: Gültiges Profil validieren"""
        profil = {
            "session_id": "session1",
            "plz": "80331",
            "haushalt": {
                "antragstellerin": {}
            }
        }
        
        fehler = experte.validate_profil(profil)
        
        assert len(fehler) == 0
    
    def test_validate_profil_missing_session_id(self, experte):
        """Test: Profil ohne Session-ID validieren"""
        profil = {
            "plz": "80331",
            "haushalt": {
                "antragstellerin": {}
            }
        }
        
        fehler = experte.validate_profil(profil)
        
        assert len(fehler) == 1
        assert "Session-ID fehlt" in fehler
    
    def test_validate_profil_invalid_plz(self, experte):
        """Test: Profil mit ungültiger PLZ validieren"""
        profil = {
            "session_id": "session1",
            "plz": "invalid",
            "haushalt": {
                "antragstellerin": {}
            }
        }
        
        fehler = experte.validate_profil(profil)
        
        assert len(fehler) == 1
        assert "PLZ muss ein 5-stelliger String sein" in fehler
    
    def test_get_alter(self, experte):
        """Test: Alter der Antragstellerin holen"""
        profil = {
            "haushalt": {
                "antragstellerin": {
                    "alter": 30
                }
            }
        }
        
        alter = experte.get_alter(profil)
        
        assert alter == 30
    
    def test_get_alter_not_set(self, experte):
        """Test: Alter nicht gesetzt"""
        profil = {"haushalt": {"antragstellerin": {}}}
        
        alter = experte.get_alter(profil)
        
        assert alter is None
    
    def test_get_einkommen(self, experte):
        """Test: Einkommen der Antragstellerin holen"""
        profil = {
            "haushalt": {
                "antragstellerin": {
                    "einkommen_jaehrlich": 50000
                }
            }
        }
        
        einkommen = experte.get_einkommen(profil)
        
        assert einkommen == 50000
    
    def test_get_anzahl_kinder(self, experte):
        """Test: Anzahl der Kinder holen"""
        profil = {
            "haushalt": {
                "kinder": [
                    {"name": "Kind 1"},
                    {"name": "Kind 2"}
                ]
            }
        }
        
        anzahl = experte.get_anzahl_kinder(profil)
        
        assert anzahl == 2
    
    def test_get_schwangerschaft(self, experte):
        """Test: Schwangerschaft prüfen"""
        profil_schwanger = {
            "situation": {
                "schwangerschaft": {
                    "vorhanden": True
                }
            }
        }
        
        profil_nicht_schwanger = {
            "situation": {
                "schwangerschaft": {
                    "vorhanden": False
                }
            }
        }
        
        assert experte.get_schwangerschaft(profil_schwanger) is True
        assert experte.get_schwangerschaft(profil_nicht_schwanger) is False
    
    def test_get_geburt(self, experte):
        """Test: Geburt prüfen"""
        profil_geburt = {
            "situation": {
                "geburt": {
                    "vorhanden": True
                }
            }
        }
        
        profil_keine_geburt = {
            "situation": {
                "geburt": {
                    "vorhanden": False
                }
            }
        }
        
        assert experte.get_geburt(profil_geburt) is True
        assert experte.get_geburt(profil_keine_geburt) is False
