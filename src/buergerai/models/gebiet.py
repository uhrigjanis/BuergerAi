"""
Gebietsmodell für die hierarchische Darstellung von Bundesländern, Kreisen und Gemeinden
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional, List
import uuid


class GebietsEbene(Enum):
    """Ebenen der Gebietshierarchie"""
    BUND = "bund"
    LAND = "land"
    KREIS = "kreis"
    GEMEINDE = "gemeinde"


@dataclass
class Gebiet:
    """
    Repräsentiert ein geografisches Gebiet in der Hierarchie.
    
    Attribute:
        id: Eindeutige Identifikationsnummer
        name: Name des Gebiets (z.B. "Bayern", "München")
        ebene: Ebene in der Hierarchie (Bund, Land, Kreis, Gemeinde)
        ags: Amtlicher Gemeindeschlüssel
        parent_id: ID des übergeordneten Gebiets (None für Bund)
        plz_bereich: Liste der PLZ-Bereiche, die zu diesem Gebiet gehören
        gueltig_ab: Gültigkeitsbeginn
        gueltig_bis: Gültigkeitsende (None für aktuell gültig)
    """
    name: str
    ebene: GebietsEbene
    ags: str
    parent_id: Optional[str] = None
    plz_bereich: List[str] = field(default_factory=list)
    gueltig_ab: date = field(default_factory=date.today)
    gueltig_bis: Optional[date] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        """Validierung nach Initialisierung"""
        if self.ebene == GebietsEbene.BUND and self.parent_id is not None:
            raise ValueError("Bund darf kein parent_id haben")
        
        if self.ebene == GebietsEbene.BUND and self.ags != "00":
            raise ValueError("Bund muss AGS '00' haben")
    
    def ist_gueltig(self, datum: Optional[date] = None) -> bool:
        """Prüft, ob das Gebiet zum gegebenen Datum gültig ist"""
        if datum is None:
            datum = date.today()
        
        if datum < self.gueltig_ab:
            return False
        
        if self.gueltig_bis is not None and datum > self.gueltig_bis:
            return False
        
        return True
    
    def get_hierarchie_pfad(self, alle_gebiete: List['Gebiet']) -> List['Gebiet']:
        """
        Gibt die vollständige Hierarchie von diesem Gebiet bis zum Bund zurück.
        
        Args:
            alle_gebiete: Liste aller bekannten Gebiete
            
        Returns:
            Liste von Gebieten in der Reihenfolge: [Gemeinde, Kreis, Land, Bund] oder kürzer
        """
        gebiets_map = {g.id: g for g in alle_gebiete}
        hierarchie = []
        aktuell = self
        
        while aktuell is not None:
            hierarchie.append(aktuell)
            aktuell = gebiets_map.get(aktuell.parent_id)
        
        # Umkehren, damit Bund zuerst kommt
        return hierarchie[::-1]


# Typ-Alias für Hierarchie-Pfade
GebietsHierarchie = List[Gebiet]
