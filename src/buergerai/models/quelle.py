"""
Quellenmodell für die Nachverfolgbarkeit von Informationen
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional
import uuid


class QuellenTyp(Enum):
    """Typen von Quellen"""
    AMTLICH = "amtlich"        # Offizielle behördliche Quelle
    PORTAL = "portal"          # Behördliches Portal
    GESETZ = "gesetz"          # Gesetzestext
    SONSTIGES = "sonstiges"    # Andere vertrauenswürdige Quelle


@dataclass
class Quelle:
    """
    Repräsentiert eine Quelle für Informationen.
    
    Jede Information in der Knowledge Base sollte mit einer Quelle
    verknüpft sein, um die Nachverfolgbarkeit zu gewährleisten.
    
    Attribute:
        id: Eindeutige Identifikationsnummer
        name: Name der Quelle (z.B. "LeiKa")
        url: URL der Quelle
        typ: Typ der Quelle
        beschreibung: Beschreibung der Quelle
    """
    id: str
    name: str
    url: Optional[str] = None
    typ: QuellenTyp = QuellenTyp.SONSTIGES
    beschreibung: Optional[str] = None
    
    def __post_init__(self):
        """Validierung nach Initialisierung"""
        if self.id is None:
            object.__setattr__(self, 'id', str(uuid.uuid4()))
    
    def get_zitat(self) -> str:
        """Generiert ein Zitat für die Quelle"""
        if self.url:
            return f"[{self.name}]({self.url})"
        return self.name
