"""
Repository für Leistungen und deren Varianten
"""

from typing import Optional, List, Dict, Set
from datetime import date
import json
import os

from ..models import (
    Leistung, Leistungskategorie, Leistungstag, Leistungsvariante,
    Abdeckungsstatus, Anspruchsregel, Bedingung, Operator,
    Verfahren, Unterlage, Verfahrensschritt, Zustaendigkeit,
    Behoerde, Quelle, QuellenTyp
)


class LeistungRepository:
    """
    Repository für den Zugriff auf Leistungsdaten.
    
    Lädt Leistungen, Varianten, Regeln und Verfahren aus JSON-Dateien.
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialisiert das Repository.
        
        Args:
            data_dir: Verzeichnis mit den Leistungsdaten (Default: data/leistungen)
        """
        self.data_dir = data_dir or os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "data", "leistungen"
        )
        
        self._leistungen: Dict[str, Leistung] = {}
        self._varianten: Dict[str, Leistungsvariante] = {}
        self._regeln: Dict[str, Anspruchsregel] = {}
        self._verfahren: Dict[str, Verfahren] = {}
        self._zustaendigkeiten: Dict[str, Zustaendigkeit] = {}
        self._behoerden: Dict[str, Behoerde] = {}
        self._quellen: Dict[str, Quelle] = {}
        
        # Indizes für schnellen Zugriff
        self._leistung_varianten_index: Dict[str, List[str]] = {}  # leistung_id -> [variante_id]
        self._gebiet_varianten_index: Dict[str, List[str]] = {}  # gebiet_id -> [variante_id]
        self._leistung_tags_index: Dict[str, Set[str]] = {}  # tag -> Set[leistung_id]
        
        self._loaded = False
        
    def _load_data(self):
        """Lädt alle Daten aus JSON-Dateien"""
        if self._loaded:
            return
        
        # Leistungen laden
        self._load_leistungen()
        
        # Varianten laden
        self._load_varianten()
        
        # Regeln laden
        self._load_regeln()
        
        # Verfahren laden
        self._load_verfahren()
        
        # Zuständigkeiten laden
        self._load_zustaendigkeiten()
        
        # Quellen laden
        self._load_quellen()
        
        # Indizes aufbauen
        self._build_indices()
        
        self._loaded = True
    
    def _load_leistungen(self):
        """Lädt Leistungen aus JSON-Dateien"""
        self._leistungen = {}
        
        # Standard-Kategorien
        kategorien_data = {
            "familie": {"name": "Familie", "beschreibung": "Leistungen für Familien"},
            "soziales": {"name": "Soziales", "beschreibung": "Soziale Leistungen"},
            "gesundheit": {"name": "Gesundheit", "beschreibung": "Gesundheitsleistungen"}
        }
        
        self._kategorien = {}
        for kat_id, data in kategorien_data.items():
            kat = Leistungskategorie(
                id=kat_id,
                name=data["name"],
                beschreibung=data.get("beschreibung")
            )
            self._kategorien[kat_id] = kat
        
        # Standard-Tags
        tags_data = [
            "Schwangerschaft", "Geburt", "Heirat", "Scheidung", "Umzug",
            "Arbeitslosigkeit", "Rente", "Krankheit", "Pflege", "Behindertengeld"
        ]
        
        self._tags = {}
        for tag_name in tags_data:
            tag = Leistungstag(id=tag_name.lower().replace(" ", "_"), name=tag_name)
            self._tags[tag.id] = tag
        
        # Leistungen aus Dateien laden
        if os.path.exists(self.data_dir):
            for filename in os.listdir(self.data_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(self.data_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    for item in data.get("leistungen", []):
                        leistung = self._parse_leistung(item)
                        self._leistungen[leistung.id] = leistung
    
    def _load_varianten(self):
        """Lädt Leistungsvarianten aus JSON-Dateien"""
        self._varianten = {}
        
        if os.path.exists(self.data_dir):
            for filename in os.listdir(self.data_dir):
                if filename.startswith("varianten") and filename.endswith(".json"):
                    filepath = os.path.join(self.data_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    for item in data.get("varianten", []):
                        variante = self._parse_variante(item)
                        self._varianten[variante.id] = variante
    
    def _load_regeln(self):
        """Lädt Anspruchsregeln aus JSON-Dateien"""
        self._regeln = {}
        
        if os.path.exists(os.path.join(self.data_dir, "..", "regeln")):
            regeln_dir = os.path.join(self.data_dir, "..", "regeln")
            for filename in os.listdir(regeln_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(regeln_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    for item in data.get("regeln", []):
                        regel = self._parse_regel(item)
                        self._regeln[regel.id] = regel
    
    def _load_verfahren(self):
        """Lädt Verfahren aus JSON-Dateien"""
        self._verfahren = {}
        
        if os.path.exists(os.path.join(self.data_dir, "..", "verfahren")):
            verfahren_dir = os.path.join(self.data_dir, "..", "verfahren")
            for filename in os.listdir(verfahren_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(verfahren_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    for item in data.get("verfahren", []):
                        verfahren = self._parse_verfahren(item)
                        self._verfahren[verfahren.id] = verfahren
    
    def _load_zustaendigkeiten(self):
        """Lädt Zuständigkeiten aus JSON-Dateien"""
        self._zustaendigkeiten = {}
        
        if os.path.exists(os.path.join(self.data_dir, "..", "zustaendigkeiten")):
            zustaendigkeiten_dir = os.path.join(self.data_dir, "..", "zustaendigkeiten")
            for filename in os.listdir(zustaendigkeiten_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(zustaendigkeiten_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    for item in data.get("zustaendigkeiten", []):
                        zustaendigkeit = self._parse_zustaendigkeit(item)
                        self._zustaendigkeiten[zustaendigkeit.id] = zustaendigkeit
    
    def _load_quellen(self):
        """Lädt Quellen aus JSON-Dateien"""
        self._quellen = {}
        
        if os.path.exists(os.path.join(self.data_dir, "..", "quellen")):
            quellen_dir = os.path.join(self.data_dir, "..", "quellen")
            for filename in os.listdir(quellen_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(quellen_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    for item in data.get("quellen", []):
                        quelle = self._parse_quelle(item)
                        self._quellen[quelle.id] = quelle
    
    def _parse_leistung(self, data: Dict) -> Leistung:
        """Parsed eine Leistung aus Dictionary-Daten"""
        leistung = Leistung(
            id=data.get("id", str(len(self._leistungen))),
            name=data["name"],
            beschreibung=data.get("beschreibung"),
            kurzbeschreibung=data.get("kurzbeschreibung")
        )
        
        # Kategorien hinzufügen
        for kat_id in data.get("kategorien", []):
            if kat_id in self._kategorien:
                leistung.add_kategorie(self._kategorien[kat_id])
        
        # Tags hinzufügen
        for tag_name in data.get("tags", []):
            tag_id = tag_name.lower().replace(" ", "_")
            if tag_id in self._tags:
                leistung.add_tag(self._tags[tag_id])
        
        return leistung
    
    def _parse_variante(self, data: Dict) -> Leistungsvariante:
        """Parsed eine Leistungsvariante aus Dictionary-Daten"""
        return Leistungsvariante(
            id=data.get("id", str(len(self._varianten))),
            leistung_id=data["leistung_id"],
            gebiet_id=data["gebiet_id"],
            anspruchsregel_id=data.get("anspruchsregel_id"),
            zustaendigkeit_id=data.get("zustaendigkeit_id"),
            verfahrens_id=data.get("verfahrens_id"),
            abdeckungsstatus=Abdeckungsstatus(data.get("abdeckungsstatus", "unbekannt")),
            gueltig_ab=date.fromisoformat(data.get("gueltig_ab", "1900-01-01")),
            gueltig_bis=date.fromisoformat(data.get("gueltig_bis")) 
                       if data.get("gueltig_bis") else None,
            quellen=data.get("quellen", [])
        )
    
    def _parse_regel(self, data: Dict) -> Anspruchsregel:
        """Parsed eine Anspruchsregel aus Dictionary-Daten"""
        regel = Anspruchsregel(
            id=data.get("id", str(len(self._regeln))),
            name=data["name"],
            beschreibung=data.get("beschreibung"),
            gueltig_ab=date.fromisoformat(data.get("gueltig_ab", "1900-01-01")),
            gueltig_bis=date.fromisoformat(data.get("gueltig_bis")) 
                       if data.get("gueltig_bis") else None
        )
        
        # Bedingungen hinzufügen
        for bedingung_data in data.get("bedingungen", []):
            bedingung = self._parse_bedingung(bedingung_data)
            regel.add_bedingung(bedingung)
        
        return regel
    
    def _parse_bedingung(self, data: Dict) -> Bedingung:
        """Parsed eine Bedingung aus Dictionary-Daten"""
        return Bedingung(
            id=data.get("id", str(len(self._regeln) * 100 + len(self._regeln.get(data.get("regel_id", ""), [])))),
            feld=data["feld"],
            operator=Operator(data["operator"]),
            wert=data["wert"],
            beschreibung=data.get("beschreibung"),
            reihenfolge=data.get("reihenfolge", 0)
        )
    
    def _parse_verfahren(self, data: Dict) -> Verfahren:
        """Parsed ein Verfahren aus Dictionary-Daten"""
        verfahren = Verfahren(
            id=data.get("id", str(len(self._verfahren))),
            formular_link=data.get("formular_link"),
            bearbeitungsdauer_tage=data.get("bearbeitungsdauer_tage"),
            frist_tage=data.get("frist_tage"),
            koste=data.get("koste")
        )
        
        # Unterlagen hinzufügen
        for unterlage_data in data.get("unterlagen", []):
            unterlage = Unterlage(
                id=unterlage_data.get("id", str(len(self._verfahren) * 100 + len(verfahren.unterlagen))),
                name=unterlage_data["name"],
                beschreibung=unterlage_data.get("beschreibung"),
                pflicht=unterlage_data.get("pflicht", True),
                reihenfolge=unterlage_data.get("reihenfolge", 0)
            )
            verfahren.add_unterlage(unterlage)
        
        # Schritte hinzufügen
        for schritt_data in data.get("schritte", []):
            schritt = Verfahrensschritt(
                id=schritt_data.get("id", str(len(self._verfahren) * 1000 + len(verfahren.schritte))),
                beschreibung=schritt_data["beschreibung"],
                geschatzte_dauer_minuten=schritt_data.get("geschatzte_dauer_minuten"),
                reihenfolge=schritt_data.get("reihenfolge", 0)
            )
            verfahren.add_schritt(schritt)
        
        return verfahren
    
    def _parse_zustaendigkeit(self, data: Dict) -> Zustaendigkeit:
        """Parsed eine Zuständigkeit aus Dictionary-Daten"""
        zustaendigkeit = Zustaendigkeit(
            id=data.get("id", str(len(self._zustaendigkeiten))),
            behoerde_name=data["behoerde_name"],
            behoerde_kontakt=data.get("behoerde_kontakt"),
            portal_link=data.get("portal_link"),
            post_adresse=data.get("post_adresse")
        )
        
        return zustaendigkeit
    
    def _parse_quelle(self, data: Dict) -> Quelle:
        """Parsed eine Quelle aus Dictionary-Daten"""
        return Quelle(
            id=data.get("id", str(len(self._quellen))),
            name=data["name"],
            url=data.get("url"),
            typ=QuellenTyp(data.get("typ", "sonstiges")),
            beschreibung=data.get("beschreibung")
        )
    
    def _build_indices(self):
        """Baut Indizes für schnellen Zugriff auf"""
        # Leistung -> Varianten Index
        self._leistung_varianten_index = {}
        for variante_id, variante in self._varianten.items():
            if variante.leistung_id not in self._leistung_varianten_index:
                self._leistung_varianten_index[variante.leistung_id] = []
            self._leistung_varianten_index[variante.leistung_id].append(variante_id)
        
        # Gebiet -> Varianten Index
        self._gebiet_varianten_index = {}
        for variante_id, variante in self._varianten.items():
            if variante.gebiet_id not in self._gebiet_varianten_index:
                self._gebiet_varianten_index[variante.gebiet_id] = []
            self._gebiet_varianten_index[variante.gebiet_id].append(variante_id)
        
        # Tag -> Leistungen Index
        self._leistung_tags_index = {}
        for leistung_id, leistung in self._leistungen.items():
            for tag in leistung.tags:
                if tag.name not in self._leistung_tags_index:
                    self._leistung_tags_index[tag.name] = set()
                self._leistung_tags_index[tag.name].add(leistung_id)
    
    def get_by_id(self, leistung_id: str) -> Optional[Leistung]:
        """Holt eine Leistung für eine gegebene ID"""
        self._load_data()
        return self._leistungen.get(leistung_id)
    
    def get_by_name(self, name: str) -> Optional[Leistung]:
        """Holt eine Leistung für einen gegebenen Namen"""
        self._load_data()
        
        for leistung in self._leistungen.values():
            if leistung.name.lower() == name.lower():
                return leistung
        
        return None
    
    def get_varianten_for_leistung(self, leistung_id: str) -> List[Leistungsvariante]:
        """Holt alle Varianten für eine Leistung"""
        self._load_data()
        
        variante_ids = self._leistung_varianten_index.get(leistung_id, [])
        return [self._varianten[vid] for vid in variante_ids]
    
    def get_varianten_for_gebiet(self, gebiet_id: str) -> List[Leistungsvariante]:
        """Holt alle Varianten für ein Gebiet"""
        self._load_data()
        
        variante_ids = self._gebiet_varianten_index.get(gebiet_id, [])
        return [self._varianten[vid] for vid in variante_ids]
    
    def suche_by_tags(
        self,
        tags: List[str],
        hierarchie: Optional[List] = None,
        gueltig_am: Optional[date] = None
    ) -> List[Leistungsvariante]:
        """Sucht Leistungsvarianten nach Tags"""
        self._load_data()
        
        # Leistungen mit passenden Tags finden
        passende_leistung_ids = set()
        for tag in tags:
            if tag in self._leistung_tags_index:
                if not passende_leistung_ids:
                    passende_leistung_ids = self._leistung_tags_index[tag].copy()
                else:
                    passende_leistung_ids &= self._leistung_tags_index[tag]
        
        if not passende_leistung_ids:
            return []
        
        # Varianten für diese Leistungen holen
        varianten = []
        for leistung_id in passende_leistung_ids:
            varianten.extend(self.get_varianten_for_leistung(leistung_id))
        
        # Nach Gültigkeit filtern
        if gueltig_am is None:
            gueltig_am = date.today()
        
        varianten = [v for v in varianten if v.ist_gueltig(gueltig_am)]
        
        # Nach Hierarchie filtern (falls angegeben)
        if hierarchie:
            hierarchie_ids = {g.id for g in hierarchie}
            varianten = [v for v in varianten if v.gebiet_id in hierarchie_ids]
        
        return varianten
    
    def suche_by_lebenssituation(
        self,
        lebenssituationen: List[str],
        hierarchie: Optional[List] = None,
        gueltig_am: Optional[date] = None
    ) -> List[Leistungsvariante]:
        """Sucht Leistungsvarianten nach Lebenssituationen (Tags)"""
        return self.suche_by_tags(lebenssituationen, hierarchie, gueltig_am)
    
    def get_anspruchsregel(self, regel_id: str) -> Optional[Anspruchsregel]:
        """Holt eine Anspruchsregel"""
        self._load_data()
        return self._regeln.get(regel_id)
    
    def get_verfahren(self, verfahrens_id: str) -> Optional[Verfahren]:
        """Holt ein Verfahren"""
        self._load_data()
        return self._verfahren.get(verfahrens_id)
    
    def get_zustaendigkeit(self, zustaendigkeit_id: str) -> Optional[Zustaendigkeit]:
        """Holt eine Zuständigkeit"""
        self._load_data()
        return self._zustaendigkeiten.get(zustaendigkeit_id)
    
    def get_quelle(self, quelle_id: str) -> Optional[Quelle]:
        """Holt eine Quelle"""
        self._load_data()
        return self._quellen.get(quelle_id)
    
    def get_all_leistungen(self) -> List[Leistung]:
        """Holt alle Leistungen"""
        self._load_data()
        return list(self._leistungen.values())
    
    def get_all_varianten(self) -> List[Leistungsvariante]:
        """Holt alle Varianten"""
        self._load_data()
        return list(self._varianten.values())
