"""
AbhängigkeitsExperte - Experte für Abhängigkeiten zwischen Leistungen
"""

from typing import Optional, List, Dict, Any, Set, Tuple
from datetime import date
import networkx as nx

from ...models import Leistungsvariante, Gebiet
from ...knowledge_base import KnowledgeBase

# Typ-Alias für Hierarchie-Pfade
GebietsHierarchie = List[Gebiet]


class AbhaengigkeitsExperte:
    """
    Experte für Abhängigkeiten zwischen Leistungen.
    
    Verantwortlich für:
    - Verwaltung des Abhängigkeitsgraphen
    - Bestimmung der optimalen Reihenfolge für die Beantragung
    - Erkennung von Voraussetzungen
    """
    
    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None):
        """
        Initialisiert den AbhängigkeitsExperten.
        
        Args:
            knowledge_base: Knowledge Base für den Datenzugriff
        """
        self.kb = knowledge_base or KnowledgeBase()
        self._graph = self._build_graph()
        
    def _build_graph(self) -> nx.DiGraph:
        """
        Baut den Abhängigkeitsgraphen aus den Daten.
        
        Der Graph enthält:
        - Knoten: Leistungs-IDs
        - Kanten: Abhängigkeiten (A -> B bedeutet: A muss vor B beantragt werden)
        
        Returns:
            Gerichteter Graph
        """
        graph = nx.DiGraph()
        
        # Abhängigkeiten aus den Daten laden
        # (In einer echten Implementierung würden diese aus einer Datenbank
        # oder Konfigurationsdatei geladen werden)
        
        # Standard-Abhängigkeiten für häufige Szenarien
        abhaengigkeiten = [
            # Geburt
            ("geburtsurkunde", "elterngeld"),
            ("geburtsurkunde", "kindergeld"),
            ("geburtsurkunde", "mutterschaftsgeld"),
            ("geburtsurkunde", "bayerisches_familiengeld"),
            
            # Heirat
            ("heiratsurkunde", "elterngeld"),  # Für Stiefkinder
            
            # Umzug
            ("wohnsitzanmeldung", "kindergeld"),
            
            # Allgemein
            ("steuer_id", "kindergeld"),
            ("steuer_id", "elterngeld"),
            ("krankenversicherung", "mutterschaftsgeld"),
        ]
        
        for quelle, ziel in abhaengigkeiten:
            graph.add_edge(quelle, ziel)
        
        return graph
    
    def get_reihenfolge(
        self,
        varianten: List[Leistungsvariante]
    ) -> List[str]:
        """
        Bestimmt die optimale Reihenfolge für die Beantragung von Leistungen.
        
        Args:
            varianten: Liste von Leistungsvarianten
            
        Returns:
            Liste von Leistungs-IDs in der optimalen Reihenfolge
        """
        # Leistungs-IDs extrahieren
        leistung_ids = [v.leistung_id for v in varianten]
        
        # Teilgraph für die gegebenen Leistungen erstellen
        subgraph = self._graph.subgraph(leistung_ids)
        
        # Topologische Sortierung für Abhängigkeiten
        try:
            reihenfolge = list(nx.topological_sort(subgraph))
        except nx.NetworkXError:
            # Zyklus erkannt - Fallback: einfache Sortierung
            reihenfolge = sorted(leistung_ids)
        
        # Leistungen ohne Abhängigkeiten zuerst
        # (Diese sind nicht im Graphen oder haben keine eingehenden Kanten)
        unabhaengige = [
            lid for lid in leistung_ids 
            if lid not in reihenfolge and lid in self._graph
        ]
        
        # Kombinieren: Unabhängige zuerst, dann abhängige in topologischer Reihenfolge
        return unabhaengige + reihenfolge
    
    def get_voraussetzungen(
        self,
        leistung_id: str
    ) -> List[str]:
        """
        Gibt die Voraussetzungen für eine Leistung zurück.
        
        Args:
            leistung_id: ID der Leistung
            
        Returns:
            Liste von Leistungs-IDs, die Voraussetzungen sind
        """
        if leistung_id not in self._graph:
            return []
        
        # Alle Vorgänger im Graphen
        return list(self._graph.predecessors(leistung_id))
    
    def get_abhaengige(
        self,
        leistung_id: str
    ) -> List[str]:
        """
        Gibt die Leistungen zurück, die von dieser Leistung abhängen.
        
        Args:
            leistung_id: ID der Leistung
            
        Returns:
            Liste von Leistungs-IDs, die abhängig sind
        """
        if leistung_id not in self._graph:
            return []
        
        # Alle Nachfolger im Graphen
        return list(self._graph.successors(leistung_id))
    
    def hat_abhaengigkeit(
        self,
        leistung_a: str,
        leistung_b: str
    ) -> bool:
        """
        Prüft, ob Leistung A eine Voraussetzung für Leistung B ist.
        
        Args:
            leistung_a: ID der ersten Leistung
            leistung_b: ID der zweiten Leistung
            
        Returns:
            True, wenn A Voraussetzung für B ist
        """
        return self._graph.has_edge(leistung_a, leistung_b)
    
    def get_abhaengigkeits_pfad(
        self,
        leistung_a: str,
        leistung_b: str
    ) -> Optional[List[str]]:
        """
        Findet einen Pfad von Leistung A zu Leistung B im Abhängigkeitsgraphen.
        
        Args:
            leistung_a: Start-Leistung
            leistung_b: Ziel-Leistung
            
        Returns:
            Liste von Leistungs-IDs auf dem Pfad oder None, wenn kein Pfad existiert
        """
        try:
            pfad = nx.shortest_path(self._graph, leistung_a, leistung_b)
            return pfad
        except nx.NetworkXNoPath:
            return None
    
    def add_abhaengigkeit(
        self,
        voraussetzung: str,
        abhaengig: str
    ):
        """
        Fügt eine neue Abhängigkeit hinzu.
        
        Args:
            voraussetzung: ID der Voraussetzungs-Leistung
            abhaengig: ID der abhängigen Leistung
        """
        self._graph.add_edge(voraussetzung, abhaengig)
    
    def remove_abhaengigkeit(
        self,
        voraussetzung: str,
        abhaengig: str
    ):
        """
        Entfernt eine Abhängigkeit.
        
        Args:
            voraussetzung: ID der Voraussetzungs-Leistung
            abhaengig: ID der abhängigen Leistung
        """
        if self._graph.has_edge(voraussetzung, abhaengig):
            self._graph.remove_edge(voraussetzung, abhaengig)
