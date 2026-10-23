"""
AnspruchsExperte - Experte für die Prüfung von Ansprüchen auf Leistungen
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import date

from ...models import (
    Leistungsvariante, Anspruchsregel, Bedingung, Operator
)
from ...knowledge_base import KnowledgeBase


class AnspruchsExperte:
    """
    Experte für die Prüfung von Ansprüchen auf Leistungen.
    
    Verantwortlich für:
    - Prüfung, ob ein Profil die Bedingungen für eine Leistung erfüllt
    - Berechnung des voraussichtlichen Anspruchs
    - Generierung von Begründungen
    """
    
    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None):
        """
        Initialisiert den AnspruchsExperten.
        
        Args:
            knowledge_base: Knowledge Base für den Datenzugriff
        """
        self.kb = knowledge_base or KnowledgeBase()
        
    def pruefe_anspruch(
        self,
        variante: Leistungsvariante,
        profil: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prüft, ob ein Profil Anspruch auf eine Leistungsvariante hat.
        
        Args:
            variante: Die zu prüfende Variante
            profil: Das Profil der Antragstellerin
            
        Returns:
            Dictionary mit:
            - ergebnis: "ja", "nein" oder "unklar"
            - begründung: Liste von Begründungen
            - details: Zusätzliche Details
        """
        result = {
            "ergebnis": "unklar",
            "begründung": [],
            "details": {}
        }
        
        # Wenn keine Anspruchsregel definiert ist, ist der Status unklar
        if not variante.hat_anspruchsregel():
            result["begründung"].append(
                f"Keine Anspruchsregel für diese Variante definiert "
                f"(Abdeckungsstatus: {variante.abdeckungsstatus.value})"
            )
            return result
        
        # Anspruchsregel holen
        regel = self.kb.get_anspruchsregel(variante.anspruchsregel_id)
        
        if not regel:
            result["begründung"].append(
                f"Anspruchsregel {variante.anspruchsregel_id} nicht gefunden"
            )
            return result
        
        # Regel prüfen
        if not regel.ist_gueltig():
            result["begründung"].append(
                f"Anspruchsregel ist nicht mehr gültig (gültig bis: {regel.gueltig_bis})"
            )
            result["ergebnis"] = "nein"
            return result
        
        # Alle Bedingungen prüfen
        alle_erfüllt, nicht_erfüllte = regel.prüfe_alle_bedingungen(profil)
        
        if alle_erfüllt:
            result["ergebnis"] = "ja"
            result["begründung"].append("Alle Bedingungen sind erfüllt.")
        else:
            result["ergebnis"] = "nein"
            result["begründung"].extend(nicht_erfüllte)
        
        # Details hinzufügen
        result["details"] = {
            "regel_id": regel.id,
            "regel_name": regel.name,
            "anzahl_bedingungen": len(regel.bedingungen),
            "erfüllte_bedingungen": len(regel.bedingungen) - len(nicht_erfüllte)
        }
        
        return result
    
    def prüfe_alle_varianten(
        self,
        varianten: List[Leistungsvariante],
        profil: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Prüft den Anspruch für alle Varianten.
        
        Args:
            varianten: Liste von Varianten
            profil: Das Profil
            
        Returns:
            Liste von Prüfergebnissen
        """
        ergebnisse = []
        
        for variante in varianten:
            ergebnis = self.pruefe_anspruch(variante, profil)
            ergebnis["variante_id"] = variante.id
            ergebnis["leistung_id"] = variante.leistung_id
            ergebnisse.append(ergebnis)
        
        return ergebnisse
    
    def get_anspruchsregel(self, regel_id: str) -> Optional[Anspruchsregel]:
        """
        Holt eine Anspruchsregel.
        
        Args:
            regel_id: ID der Regel
            
        Returns:
            Die Regel oder None
        """
        return self.kb.get_anspruchsregel(regel_id)
    
    def create_bedingung(
        self,
        feld: str,
        operator: Operator,
        wert: Any,
        beschreibung: Optional[str] = None,
        reihenfolge: int = 0
    ) -> Bedingung:
        """
        Erstellt eine neue Bedingung.
        
        Args:
            feld: Das zu prüfende Feld
            operator: Der Vergleichsoperator
            wert: Der zu vergleichende Wert
            beschreibung: Beschreibung der Bedingung
            reihenfolge: Reihenfolge der Prüfung
            
        Returns:
            Die erstellte Bedingung
        """
        return Bedingung(
            feld=feld,
            operator=operator,
            wert=wert,
            beschreibung=beschreibung,
            reihenfolge=reihenfolge
        )
    
    def prüfe_manuelle_bedingung(
        self,
        bedingung: Bedingung,
        profil_wert: Any
    ) -> bool:
        """
        Prüft eine einzelne Bedingung manuell.
        
        Args:
            bedingung: Die zu prüfende Bedingung
            profil_wert: Der Wert aus dem Profil
            
        Returns:
            True, wenn die Bedingung erfüllt ist
        """
        return bedingung.prüfe(profil_wert)
