"""
LeistungsExperte - Experte für die Suche und Filterung von Leistungen
"""

from typing import Optional, List, Dict, Any
from datetime import date

from ...models import (
    Leistung, Leistungsvariante, Abdeckungsstatus, Gebiet
)
from ...knowledge_base import KnowledgeBase

# Typ-Alias für Hierarchie-Pfade
GebietsHierarchie = List[Gebiet]


class LeistungsExperte:
    """
    Experte für die Suche und Filterung von Leistungen.
    
    Verantwortlich für:
    - Suche von Leistungen nach Lebenssituationen
    - Filterung nach Gebieten
    - Auswahl der besten Variante für ein Gebiet
    """
    
    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None):
        """
        Initialisiert den LeistungsExperten.
        
        Args:
            knowledge_base: Knowledge Base für den Datenzugriff
        """
        self.kb = knowledge_base or KnowledgeBase()
        
    def suche_leistungen(
        self,
        lebenssituationen: List[str],
        hierarchie: Optional[GebietsHierarchie] = None,
        gueltig_am: Optional[date] = None
    ) -> List[Leistungsvariante]:
        """
        Sucht Leistungen nach Lebenssituationen.
        
        Args:
            lebenssituationen: Liste von Lebenssituationen (z.B. ["Schwangerschaft"])
            hierarchie: Optionale Gebietshierarchie für Filterung
            gueltig_am: Datum, für das die Leistungen gültig sein müssen
            
        Returns:
            Liste von passenden Leistungsvarianten
        """
        if not lebenssituationen:
            return []
        
        # Suche in der Knowledge Base
        varianten = self.kb.suche_leistungen_by_lebenssituation(
            lebenssituationen, hierarchie, gueltig_am
        )
        
        return varianten
    
    def get_leistung_by_id(self, leistung_id: str) -> Optional[Leistung]:
        """
        Holt eine Leistung für eine ID.
        
        Args:
            leistung_id: ID der Leistung
            
        Returns:
            Die Leistung oder None
        """
        return self.kb.get_leistung_by_id(leistung_id)
    
    def get_leistung_by_name(self, name: str) -> Optional[Leistung]:
        """
        Holt eine Leistung für einen Namen.
        
        Args:
            name: Name der Leistung
            
        Returns:
            Die Leistung oder None
        """
        return self.kb.get_leistung_by_name(name)
    
    def get_varianten_for_leistung(self, leistung_id: str) -> List[Leistungsvariante]:
        """
        Holt alle Varianten für eine Leistung.
        
        Args:
            leistung_id: ID der Leistung
            
        Returns:
            Liste von Varianten
        """
        return self.kb.get_varianten_for_leistung(leistung_id)
    
    def get_best_variante(
        self,
        leistung_id: str,
        hierarchie: GebietsHierarchie
    ) -> Optional[Leistungsvariante]:
        """
        Findet die beste (spezifischste) Variante für eine Leistung
        in einer gegebenen Hierarchie.
        
        Args:
            leistung_id: ID der Leistung
            hierarchie: Gebietshierarchie
            
        Returns:
            Die spezifischste gültige Variante oder None
        """
        return self.kb.get_best_variante(leistung_id, hierarchie)
    
    def get_varianten_for_gebiet(self, gebiet_id: str) -> List[Leistungsvariante]:
        """
        Holt alle Varianten für ein Gebiet.
        
        Args:
            gebiet_id: ID des Gebiets
            
        Returns:
            Liste von Varianten
        """
        return self.kb.get_varianten_for_gebiet(gebiet_id)
    
    def filter_by_abdeckungsstatus(
        self,
        varianten: List[Leistungsvariante],
        status: Abdeckungsstatus
    ) -> List[Leistungsvariante]:
        """
        Filtert Varianten nach Abdeckungsstatus.
        
        Args:
            varianten: Liste von Varianten
            status: Gewünschter Abdeckungsstatus
            
        Returns:
            Gefilterte Liste
        """
        return [v for v in varianten if v.abdeckungsstatus == status]
    
    def filter_gueltig(self, varianten: List[Leistungsvariante]) -> List[Leistungsvariante]:
        """
        Filtert Varianten nach Gültigkeit.
        
        Args:
            varianten: Liste von Varianten
            
        Returns:
            Nur gültige Varianten
        """
        return [v for v in varianten if v.ist_gueltig()]
    
    def get_all_leistungen(self) -> List[Leistung]:
        """
        Gibt alle Leistungen zurück.
        
        Returns:
            Liste aller Leistungen
        """
        return self.kb.get_all_leistungen()
    
    def get_all_varianten(self) -> List[Leistungsvariante]:
        """
        Gibt alle Varianten zurück.
        
        Returns:
            Liste aller Varianten
        """
        return self.kb.get_all_varianten()
    
    def get_leistung_tags(self, leistung: Leistung) -> List[str]:
        """
        Gibt alle Tags einer Leistung zurück.
        
        Args:
            leistung: Die Leistung
            
        Returns:
            Liste von Tag-Namen
        """
        return [tag.name for tag in leistung.tags]
    
    def get_leistung_kategorien(self, leistung: Leistung) -> List[str]:
        """
        Gibt alle Kategorien einer Leistung zurück.
        
        Args:
            leistung: Die Leistung
            
        Returns:
            Liste von Kategorie-Namen
        """
        return [kat.name for kat in leistung.kategorien]
