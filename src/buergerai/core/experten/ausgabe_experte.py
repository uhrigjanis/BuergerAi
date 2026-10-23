"""
AusgabeExperte - Experte für die Generierung von Checklisten und Ausgaben
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import date

from ...models import (
    Leistungsvariante, Abdeckungsstatus, GebietsHierarchie, Gebiet
)
from ...knowledge_base import KnowledgeBase
from .anspruchs_experte import AnspruchsExperte
from .verfahrens_experte import VerfahrensExperte
from .abhaengigkeits_experte import AbhaengigkeitsExperte


class AusgabeExperte:
    """
    Experte für die Generierung von Checklisten und Ausgaben.
    
    Verantwortlich für:
    - Generierung priorisierter Checklisten
    - Formatierung der Ergebnisse
    - Zusammenfassung von Informationen
    """
    
    def __init__(
        self,
        anspruchs_experte: Optional[AnspruchsExperte] = None,
        verfahrens_experte: Optional[VerfahrensExperte] = None,
        abhaengigkeits_experte: Optional[AbhaengigkeitsExperte] = None,
        knowledge_base: Optional[KnowledgeBase] = None
    ):
        """
        Initialisiert den AusgabeExperten.
        
        Args:
            anspruchs_experte: AnspruchsExperte für die Prüfung
            verfahrens_experte: VerfahrensExperte für Verfahrensdaten
            abhaengigkeits_experte: AbhängigkeitsExperte für Reihenfolge
            knowledge_base: Knowledge Base für den Datenzugriff
        """
        self.anspruchs_experte = anspruchs_experte or AnspruchsExperte(knowledge_base)
        self.verfahrens_experte = verfahrens_experte or VerfahrensExperte(knowledge_base)
        self.abhaengigkeits_experte = abhaengigkeits_experte or AbhaengigkeitsExperte(knowledge_base)
        self.kb = knowledge_base or KnowledgeBase()
        
    def generate_checkliste(
        self,
        varianten: List[Leistungsvariante],
        profil: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generiert eine priorisierte Checkliste aus Leistungsvarianten.
        
        Die Checkliste wird sortiert nach:
        1. Dringlichkeit (Fristen: kürzeste zuerst)
        2. Abhängigkeiten (Leistungen ohne Voraussetzungen zuerst)
        3. Relevanz (Wahrscheinlichkeit des Anspruchs: Ja > Unklar > Nein)
        
        Args:
            varianten: Liste von Leistungsvarianten
            profil: Das Profil der Antragstellerin
            
        Returns:
            Liste von Checklisten-Einträgen, sortiert nach Priorität
        """
        checkliste = []
        
        # Für jede Variante Anspruch prüfen und Verfahrensdaten holen
        for variante in varianten:
            anspruch = self.anspruchs_experte.pruefe_anspruch(variante, profil)
            verfahren = self.verfahrens_experte.get_verfahren(variante.verfahrens_id) if variante.verfahrens_id else {}
            zustaendigkeit = self.verfahrens_experte.get_zustaendigkeit(variante.zustaendigkeit_id) if variante.zustaendigkeit_id else {}
            
            # Leistung-Name holen
            leistung = self.kb.get_leistung_by_id(variante.leistung_id)
            leistung_name = leistung.name if leistung else variante.leistung_id
            
            # Checklisten-Eintrag erstellen
            eintrag = {
                "leistung_id": variante.leistung_id,
                "leistung_name": leistung_name,
                "variante_id": variante.id,
                "anspruch": anspruch["ergebnis"],
                "begründung": anspruch["begründung"],
                "zustaendigkeit": zustaendigkeit,
                "frist_tage": verfahren.get("frist_tage"),
                "unterlagen": verfahren.get("unterlagen", []),
                "formular_link": verfahren.get("formular_link"),
                "schritte": verfahren.get("schritte", []),
                "bearbeitungsdauer_tage": verfahren.get("bearbeitungsdauer_tage"),
                "koste": verfahren.get("koste"),
                "quellen": variante.quellen,
                "abdeckungsstatus": variante.abdeckungsstatus.value,
                "details": anspruch.get("details", {})
            }
            checkliste.append(eintrag)
        
        # Abhängigkeiten prüfen und Reihenfolge anpassen
        leistung_ids = [e["leistung_id"] for e in checkliste]
        
        # Nur Varianten mit gültigen Leistung-IDs
        valid_varianten = [
            v for v in varianten 
            if v.leistung_id in leistung_ids and v.ist_gueltig()
        ]
        
        reihenfolge = self.abhaengigkeits_experte.get_reihenfolge(valid_varianten)
        
        # Priorisieren
        checkliste = self._priorisiere(checkliste, reihenfolge)
        
        return checkliste
    
    def _priorisiere(
        self,
        checkliste: List[Dict[str, Any]],
        reihenfolge: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Priorisiert die Checkliste nach:
        1. Dringlichkeit (Fristen)
        2. Abhängigkeiten (Reihenfolge)
        3. Anspruch (Ja > Unklar > Nein)
        
        Args:
            checkliste: Liste von Checklisten-Einträgen
            reihenfolge: Liste von Leistungs-IDs in der Abhängigkeits-Reihenfolge
            
        Returns:
            Priorisierte Checkliste
        """
        # 1. Nach Frist sortieren (kürzeste Frist zuerst)
        checkliste.sort(key=lambda x: x.get("frist_tage") or float('inf'))
        
        # 2. Nach Abhängigkeiten sortieren (Leistungen ohne Voraussetzungen zuerst)
        reihenfolge_index = {leistung_id: idx for idx, leistung_id in enumerate(reihenfolge)}
        checkliste.sort(key=lambda x: reihenfolge_index.get(x["leistung_id"], float('inf')))
        
        # 3. Nach Anspruch sortieren (Ja > Unklar > Nein)
        anspruch_prioritaet = {
            "ja": 0,
            "unklar": 1,
            "nein": 2
        }
        checkliste.sort(key=lambda x: anspruch_prioritaet.get(x["anspruch"], 3))
        
        return checkliste
    
    def generate_zusammenfassung(
        self,
        checkliste: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generiert eine Zusammenfassung der Checkliste.
        
        Args:
            checkliste: Die Checkliste
            
        Returns:
            Dictionary mit Zusammenfassungsinformationen
        """
        # Nach Anspruch gruppieren
        nach_anspruch = {"ja": [], "unklar": [], "nein": []}
        for eintrag in checkliste:
            nach_anspruch.setdefault(eintrag["anspruch"], []).append(eintrag)
        
        # Statistik
        statistik = {
            "gesamt": len(checkliste),
            "anspruch_ja": len(nach_anspruch["ja"]),
            "anspruch_unklar": len(nach_anspruch["unklar"]),
            "anspruch_nein": len(nach_anspruch["nein"]),
            "dringend": len([e for e in checkliste if e.get("frist_tage", 999) <= 7]),
            "mit_formular": len([e for e in checkliste if e.get("formular_link")]),
            "kostenpflichtig": len([e for e in checkliste if e.get("koste", 0) > 0])
        }
        
        # Nächste Schritte
        naechste_schritte = [
            e for e in checkliste 
            if e["anspruch"] == "ja" and e.get("frist_tage")
        ]
        naechste_schritte.sort(key=lambda x: x["frist_tage"])
        
        return {
            "statistik": statistik,
            "nach_anspruch": nach_anspruch,
            "naechste_schritte": naechste_schritte[:5],  # Top 5
            "gesamte_bearbeitungsdauer_tage": sum(
                e.get("bearbeitungsdauer_tage", 0) or 0 
                for e in checkliste 
                if e["anspruch"] == "ja"
            )
        }
    
    def format_checkliste_markdown(
        self,
        checkliste: List[Dict[str, Any]],
        title: str = "Ihre Leistungen"
    ) -> str:
        """
        Formatiert die Checkliste als Markdown.
        
        Args:
            checkliste: Die Checkliste
            title: Titel der Checkliste
            
        Returns:
            Markdown-String
        """
        md = f"# {title}\n\n"
        
        # Dringende Leistungen (Frist <= 7 Tage)
        dringend = [e for e in checkliste if e.get("frist_tage", 999) <= 7 and e["anspruch"] == "ja"]
        if dringend:
            md += "## 🔴 DRINGEND\n\n"
            for e in sorted(dringend, key=lambda x: x.get("frist_tage", 0)):
                md += self._format_eintrag_markdown(e)
            md += "\n"
        
        # Nächste Schritte (Anspruch: Ja)
        naechste = [e for e in checkliste if e["anspruch"] == "ja"]
        if naechste:
            md += "## ✅ NÄCHSTE SCHRITTE\n\n"
            for e in naechste:
                md += self._format_eintrag_markdown(e)
            md += "\n"
        
        # Unklare Ansprüche
        unklar = [e for e in checkliste if e["anspruch"] == "unklar"]
        if unklar:
            md += "## ⚠️ OPTIONAL / UNKLAR\n\n"
            for e in unklar:
                md += self._format_eintrag_markdown(e)
            md += "\n"
        
        # Kein Anspruch
        nein = [e for e in checkliste if e["anspruch"] == "nein"]
        if nein:
            md += "## ❌ KEIN ANSPRUCH\n\n"
            for e in nein:
                md += self._format_eintrag_markdown(e)
        
        return md
    
    def _format_eintrag_markdown(self, eintrag: Dict[str, Any]) -> str:
        """Formatiert einen einzelnen Eintrag als Markdown"""
        md = f"### {eintrag['leistung_name']}\n"
        
        # Anspruch
        anspruch_icons = {"ja": "✅", "unklar": "⚠️", "nein": "❌"}
        md += f"- Anspruch: {anspruch_icons.get(eintrag['anspruch'], '❓')} {eintrag['anspruch'].upper()}\n"
        
        # Begründung
        if eintrag["begründung"]:
            md += f"- Begründung: {'; '.join(eintrag['begründung'])}\n"
        
        # Frist
        if eintrag.get("frist_tage"):
            md += f"- Frist: {eintrag['frist_tage']} Tage\n"
        
        # Zuständigkeit
        zustaendigkeit = eintrag.get("zustaendigkeit", {})
        if zustaendigkeit.get("behoerde_name"):
            md += f"- Zuständig: {zustaendigkeit['behoerde_name']}\n"
        
        # Unterlagen
        unterlagen = eintrag.get("unterlagen", [])
        if unterlagen:
            unterlagen_text = ", ".join([u["name"] for u in unterlagen if u.get("pflicht", True)])
            md += f"- Unterlagen: {unterlagen_text}\n"
        
        # Formular-Link
        if eintrag.get("formular_link"):
            md += f"- Formular: [{eintrag['formular_link']}]({eintrag['formular_link']})\n"
        
        # Kosten
        if eintrag.get("koste"):
            md += f"- Kosten: {eintrag['koste']} €\n"
        
        # Abdeckungsstatus
        if eintrag.get("abdeckungsstatus") != "verifiziert":
            md += f"- Hinweis: Datenstatus: {eintrag['abdeckungsstatus']}\n"
        
        # Quellen
        quellen = eintrag.get("quellen", [])
        if quellen:
            quellen_text = ", ".join(quellen)
            md += f"- Quellen: {quellen_text}\n"
        
        md += "\n"
        
        return md
    
    def get_leistung_name(self, leistung_id: str) -> str:
        """
        Holt den Namen einer Leistung.
        
        Args:
            leistung_id: ID der Leistung
            
        Returns:
            Name der Leistung oder die ID, wenn nicht gefunden
        """
        leistung = self.kb.get_leistung_by_id(leistung_id)
        return leistung.name if leistung else leistung_id
