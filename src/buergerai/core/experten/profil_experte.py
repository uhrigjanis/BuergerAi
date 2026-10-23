"""
ProfilExperte - Experte für die Verwaltung von User-Profilen
"""

from typing import Optional, List, Dict, Any
from datetime import date
import json
import os

from ...models import Gebiet


class ProfilExperte:
    """
    Experte für die Verwaltung von User-Profilen.
    
    Verantwortlich für:
    - Erstellen, Lesen, Aktualisieren von Profilen
    - Speicherung in Session-Storage (temporär)
    - Validierung von Profil-Daten
    """
    
    def __init__(self, session_storage: Optional[Dict[str, Any]] = None):
        """
        Initialisiert den ProfilExperten.
        
        Args:
            session_storage: Dictionary für die Session-Speicherung
                           (Default: In-Memory Speicher)
        """
        self.session_storage = session_storage or {}
        
    def create_profil(self, session_id: str, plz: str, initial_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Erstellt ein neues Profil.
        
        Args:
            session_id: Eindeutige Session-ID
            plz: Postleitzahl des Wohnorts
            initial_data: Optionale initiale Daten
            
        Returns:
            Das erstellte Profil
        """
        profil = {
            "session_id": session_id,
            "plz": plz,
            "erstellungsdatum": date.today().isoformat(),
            "letzte_aktivitaet": date.today().isoformat(),
            "haushalt": {
                "antragstellerin": {
                    "alter": None,
                    "einkommen_jaehrlich": None,
                    "einkommen_monatlich": None,
                    "beschäftigungsstatus": None,
                    "staatsangehörigkeit": "deutsch",
                    "familienstand": None
                },
                "partner": {
                    "vorhanden": False,
                    "alter": None,
                    "einkommen_jaehrlich": None
                },
                "kinder": [],
                "wohnsitz": {
                    "plz": plz,
                    "ort": None
                }
            },
            "situation": {
                "schwangerschaft": {
                    "vorhanden": False,
                    "geburtstermin": None,
                    "anzahl_kinder": 0
                },
                "geburt": {
                    "vorhanden": False,
                    "geburtsdatum": None,
                    "anzahl_kinder": 0
                },
                "heirat": {
                    "vorhanden": False,
                    "datums": None
                }
            }
        }
        
        # Initialdaten überschreiben
        if initial_data:
            self._merge_profil(profil, initial_data)
        
        # Speichern
        self.session_storage[session_id] = profil
        
        return profil
    
    def get_profil(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Holt ein Profil für eine Session-ID.
        
        Args:
            session_id: Session-ID
            
        Returns:
            Das Profil oder None, wenn nicht gefunden
        """
        profil = self.session_storage.get(session_id)
        
        if profil:
            # Letzte Aktivität aktualisieren
            profil["letzte_aktivitaet"] = date.today().isoformat()
            self.session_storage[session_id] = profil
        
        return profil
    
    def update_profil(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aktualisiert ein Profil.
        
        Args:
            session_id: Session-ID
            updates: Dictionary mit Updates
            
        Returns:
            Das aktualisierte Profil
            
        Raises:
            ValueError: Wenn das Profil nicht existiert
        """
        profil = self.get_profil(session_id)
        
        if not profil:
            raise ValueError(f"Profil für Session {session_id} nicht gefunden")
        
        # Updates anwenden
        self._merge_profil(profil, updates)
        
        # Speichern
        self.session_storage[session_id] = profil
        
        return profil
    
    def delete_profil(self, session_id: str) -> bool:
        """
        Löscht ein Profil.
        
        Args:
            session_id: Session-ID
            
        Returns:
            True, wenn das Profil gelöscht wurde, sonst False
        """
        if session_id in self.session_storage:
            del self.session_storage[session_id]
            return True
        return False
    
    def _merge_profil(self, profil: Dict[str, Any], updates: Dict[str, Any]):
        """
        Führt zwei Profile zusammen (Deep Merge).
        
        Args:
            profil: Das Ziel-Profil
            updates: Die Updates
        """
        for key, value in updates.items():
            if key in profil and isinstance(profil[key], dict) and isinstance(value, dict):
                # Rekursiver Merge für verschachtelte Dictionaries
                self._merge_profil(profil[key], value)
            else:
                profil[key] = value
    
    def get_wert(self, profil: Dict[str, Any], pfad: str) -> Any:
        """
        Holt einen Wert aus dem Profil anhand eines Pfads.
        
        Beispiel:
            get_wert(profil, "haushalt.antragstellerin.alter")
            -> profil["haushalt"]["antragstellerin"]["alter"]
        
        Args:
            profil: Das Profil
            pfad: Der Pfad (dot-notation)
            
        Returns:
            Der Wert oder None, wenn nicht gefunden
        """
        keys = pfad.split(".")
        aktuell = profil
        
        for key in keys:
            if isinstance(aktuell, dict) and key in aktuell:
                aktuell = aktuell[key]
            else:
                return None
        
        return aktuell
    
    def validate_profil(self, profil: Dict[str, Any]) -> List[str]:
        """
        Validiert ein Profil.
        
        Args:
            profil: Das zu validierende Profil
            
        Returns:
            Liste von Fehlern (leer, wenn gültig)
        """
        fehler = []
        
        # Session-ID prüfen
        if "session_id" not in profil:
            fehler.append("Session-ID fehlt")
        
        # PLZ prüfen
        if "plz" not in profil:
            fehler.append("PLZ fehlt")
        elif not isinstance(profil["plz"], str) or len(profil["plz"]) != 5:
            fehler.append("PLZ muss ein 5-stelliger String sein")
        
        # Haushalt prüfen
        if "haushalt" not in profil:
            fehler.append("Haushalt fehlt")
        else:
            haushalt = profil["haushalt"]
            
            # Antragstellerin prüfen
            if "antragstellerin" not in haushalt:
                fehler.append("Antragstellerin fehlt")
        
        return fehler
    
    def get_alter(self, profil: Dict[str, Any]) -> Optional[int]:
        """Holt das Alter der Antragstellerin"""
        return self.get_wert(profil, "haushalt.antragstellerin.alter")
    
    def get_einkommen(self, profil: Dict[str, Any]) -> Optional[float]:
        """Holt das jährliche Einkommen der Antragstellerin"""
        return self.get_wert(profil, "haushalt.antragstellerin.einkommen_jaehrlich")
    
    def get_anzahl_kinder(self, profil: Dict[str, Any]) -> int:
        """Holt die Anzahl der Kinder"""
        kinder = self.get_wert(profil, "haushalt.kinder") or []
        return len(kinder)
    
    def get_schwangerschaft(self, profil: Dict[str, Any]) -> bool:
        """Prüft, ob Schwangerschaft vorliegt"""
        return self.get_wert(profil, "situation.schwangerschaft.vorhanden") or False
    
    def get_geburt(self, profil: Dict[str, Any]) -> bool:
        """Prüft, ob Geburt vorliegt"""
        return self.get_wert(profil, "situation.geburt.vorhanden") or False
