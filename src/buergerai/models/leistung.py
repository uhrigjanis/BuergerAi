"""
Leistungsmodell für öffentliche Leistungen
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List
import uuid


@dataclass
class Leistungskategorie:
    """Kategorie für die Klassifizierung von Leistungen"""
    id: str
    name: str
    beschreibung: Optional[str] = None
    
    def __post_init__(self):
        """Validierung nach Initialisierung"""
        if self.id is None:
            object.__setattr__(self, 'id', str(uuid.uuid4()))


@dataclass
class Leistungstag:
    """Tag zur Klassifizierung von Leistungen"""
    id: str
    name: str
    
    def __post_init__(self):
        """Validierung nach Initialisierung"""
        if self.id is None:
            object.__setattr__(self, 'id', str(uuid.uuid4()))


@dataclass
class Leistung:
    """
    Repräsentiert eine abstrakte öffentliche Leistung.
    
    Attribute:
        id: Eindeutige Identifikationsnummer
        name: Name der Leistung (z.B. "Elterngeld")
        beschreibung: Ausführliche Beschreibung
        kurzbeschreibung: Kurze Zusammenfassung
    """
    id: str
    name: str
    beschreibung: Optional[str] = None
    kurzbeschreibung: Optional[str] = None
    kategorien: List[Leistungskategorie] = field(default_factory=list)
    tags: List[Leistungstag] = field(default_factory=list)
    erstellungsdatum: date = field(default_factory=date.today)
    letze_aenderung: date = field(default_factory=date.today)
    
    def __post_init__(self):
        """Validierung nach Initialisierung"""
        if self.id is None:
            object.__setattr__(self, 'id', str(uuid.uuid4()))
    
    def add_kategorie(self, kategorie: Leistungskategorie):
        """Fügt eine Kategorie hinzu"""
        if kategorie not in self.kategorien:
            self.kategorien.append(kategorie)
    
    def add_tag(self, tag: Leistungstag):
        """Fügt einen Tag hinzu"""
        if tag not in self.tags:
            self.tags.append(tag)
