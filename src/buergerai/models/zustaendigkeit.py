"""
Zuständigkeitsmodell für Behörden
"""

from dataclasses import dataclass, field
from typing import Optional, List
import uuid


@dataclass
class Behoerde:
    """
    Repräsentiert eine Behörde.
    
    Attribute:
        id: Eindeutige Identifikationsnummer
        name: Name der Behörde
        kontakt: Kontaktdaten (E-Mail, Telefon)
        portal_link: Link zum Online-Portal
        post_adresse: Postadresse
    """
    id: str
    name: str
    kontakt: Optional[str] = None
    portal_link: Optional[str] = None
    post_adresse: Optional[str] = None
    
    def __post_init__(self):
        """Validierung nach Initialisierung"""
        if self.id is None:
            object.__setattr__(self, 'id', str(uuid.uuid4()))


@dataclass
class Zustaendigkeit:
    """
    Repräsentiert die Zuständigkeit für eine Leistung.
    
    Attribute:
        id: Eindeutige Identifikationsnummer
        behoerde: Die zuständige Behörde
        behörden_name: Name der Behörde (für schnellen Zugriff)
        behörden_kontakt: Kontaktdaten
        portal_link: Link zum Online-Portal
        post_adresse: Postadresse
    """
    id: str
    behoerde: Optional[Behoerde] = None
    behoerde_name: str = ""
    behoerde_kontakt: Optional[str] = None
    portal_link: Optional[str] = None
    post_adresse: Optional[str] = None
    
    def __post_init__(self):
        """Validierung nach Initialisierung"""
        if self.id is None:
            object.__setattr__(self, 'id', str(uuid.uuid4()))
    
    def __post_init__(self):
        """Synchronisiert behörden_name mit behoerde"""
        if self.behoerde and not self.behoerde_name:
            self.behoerde_name = self.behoerde.name
        if self.behoerde and not self.behoerde_kontakt:
            self.behoerde_kontakt = self.behoerde.kontakt
        if self.behoerde and not self.portal_link:
            self.portal_link = self.behoerde.portal_link
        if self.behoerde and not self.post_adresse:
            self.post_adresse = self.behoerde.post_adresse
