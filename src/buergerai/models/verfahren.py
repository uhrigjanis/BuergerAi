"""
Verfahrensmodell für die Abwicklung von Leistungen
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List
import uuid


@dataclass
class Unterlage:
    """
    Eine Unterlage, die für ein Verfahren benötigt wird.
    
    Attribute:
        id: Eindeutige Identifikationsnummer
        name: Name der Unterlage (z.B. "Geburtsurkunde")
        beschreibung: Beschreibung der Unterlage
        pflicht: Ob die Unterlage zwingend erforderlich ist
        reihenfolge: Reihenfolge in der Liste
    """
    id: str
    name: str
    beschreibung: Optional[str] = None
    pflicht: bool = True
    reihenfolge: int = 0
    
    def __post_init__(self):
        """Validierung nach Initialisierung"""
        if self.id is None:
            object.__setattr__(self, 'id', str(uuid.uuid4()))


@dataclass
class Verfahrensschritt:
    """
    Ein Schritt im Verfahren.
    
    Attribute:
        id: Eindeutige Identifikationsnummer
        beschreibung: Beschreibung des Schritts
        geschatzte_dauer_minuten: Geschätzte Bearbeitungsdauer
        reihenfolge: Reihenfolge im Verfahren
    """
    id: str
    beschreibung: str
    geschatzte_dauer_minuten: Optional[int] = None
    reihenfolge: int = 0
    
    def __post_init__(self):
        """Validierung nach Initialisierung"""
        if self.id is None:
            object.__setattr__(self, 'id', str(uuid.uuid4()))


@dataclass
class Verfahren:
    """
    Repräsentiert das Verfahren zur Beantragung einer Leistung.
    
    Attribute:
        id: Eindeutige Identifikationsnummer
        formular_link: Link zum Antragsformular
        bearbeitungsdauer_tage: Geschätzte Bearbeitungsdauer in Tagen
        frist_tage: Frist für die Beantragung in Tagen (ab Ereignis)
        koste: Kosten für die Beantragung
        unterlagen: Liste der benötigten Unterlagen
        schritte: Liste der Verfahrensschritte
    """
    id: str
    formular_link: Optional[str] = None
    bearbeitungsdauer_tage: Optional[int] = None
    frist_tage: Optional[int] = None
    koste: Optional[float] = None
    unterlagen: List[Unterlage] = field(default_factory=list)
    schritte: List[Verfahrensschritt] = field(default_factory=list)
    
    def __post_init__(self):
        """Validierung nach Initialisierung"""
        if self.id is None:
            object.__setattr__(self, 'id', str(uuid.uuid4()))
    
    def add_unterlage(self, unterlage: Unterlage):
        """Fügt eine Unterlage hinzu"""
        self.unterlagen.append(unterlage)
        self.unterlagen.sort(key=lambda u: u.reihenfolge)
    
    def add_schritt(self, schritt: Verfahrensschritt):
        """Fügt einen Verfahrensschritt hinzu"""
        self.schritte.append(schritt)
        self.schritte.sort(key=lambda s: s.reihenfolge)
    
    def get_gesamtdauer_minuten(self) -> int:
        """Berechnet die geschätzte Gesamtdauer aller Schritte"""
        return sum(s.geschatzte_dauer_minuten or 0 for s in self.schritte)
