"""
Haupt-Knowledge-Base-Klasse für den Zugriff auf alle Daten
"""

from typing import Optional, List, Dict, Any
from datetime import date

from ..models import (
    Gebiet, GebietsEbene, Leistung, Leistungsvariante, Abdeckungsstatus,
    Anspruchsregel, Verfahren, Zustaendigkeit, Quelle
)
from .gebiet_repository import GebietRepository
from .leistung_repository import LeistungRepository


class KnowledgeBase:
    """
    Zentrale Knowledge Base für den Zugriff auf alle Daten.
    
    Diese Klasse aggregiert alle Repositories und bietet eine einheitliche
    Schnittstelle für den Zugriff auf Gebiete, Leistungen und deren Varianten.
    """
    
    def __init__(self):
        """Initialisiert die Knowledge Base mit den Repositories"""
        self.gebiet_repo = GebietRepository()
        self.leistung_repo = LeistungRepository()
        
    def get_gebiet_by_plz(self, plz: str) -> Optional[Gebiet]:
        """Holt das Gebiet für eine gegebene PLZ"""
        return self.gebiet_repo.get_by_plz(plz)
    
    def get_gebiet_by_ags(self, ags: str) -> Optional[Gebiet]:
        """Holt das Gebiet für einen gegebenen AGS"""
        return self.gebiet_repo.get_by_ags(ags)
    
    def get_gebiet_by_id(self, gebiet_id: str) -> Optional[Gebiet]:
        """Holt das Gebiet für eine gegebene ID"""
        return self.gebiet_repo.get_by_id(gebiet_id)
    
    def resolve_hierarchie(self, plz: str) -> List[Gebiet]:
        """
        Löst die vollständige Gebietshierarchie für eine PLZ auf.
        
        Args:
            plz: Postleitzahl
            
        Returns:
            Liste von Gebieten in der Reihenfolge: [Gemeinde, Kreis, Land, Bund]
            oder eine kürzere Liste, wenn nicht alle Ebenen verfügbar sind.
        """
        return self.gebiet_repo.resolve_hierarchie(plz)
    
    def get_all_gebiete(self) -> List[Gebiet]:
        """Holt alle Gebiete"""
        return self.gebiet_repo.get_all()
    
    def get_leistung_by_id(self, leistung_id: str) -> Optional[Leistung]:
        """Holt eine Leistung für eine gegebene ID"""
        return self.leistung_repo.get_by_id(leistung_id)
    
    def get_leistung_by_name(self, name: str) -> Optional[Leistung]:
        """Holt eine Leistung für einen gegebenen Namen"""
        return self.leistung_repo.get_by_name(name)
    
    def get_varianten_for_leistung(self, leistung_id: str) -> List[Leistungsvariante]:
        """Holt alle Varianten für eine Leistung"""
        return self.leistung_repo.get_varianten_for_leistung(leistung_id)
    
    def get_varianten_for_gebiet(self, gebiet_id: str) -> List[Leistungsvariante]:
        """Holt alle Varianten für ein Gebiet"""
        return self.leistung_repo.get_varianten_for_gebiet(gebiet_id)
    
    def suche_leistungen_by_tags(
        self, 
        tags: List[str], 
        hierarchie: Optional[List[Gebiet]] = None,
        gueltig_am: Optional[date] = None
    ) -> List[Leistungsvariante]:
        """
        Sucht Leistungsvarianten nach Tags.
        
        Args:
            tags: Liste von Tags (z.B. ["Schwangerschaft", "Geburt"])
            hierarchie: Optionale Gebietshierarchie für Filterung
            gueltig_am: Datum, für das die Varianten gültig sein müssen
            
        Returns:
            Liste von passenden Leistungsvarianten
        """
        return self.leistung_repo.suche_by_tags(tags, hierarchie, gueltig_am)
    
    def suche_leistungen_by_lebenssituation(
        self,
        lebenssituationen: List[str],
        hierarchie: Optional[List[Gebiet]] = None,
        gueltig_am: Optional[date] = None
    ) -> List[Leistungsvariante]:
        """
        Sucht Leistungsvarianten nach Lebenssituationen.
        
        Args:
            lebenssituationen: Liste von Lebenssituationen
            hierarchie: Optionale Gebietshierarchie für Filterung
            gueltig_am: Datum, für das die Varianten gültig sein müssen
            
        Returns:
            Liste von passenden Leistungsvarianten
        """
        return self.leistung_repo.suche_by_lebenssituation(
            lebenssituationen, hierarchie, gueltig_am
        )
    
    def get_anspruchsregel(self, regel_id: str) -> Optional[Anspruchsregel]:
        """Holt eine Anspruchsregel"""
        return self.leistung_repo.get_anspruchsregel(regel_id)
    
    def get_verfahren(self, verfahrens_id: str) -> Optional[Verfahren]:
        """Holt ein Verfahren"""
        return self.leistung_repo.get_verfahren(verfahrens_id)
    
    def get_zustaendigkeit(self, zustaendigkeit_id: str) -> Optional[Zustaendigkeit]:
        """Holt eine Zuständigkeit"""
        return self.leistung_repo.get_zustaendigkeit(zustaendigkeit_id)
    
    def get_quelle(self, quelle_id: str) -> Optional[Quelle]:
        """Holt eine Quelle"""
        return self.leistung_repo.get_quelle(quelle_id)
    
    def get_best_variante(
        self,
        leistung_id: str,
        hierarchie: List[Gebiet]
    ) -> Optional[Leistungsvariante]:
        """
        Findet die beste (spezifischste) Variante für eine Leistung
        in einer gegebenen Hierarchie.
        
        Args:
            leistung_id: ID der Leistung
            hierarchie: Gebietshierarchie (z.B. [Gemeinde, Kreis, Land, Bund])
            
        Returns:
            Die spezifischste gültige Variante oder None
        """
        # Varianten für diese Leistung holen
        alle_varianten = self.get_varianten_for_leistung(leistung_id)
        
        # Nach Hierarchie-Ebene filtern und sortieren
        # Priorität: Gemeinde > Kreis > Land > Bund
        ebene_prioritaet = {
            GebietsEbene.GEMEINDE: 0,
            GebietsEbene.KREIS: 1,
            GebietsEbene.LAND: 2,
            GebietsEbene.BUND: 3
        }
        
        # Gebiete in der Hierarchie für schnellen Zugriff
        hierarchie_gebiete = {g.id: g for g in hierarchie}
        
        # Passende Varianten finden
        passende = []
        for variante in alle_varianten:
            if not variante.ist_gueltig():
                continue
            
            # Prüfen, ob das Gebiet der Variante in der Hierarchie ist
            gebiet = self.get_gebiet_by_id(variante.gebiet_id)
            if gebiet and gebiet.id in hierarchie_gebiete:
                passende.append((variante, ebene_prioritaet.get(gebiet.ebene, 99)))
        
        if not passende:
            return None
        
        # Nach Priorität sortieren (niedrigste Zahl = höchste Priorität)
        passende.sort(key=lambda x: x[1])
        
        return passende[0][0]
