"""
GebietsExperte - Experte für die Auflösung von Gebieten und Hierarchien
"""

from typing import Optional, List, Dict, Any
from datetime import date

from ...models import Gebiet, GebietsEbene, GebietsHierarchie
from ...knowledge_base import KnowledgeBase


class GebietsExperte:
    """
    Experte für die Auflösung von Gebieten und deren Hierarchien.
    
    Verantwortlich für:
    - Auflösen von PLZ zu Gebiet
    - Erstellen der vollständigen Hierarchie (Gemeinde -> Kreis -> Land -> Bund)
    - Validierung von Gebieten
    """
    
    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None):
        """
        Initialisiert den GebietsExperten.
        
        Args:
            knowledge_base: Knowledge Base für den Datenzugriff
        """
        self.kb = knowledge_base or KnowledgeBase()
        
    def resolve_hierarchie(self, plz: str) -> GebietsHierarchie:
        """
        Löst die vollständige Gebietshierarchie für eine PLZ auf.
        
        Args:
            plz: Postleitzahl als String (z.B. "80331")
            
        Returns:
            Liste von Gebieten in der Reihenfolge: [Gemeinde, Kreis, Land, Bund]
            oder eine kürzere Liste, wenn nicht alle Ebenen verfügbar sind.
            
        Raises:
            ValueError: Wenn die PLZ ungültig ist
        """
        if not plz or not isinstance(plz, str):
            raise ValueError(f"Ungültige PLZ: {plz}")
        
        # Normalisieren (Leerzeichen entfernen)
        plz = plz.strip()
        
        # Hierarchie aus der Knowledge Base holen
        hierarchie = self.kb.resolve_hierarchie(plz)
        
        if not hierarchie:
            # Fallback: Bund
            bund = self.kb.get_gebiet_by_ags("00")
            if bund:
                return [bund]
            raise ValueError(f"Keine Hierarchie für PLZ {plz} gefunden")
        
        return hierarchie
    
    def get_gebiet_by_plz(self, plz: str) -> Optional[Gebiet]:
        """
        Holt das spezifischste Gebiet für eine PLZ.
        
        Args:
            plz: Postleitzahl
            
        Returns:
            Das Gebiet oder None, wenn nicht gefunden
        """
        return self.kb.get_gebiet_by_plz(plz)
    
    def get_gebiet_by_ags(self, ags: str) -> Optional[Gebiet]:
        """
        Holt das Gebiet für einen AGS (Amtlicher Gemeindeschlüssel).
        
        Args:
            ags: Amtlicher Gemeindeschlüssel
            
        Returns:
            Das Gebiet oder None, wenn nicht gefunden
        """
        return self.kb.get_gebiet_by_ags(ags)
    
    def get_gebiet_by_id(self, gebiet_id: str) -> Optional[Gebiet]:
        """
        Holt das Gebiet für eine ID.
        
        Args:
            gebiet_id: ID des Gebiets
            
        Returns:
            Das Gebiet oder None, wenn nicht gefunden
        """
        return self.kb.get_gebiet_by_id(gebiet_id)
    
    def validate_plz(self, plz: str) -> bool:
        """
        Validiert eine PLZ.
        
        Args:
            plz: Postleitzahl
            
        Returns:
            True, wenn die PLZ gültig ist, sonst False
        """
        gebiet = self.get_gebiet_by_plz(plz)
        return gebiet is not None
    
    def get_ebene(self, gebiet: Gebiet) -> GebietsEbene:
        """
        Gibt die Ebene eines Gebiets zurück.
        
        Args:
            gebiet: Das Gebiet
            
        Returns:
            Die Ebene des Gebiets
        """
        return gebiet.ebene
    
    def get_parent(self, gebiet: Gebiet) -> Optional[Gebiet]:
        """
        Gibt das übergeordnete Gebiet zurück.
        
        Args:
            gebiet: Das Gebiet
            
        Returns:
            Das übergeordnete Gebiet oder None
        """
        if gebiet.parent_id:
            return self.get_gebiet_by_id(gebiet.parent_id)
        return None
    
    def get_children(self, gebiet: Gebiet) -> List[Gebiet]:
        """
        Gibt alle untergeordneten Gebiete zurück.
        
        Args:
            gebiet: Das Gebiet
            
        Returns:
            Liste der untergeordneten Gebiete
        """
        return self.kb.gebiet_repo.get_children(gebiet.id)
    
    def get_all_gebiete(self) -> List[Gebiet]:
        """
        Gibt alle Gebiete zurück.
        
        Returns:
            Liste aller Gebiete
        """
        return self.kb.get_all_gebiete()
    
    def get_by_ebene(self, ebene: GebietsEbene) -> List[Gebiet]:
        """
        Gibt alle Gebiete einer bestimmten Ebene zurück.
        
        Args:
            ebene: Die gewünschte Ebene
            
        Returns:
            Liste der Gebiete dieser Ebene
        """
        return self.kb.gebiet_repo.get_by_ebene(ebene)
