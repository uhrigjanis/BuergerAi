"""
Leistungsvariantenmodell für regionale Ausprägungen von Leistungen
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional, List
import uuid


class Abdeckungsstatus(Enum):
    """Status der Datenabdeckung für eine Leistungsvariante"""
    VERIFIZIERT = "verifiziert"      # Vollständig geprüft gegen Primärquellen
    LANDESEBENE = "landesebene"      # Daten auf Landesebene verfügbar
    UNBEKANNT = "unbekannt"        # Daten nicht vollständig erfasst


@dataclass
class Leistungsvariante:
    """
    Repräsentiert eine regionale Ausprägung einer Leistung.
    
    Jede Leistung kann in verschiedenen Gebieten (Bund, Land, Kreis, Gemeinde)
    unterschiedliche Varianten haben (z.B. unterschiedliche Regelungen,
    Zuständigkeiten oder Verfahren).
    
    Attribute:
        id: Eindeutige Identifikationsnummer
        leistung_id: ID der abstrakten Leistung
        gebiet_id: ID des Gebiets, für das diese Variante gilt
        anspruchsregel_id: ID der Anspruchsregel (optional)
        zustaendigkeit_id: ID der Zuständigkeit (optional)
        verfahrens_id: ID des Verfahrens (optional)
        abdeckungsstatus: Status der Datenabdeckung
        gueltig_ab: Gültigkeitsbeginn
        gueltig_bis: Gültigkeitsende (None für aktuell gültig)
        quellen: Liste der Quellen-IDs
    """
    id: str
    leistung_id: str
    gebiet_id: str
    anspruchsregel_id: Optional[str] = None
    zustaendigkeit_id: Optional[str] = None
    verfahrens_id: Optional[str] = None
    abdeckungsstatus: Abdeckungsstatus = Abdeckungsstatus.UNBEKANNT
    gueltig_ab: date = field(default_factory=date.today)
    gueltig_bis: Optional[date] = None
    quellen: List[str] = field(default_factory=list)
    erstellungsdatum: date = field(default_factory=date.today)
    letze_aenderung: date = field(default_factory=date.today)
    
    def __post_init__(self):
        """Validierung nach Initialisierung"""
        if self.id is None:
            object.__setattr__(self, 'id', str(uuid.uuid4()))
    
    def ist_gueltig(self, datum: Optional[date] = None) -> bool:
        """Prüft, ob die Variante zum gegebenen Datum gültig ist"""
        if datum is None:
            datum = date.today()
        
        if datum < self.gueltig_ab:
            return False
        
        if self.gueltig_bis is not None and datum > self.gueltig_bis:
            return False
        
        return True
    
    def ist_vollstaendig(self) -> bool:
        """Prüft, ob die Variante vollständig erfasst ist"""
        return self.abdeckungsstatus == Abdeckungsstatus.VERIFIZIERT
    
    def hat_anspruchsregel(self) -> bool:
        """Prüft, ob eine Anspruchsregel definiert ist"""
        return self.anspruchsregel_id is not None
    
    def hat_zustaendigkeit(self) -> bool:
        """Prüft, ob eine Zuständigkeit definiert ist"""
        return self.zustaendigkeit_id is not None
    
    def hat_verfahren(self) -> bool:
        """Prüft, ob ein Verfahren definiert ist"""
        return self.verfahrens_id is not None
