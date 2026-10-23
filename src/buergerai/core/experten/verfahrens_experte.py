"""
VerfahrensExperte - Experte für Verfahrensdaten
"""

from typing import Optional, List, Dict, Any
from datetime import date

from ...models import Verfahren, Unterlage, Verfahrensschritt, Zustaendigkeit
from ...knowledge_base import KnowledgeBase


class VerfahrensExperte:
    """
    Experte für Verfahrensdaten.
    
    Verantwortlich für:
    - Bereitstellung von Verfahrensinformationen
    - Auflistung benötigter Unterlagen
    - Beschreibung der Verfahrensschritte
    """
    
    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None):
        """
        Initialisiert den VerfahrensExperten.
        
        Args:
            knowledge_base: Knowledge Base für den Datenzugriff
        """
        self.kb = knowledge_base or KnowledgeBase()
        
    def get_verfahren(self, verfahrens_id: str) -> Optional[Dict[str, Any]]:
        """
        Holt die Verfahrensdaten für eine Variante.
        
        Args:
            verfahrens_id: ID des Verfahrens
            
        Returns:
            Dictionary mit Verfahrensdaten oder None
        """
        verfahren = self.kb.get_verfahren(verfahrens_id)
        
        if not verfahren:
            return None
        
        return {
            "id": verfahren.id,
            "formular_link": verfahren.formular_link,
            "bearbeitungsdauer_tage": verfahren.bearbeitungsdauer_tage,
            "frist_tage": verfahren.frist_tage,
            "koste": verfahren.koste,
            "unterlagen": [
                {
                    "name": u.name,
                    "beschreibung": u.beschreibung,
                    "pflicht": u.pflicht,
                    "reihenfolge": u.reihenfolge
                }
                for u in verfahren.unterlagen
            ],
            "schritte": [
                {
                    "beschreibung": s.beschreibung,
                    "geschatzte_dauer_minuten": s.geschatzte_dauer_minuten,
                    "reihenfolge": s.reihenfolge
                }
                for s in verfahren.schritte
            ],
            "gesamtdauer_minuten": verfahren.get_gesamtdauer_minuten()
        }
    
    def get_zustaendigkeit(self, zustaendigkeit_id: str) -> Optional[Dict[str, Any]]:
        """
        Holt die Zuständigkeitsdaten.
        
        Args:
            zustaendigkeit_id: ID der Zuständigkeit
            
        Returns:
            Dictionary mit Zuständigkeitsdaten oder None
        """
        zustaendigkeit = self.kb.get_zustaendigkeit(zustaendigkeit_id)
        
        if not zustaendigkeit:
            return None
        
        return {
            "id": zustaendigkeit.id,
            "behoerde_name": zustaendigkeit.behoerde_name,
            "behoerde_kontakt": zustaendigkeit.behoerde_kontakt,
            "portal_link": zustaendigkeit.portal_link,
            "post_adresse": zustaendigkeit.post_adresse
        }
    
    def get_unterlagen(self, verfahrens_id: str) -> List[Dict[str, Any]]:
        """
        Holt die benötigten Unterlagen für ein Verfahren.
        
        Args:
            verfahrens_id: ID des Verfahrens
            
        Returns:
            Liste von Unterlagen
        """
        verfahren = self.kb.get_verfahren(verfahrens_id)
        
        if not verfahren:
            return []
        
        return [
            {
                "name": u.name,
                "beschreibung": u.beschreibung,
                "pflicht": u.pflicht,
                "reihenfolge": u.reihenfolge
            }
            for u in verfahren.unterlagen
        ]
    
    def get_schritte(self, verfahrens_id: str) -> List[Dict[str, Any]]:
        """
        Holt die Verfahrensschritte für ein Verfahren.
        
        Args:
            verfahrens_id: ID des Verfahrens
            
        Returns:
            Liste von Verfahrensschritten
        """
        verfahren = self.kb.get_verfahren(verfahrens_id)
        
        if not verfahren:
            return []
        
        return [
            {
                "beschreibung": s.beschreibung,
                "geschatzte_dauer_minuten": s.geschatzte_dauer_minuten,
                "reihenfolge": s.reihenfolge
            }
            for s in verfahren.schritte
        ]
    
    def get_bearbeitungsdauer(self, verfahrens_id: str) -> Optional[int]:
        """
        Holt die Bearbeitungsdauer in Tagen.
        
        Args:
            verfahrens_id: ID des Verfahrens
            
        Returns:
            Bearbeitungsdauer in Tagen oder None
        """
        verfahren = self.kb.get_verfahren(verfahrens_id)
        
        if not verfahren:
            return None
        
        return verfahren.bearbeitungsdauer_tage
    
    def get_frist(self, verfahrens_id: str) -> Optional[int]:
        """
        Holt die Frist in Tagen.
        
        Args:
            verfahrens_id: ID des Verfahrens
            
        Returns:
            Frist in Tagen oder None
        """
        verfahren = self.kb.get_verfahren(verfahrens_id)
        
        if not verfahren:
            return None
        
        return verfahren.frist_tage
    
    def get_kosten(self, verfahrens_id: str) -> Optional[float]:
        """
        Holt die Kosten für ein Verfahren.
        
        Args:
            verfahrens_id: ID des Verfahrens
            
        Returns:
            Kosten oder None
        """
        verfahren = self.kb.get_verfahren(verfahrens_id)
        
        if not verfahren:
            return None
        
        return verfahren.koste
    
    def get_formular_link(self, verfahrens_id: str) -> Optional[str]:
        """
        Holt den Link zum Antragsformular.
        
        Args:
            verfahrens_id: ID des Verfahrens
            
        Returns:
            URL des Formulars oder None
        """
        verfahren = self.kb.get_verfahren(verfahrens_id)
        
        if not verfahren:
            return None
        
        return verfahren.formular_link
