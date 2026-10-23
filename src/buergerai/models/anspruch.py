"""
Anspruchsmodell für die Prüfung von Anspruchsberechtigungen
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional, List, Dict, Any
import uuid


class Operator(Enum):
    """Vergleichsoperatoren für Bedingungen"""
    EQUAL = "=="
    NOT_EQUAL = "!="
    GREATER_THAN = ">"
    GREATER_EQUAL = ">="
    LESS_THAN = "<"
    LESS_EQUAL = "<="
    IN = "in"
    NOT_IN = "not in"
    CONTAINS = "contains"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


@dataclass
class Bedingung:
    """
    Eine einzelne Bedingung für die Anspruchsprüfung.
    
    Attribute:
        id: Eindeutige Identifikationsnummer
        feld: Das zu prüfende Feld im Profil (z.B. "alter", "einkommen")
        operator: Vergleichsoperator
        wert: Der zu vergleichende Wert
        beschreibung: Menschlich lesbare Beschreibung
        reihenfolge: Reihenfolge der Prüfung
    """
    id: str
    feld: str
    operator: Operator
    wert: Any
    beschreibung: Optional[str] = None
    reihenfolge: int = 0
    
    def __post_init__(self):
        """Validierung nach Initialisierung"""
        if self.id is None:
            object.__setattr__(self, 'id', str(uuid.uuid4()))
    
    def prüfe(self, profil_wert: Any) -> bool:
        """
        Prüft, ob die Bedingung für einen gegebenen Profilwert erfüllt ist.
        
        Args:
            profil_wert: Der Wert aus dem Profil für das Feld
            
        Returns:
            True, wenn die Bedingung erfüllt ist, sonst False
        """
        try:
            if self.operator == Operator.EQUAL:
                return profil_wert == self.wert
            elif self.operator == Operator.NOT_EQUAL:
                return profil_wert != self.wert
            elif self.operator == Operator.GREATER_THAN:
                return profil_wert > self.wert
            elif self.operator == Operator.GREATER_EQUAL:
                return profil_wert >= self.wert
            elif self.operator == Operator.LESS_THAN:
                return profil_wert < self.wert
            elif self.operator == Operator.LESS_EQUAL:
                return profil_wert <= self.wert
            elif self.operator == Operator.IN:
                return profil_wert in self.wert
            elif self.operator == Operator.NOT_IN:
                return profil_wert not in self.wert
            elif self.operator == Operator.CONTAINS:
                if isinstance(profil_wert, str) and isinstance(self.wert, str):
                    return self.wert.lower() in profil_wert.lower()
                return False
            elif self.operator == Operator.IS_NULL:
                return profil_wert is None
            elif self.operator == Operator.IS_NOT_NULL:
                return profil_wert is not None
            else:
                raise ValueError(f"Unbekannter Operator: {self.operator}")
        except TypeError:
            # Typen passen nicht zusammen
            return False


@dataclass
class Anspruchsregel:
    """
    Eine Regel zur Prüfung des Anspruchs auf eine Leistung.
    
    Eine Regel besteht aus einer oder mehreren Bedingungen, die alle
    erfüllt sein müssen (AND-Logik).
    
    Attribute:
        id: Eindeutige Identifikationsnummer
        name: Name der Regel
        beschreibung: Beschreibung der Regel
        bedingungen: Liste der Bedingungen
        gueltig_ab: Gültigkeitsbeginn
        gueltig_bis: Gültigkeitsende (None für aktuell gültig)
    """
    id: str
    name: str
    beschreibung: Optional[str] = None
    bedingungen: List[Bedingung] = field(default_factory=list)
    gueltig_ab: date = field(default_factory=date.today)
    gueltig_bis: Optional[date] = None
    
    def __post_init__(self):
        """Validierung nach Initialisierung"""
        if self.id is None:
            object.__setattr__(self, 'id', str(uuid.uuid4()))
    
    def ist_gueltig(self, datum: Optional[date] = None) -> bool:
        """Prüft, ob die Regel zum gegebenen Datum gültig ist"""
        if datum is None:
            datum = date.today()
        
        if datum < self.gueltig_ab:
            return False
        
        if self.gueltig_bis is not None and datum > self.gueltig_bis:
            return False
        
        return True
    
    def prüfe_alle_bedingungen(self, profil: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Prüft alle Bedingungen gegen ein Profil.
        
        Args:
            profil: Dictionary mit Profil-Daten
            
        Returns:
            Tuple aus (ergebnis, nicht_erfüllte_bedingungen)
            - ergebnis: True, wenn alle Bedingungen erfüllt sind
            - nicht_erfüllte_bedingungen: Liste der Beschreibungen nicht erfüllter Bedingungen
        """
        nicht_erfüllt = []
        
        for bedingung in sorted(self.bedingungen, key=lambda b: b.reihenfolge):
            profil_wert = profil.get(bedingung.feld)
            
            if not bedingung.prüfe(profil_wert):
                nicht_erfüllt.append(
                    bedingung.beschreibung or 
                    f"{bedingung.feld} {bedingung.operator.value} {bedingung.wert}"
                )
        
        return (len(nicht_erfüllt) == 0, nicht_erfüllt)
    
    def add_bedingung(self, bedingung: Bedingung):
        """Fügt eine Bedingung hinzu"""
        self.bedingungen.append(bedingung)
