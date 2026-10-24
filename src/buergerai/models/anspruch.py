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
    feld: str
    operator: Operator
    wert: Any
    beschreibung: Optional[str] = None
    reihenfolge: int = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
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
    name: str
    beschreibung: Optional[str] = None
    bedingungen: List[Bedingung] = field(default_factory=list)
    gueltig_ab: date = field(default_factory=date.today)
    gueltig_bis: Optional[date] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
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
        Prüft alle Bedingungen gegen das Profil.
        
        Args:
            profil: Das Profil als Dictionary
            
        Returns:
            Tuple aus (erfüllt, Liste der nicht erfüllten Bedingungen)
        """
        nicht_erfuellt = []
        
        for bedingung in self.bedingungen:
            profil_wert = profil.get(bedingung.feld)
            if not bedingung.prüfe(profil_wert):
                nicht_erfuellt.append(bedingung.beschreibung or f"{bedingung.feld} {bedingung.operator.value} {bedingung.wert}")
        
        return len(nicht_erfuellt) == 0, nicht_erfuellt
    
    def prüfe_mit_leerem_profil(self) -> bool:
        """Prüft, ob die Regel auch mit leerem Profil erfüllt ist"""
        # Leeres Profil
        leeres_profil: Dict[str, Any] = {}
        erfüllt, _ = self.prüfe_alle_bedingungen(leeres_profil)
        return erfüllt
    
    def add_bedingung(self, bedingung: Bedingung) -> None:
        """Fügt eine Bedingung zur Regel hinzu"""
        self.bedingungen.append(bedingung)
        # Sortieren nach Reihenfolge
        self.bedingungen.sort(key=lambda b: b.reihenfolge)
