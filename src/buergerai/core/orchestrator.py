"""
Orchestrator - Koordiniert alle Experten und führt den Haupt-Workflow aus
"""

from typing import Optional, List, Dict, Any
from datetime import date

from ..models import (
    Leistungsvariante, Gebiet
)
from ..knowledge_base import KnowledgeBase
from .experten import (
    GebietsExperte,
    LeistungsExperte,
    ProfilExperte,
    AnspruchsExperte,
    VerfahrensExperte,
    AbhaengigkeitsExperte,
    AusgabeExperte
)

# Typ-Alias für Hierarchie-Pfade
GebietsHierarchie = List[Gebiet]


class Orchestrator:
    """
    Koordiniert alle Experten und führt den Haupt-Workflow aus.
    
    Verantwortlich für:
    - Empfang von Anfragen von der UI
    - Aufruf der Experten in der richtigen Reihenfolge
    - Aggregation der Ergebnisse
    - Lösung von Abhängigkeiten zwischen Leistungen
    - Priorisierung von Checklisten
    """
    
    def __init__(
        self,
        knowledge_base: Optional[KnowledgeBase] = None,
        session_storage: Optional[Dict[str, Any]] = None
    ):
        """
        Initialisiert den Orchestrator.
        
        Args:
            knowledge_base: Knowledge Base für den Datenzugriff
            session_storage: Dictionary für Session-Speicherung
        """
        self.kb = knowledge_base or KnowledgeBase()
        self.session_storage = session_storage or {}
        
        # Experten initialisieren
        self.gebiets_experte = GebietsExperte(self.kb)
        self.leistungs_experte = LeistungsExperte(self.kb)
        self.profil_experte = ProfilExperte(self.session_storage)
        self.anspruchs_experte = AnspruchsExperte(self.kb)
        self.verfahrens_experte = VerfahrensExperte(self.kb)
        self.abhaengigkeits_experte = AbhaengigkeitsExperte(self.kb)
        self.ausgabe_experte = AusgabeExperte(
            self.anspruchs_experte,
            self.verfahrens_experte,
            self.abhaengigkeits_experte,
            self.kb
        )
    
    def process_request(
        self,
        session_id: str,
        plz: str,
        lebenssituationen: List[str],
        profil_updates: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Haupt-Workflow: Verarbeitet eine User-Anfrage und gibt eine Checkliste zurück.
        
        Args:
            session_id: ID der User-Session
            plz: Postleitzahl des Wohnorts
            lebenssituationen: Liste von Lebenssituationen
            profil_updates: Optionale Updates für das Profil
            
        Returns:
            Priorisierte Checkliste mit allen relevanten Leistungen
        """
        # 1. Profil aktualisieren oder erstellen
        if profil_updates:
            profil = self.profil_experte.update_profil(session_id, profil_updates)
        else:
            profil = self.profil_experte.get_profil(session_id)
            if not profil:
                profil = self.profil_experte.create_profil(session_id, plz)
        
        # 2. Gebietsauflösung
        hierarchie = self.gebiets_experte.resolve_hierarchie(plz)
        
        # 3. Leistungen suchen
        varianten = self.leistungs_experte.suche_leistungen(
            lebenssituationen, hierarchie
        )
        
        # 4. Checkliste generieren
        checkliste = self.ausgabe_experte.generate_checkliste(varianten, profil)
        
        return checkliste
    
    def process_request_with_details(
        self,
        session_id: str,
        plz: str,
        lebenssituationen: List[str],
        profil_updates: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Verarbeitet eine Anfrage und gibt detaillierte Ergebnisse zurück.
        
        Args:
            session_id: ID der User-Session
            plz: Postleitzahl des Wohnorts
            lebenssituationen: Liste von Lebenssituationen
            profil_updates: Optionale Updates für das Profil
            
        Returns:
            Dictionary mit:
            - checkliste: Die priorisierte Checkliste
            - zusammenfassung: Zusammenfassende Statistik
            - profil: Das aktuelle Profil
            - hierarchie: Die aufgelöste Gebietshierarchie
        """
        # Checkliste generieren
        checkliste = self.process_request(
            session_id, plz, lebenssituationen, profil_updates
        )
        
        # Zusammenfassung generieren
        zusammenfassung = self.ausgabe_experte.generate_zusammenfassung(checkliste)
        
        # Profil holen
        profil = self.profil_experte.get_profil(session_id)
        
        # Hierarchie holen
        hierarchie = self.gebiets_experte.resolve_hierarchie(plz)
        
        return {
            "checkliste": checkliste,
            "zusammenfassung": zusammenfassung,
            "profil": profil,
            "hierarchie": [
                {
                    "id": g.id,
                    "name": g.name,
                    "ebene": g.ebene.value,
                    "ags": g.ags
                }
                for g in hierarchie
            ]
        }
    
    def get_checkliste_markdown(
        self,
        session_id: str,
        plz: str,
        lebenssituationen: List[str],
        profil_updates: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None
    ) -> str:
        """
        Verarbeitet eine Anfrage und gibt die Checkliste als Markdown zurück.
        
        Args:
            session_id: ID der User-Session
            plz: Postleitzahl des Wohnorts
            lebenssituationen: Liste von Lebenssituationen
            profil_updates: Optionale Updates für das Profil
            title: Optionaler Titel für die Checkliste
            
        Returns:
            Markdown-String mit der Checkliste
        """
        # Checkliste generieren
        checkliste = self.process_request(
            session_id, plz, lebenssituationen, profil_updates
        )
        
        # Titel generieren, falls nicht angegeben
        if not title:
            situation_text = ", ".join(lebenssituationen)
            title = f"Ihre Leistungen ({situation_text}, {plz})"
        
        # Als Markdown formatieren
        return self.ausgabe_experte.format_checkliste_markdown(checkliste, title)
    
    def validate_request(
        self,
        plz: str,
        lebenssituationen: List[str]
    ) -> Dict[str, Any]:
        """
        Validiert eine Anfrage.
        
        Args:
            plz: Postleitzahl
            lebenssituationen: Liste von Lebenssituationen
            
        Returns:
            Dictionary mit Validierungsergebnissen
        """
        fehler = []
        warnungen = []
        
        # PLZ validieren
        if not self.gebiets_experte.validate_plz(plz):
            fehler.append(f"PLZ {plz} ist ungültig oder nicht in der Datenbank")
        
        # Lebenssituationen prüfen
        if not lebenssituationen:
            fehler.append("Mindestens eine Lebenssituation muss angegeben werden")
        
        # Prüfen, ob Lebenssituationen bekannt sind
        alle_leistungen = self.leistungs_experte.get_all_leistungen()
        alle_tags = set()
        for leistung in alle_leistungen:
            alle_tags.update(tag.name for tag in leistung.tags)
        
        for situation in lebenssituationen:
            if situation not in alle_tags:
                warnungen.append(f"Lebenssituation '{situation}' ist nicht in der Datenbank")
        
        return {
            "gueltig": len(fehler) == 0,
            "fehler": fehler,
            "warnungen": warnungen
        }
