"""
Repository für Gebiete
"""

from typing import Optional, List, Dict
from datetime import date
import json
import os

from ..models import Gebiet, GebietsEbene


class GebietRepository:
    """
    Repository für den Zugriff auf Gebietsdaten.
    
    Lädt Gebiete aus JSON-Dateien und bietet Methoden für den Zugriff.
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialisiert das Repository.
        
        Args:
            data_dir: Verzeichnis mit den Gebietsdaten (Default: data/gebiete)
        """
        self.data_dir = data_dir or os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "data", "gebiete"
        )
        self._gebiete: Dict[str, Gebiet] = {}
        self._plz_index: Dict[str, str] = {}
        self._ags_index: Dict[str, str] = {}
        self._loaded = False
        
    def _load_data(self):
        """Lädt die Gebietsdaten aus JSON-Dateien"""
        if self._loaded:
            return
        
        self._gebiete = {}
        self._plz_index = {}
        self._ags_index = {}
        
        # Dateien im data_dir laden
        if os.path.exists(self.data_dir):
            for filename in os.listdir(self.data_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(self.data_dir, filename)
                    self._load_json_file(filepath)
        
        # Standard-Bund hinzufügen, falls nicht vorhanden
        if "bund" not in self._gebiete:
            bund = Gebiet(
                id="bund",
                name="Deutschland",
                ebene=GebietsEbene.BUND,
                ags="00"
            )
            self._gebiete[bund.id] = bund
            self._ags_index[bund.ags] = bund.id
        
        self._loaded = True
    
    def _load_json_file(self, filepath: str):
        """Lädt eine einzelne JSON-Datei"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data.get("gebiete", []):
            gebiet = self._parse_gebiet(item)
            self._gebiete[gebiet.id] = gebiet
            self._ags_index[gebiet.ags] = gebiet.id
            
            for plz in gebiet.plz_bereich:
                self._plz_index[plz] = gebiet.id
    
    def _parse_gebiet(self, data: Dict) -> Gebiet:
        """Parsed ein Gebiet aus Dictionary-Daten"""
        return Gebiet(
            id=data.get("id", str(len(self._gebiete))),
            name=data["name"],
            ebene=GebietsEbene(data["ebene"]),
            ags=data["ags"],
            parent_id=data.get("parent_id"),
            plz_bereich=data.get("plz_bereich", []),
            gueltig_ab=date.fromisoformat(data.get("gueltig_ab", "1900-01-01")),
            gueltig_bis=date.fromisoformat(data.get("gueltig_bis")) 
                     if data.get("gueltig_bis") else None
        )
    
    def get_by_plz(self, plz: str) -> Optional[Gebiet]:
        """Holt das Gebiet für eine gegebene PLZ"""
        self._load_data()
        
        # Exakte Übereinstimmung
        gebiet_id = self._plz_index.get(plz)
        if gebiet_id:
            return self._gebiete.get(gebiet_id)
        
        # PLZ-Präfix suchen (z.B. "80" für München)
        for prefix, gebiet_id in self._plz_index.items():
            if plz.startswith(prefix):
                gebiet = self._gebiete.get(gebiet_id)
                if gebiet:
                    return gebiet
        
        return None
    
    def get_by_ags(self, ags: str) -> Optional[Gebiet]:
        """Holt das Gebiet für einen gegebenen AGS"""
        self._load_data()
        
        gebiet_id = self._ags_index.get(ags)
        if gebiet_id:
            return self._gebiete.get(gebiet_id)
        
        return None
    
    def get_by_id(self, gebiet_id: str) -> Optional[Gebiet]:
        """Holt das Gebiet für eine gegebene ID"""
        self._load_data()
        return self._gebiete.get(gebiet_id)
    
    def get_all(self) -> List[Gebiet]:
        """Holt alle Gebiete"""
        self._load_data()
        return list(self._gebiete.values())
    
    def resolve_hierarchie(self, plz: str) -> List[Gebiet]:
        """
        Löst die vollständige Gebietshierarchie für eine PLZ auf.
        
        Args:
            plz: Postleitzahl
            
        Returns:
            Liste von Gebieten in der Reihenfolge: [Gemeinde, Kreis, Land, Bund]
        """
        self._load_data()
        
        # Start mit dem Gebiet für die PLZ
        gebiet = self.get_by_plz(plz)
        if not gebiet:
            # Fallback: Bund
            bund = self.get_by_ags("00")
            if bund:
                return [bund]
            return []
        
        # Hierarchie aufbauen
        hierarchie = []
        aktuell = gebiet
        
        while aktuell:
            hierarchie.append(aktuell)
            if aktuell.parent_id:
                aktuell = self.get_by_id(aktuell.parent_id)
            else:
                aktuell = None
        
        # Bund hinzufügen, falls nicht vorhanden
        if hierarchie[-1].ebene != GebietsEbene.BUND:
            bund = self.get_by_ags("00")
            if bund:
                hierarchie.append(bund)
        
        return hierarchie
    
    def get_children(self, gebiet_id: str) -> List[Gebiet]:
        """Holt alle untergeordneten Gebiete"""
        self._load_data()
        
        children = []
        for gebiet in self._gebiete.values():
            if gebiet.parent_id == gebiet_id:
                children.append(gebiet)
        
        return children
    
    def get_by_ebene(self, ebene: GebietsEbene) -> List[Gebiet]:
        """Holt alle Gebiete einer bestimmten Ebene"""
        self._load_data()
        
        return [g for g in self._gebiete.values() if g.ebene == ebene]
