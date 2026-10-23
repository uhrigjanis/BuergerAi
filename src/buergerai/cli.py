#!/usr/bin/env python
"""
BuergerAI - Command Line Interface

Ein interaktives Terminal-Tool zum Testen der BuergerAI-Anwendung.

Usage:
    # Interaktiver Modus
    python -m buergerai
    
    # Direkte Abfrage
    python -m buergerai --plz 80331 --situationen Schwangerschaft Geburt
    
    # Mit Profil-Daten
    python -m buergerai --plz 80331 --situationen Schwangerschaft --alter 30 --einkommen 50000
    
    # Ausgabe als JSON
    python -m buergerai --plz 80331 --situationen Schwangerschaft --format json
    
    # Hilfe
    python -m buergerai --help
"""

import argparse
import json
import sys
from typing import List, Dict, Any, Optional

# Füge src zum Pfad hinzu, falls nicht bereits vorhanden
import os
src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from buergerai.core import Orchestrator


class CLIColors:
    """Farben für die Terminal-Ausgabe"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class BuergerAICLI:
    """
    Command Line Interface für BuergerAI.
    
    Bietet einen interaktiven Modus und direkte Abfragen.
    """
    
    def __init__(self):
        """Initialisiert die CLI"""
        self.orchestrator = Orchestrator()
        self.colors = CLIColors()
        self.session_id = "cli_session"
        
    def run(self):
        """Führt die CLI aus."""
        parser = self._create_parser()
        args = sys.argv[1:]
        
        # Wenn keine Argumente, interaktiver Modus
        if len(args) == 0:
            self._interactive_mode()
        else:
            # Command-Line-Modus
            parsed_args = parser.parse_args(args)
            self._handle_args(parsed_args)
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Erstellt den Argument-Parser"""
        parser = argparse.ArgumentParser(
            description='BuergerAI - Teste die Identifikation von Ansprüchen auf öffentliche Leistungen',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Beispiele:
  python -m buergerai --plz 80331 --situationen Schwangerschaft Geburt
  python -m buergerai --plz 10115 --situationen Heirat
  python -m buergerai --plz 80331 --situationen Schwangerschaft --format markdown
  python -m buergerai --plz 80331 --situationen Schwangerschaft --alter 30 --einkommen 50000
            """
        )
        
        # Positionale Argumente
        parser.add_argument(
            '--plz',
            type=str,
            help='Postleitzahl (z.B. 80331 für München)'
        )
        
        parser.add_argument(
            '--situationen',
            '--situation',
            nargs='+',
            default=[],
            help='Lebenssituationen (z.B. Schwangerschaft Geburt Heirat)'
        )
        
        # Profil-Argumente
        profil_group = parser.add_argument_group('Profil-Optionen')
        profil_group.add_argument(
            '--alter',
            type=int,
            help='Alter der Antragstellerin'
        )
        profil_group.add_argument(
            '--einkommen',
            type=float,
            help='Jährliches Einkommen'
        )
        profil_group.add_argument(
            '--kinder',
            type=int,
            default=0,
            help='Anzahl der Kinder'
        )
        profil_group.add_argument(
            '--schwanger',
            action='store_true',
            help='Schwangerschaft vorhanden'
        )
        profil_group.add_argument(
            '--geburt',
            action='store_true',
            help='Geburt vorhanden'
        )
        
        # AusgabefORMAT
        parser.add_argument(
            '--format',
            choices=['text', 'markdown', 'json'],
            default='text',
            help='Ausgabeformat (Default: text)'
        )
        
        # Validierung
        parser.add_argument(
            '--validate',
            action='store_true',
            help='Validiert die Anfrage ohne Ausführung'
        )
        
        # Verbose Modus
        parser.add_argument(
            '--verbose',
            '-v',
            action='store_true',
            help='Ausführliche Ausgabe'
        )
        
        return parser
    
    def _handle_args(self, args: argparse.Namespace):
        """Verarbeitet die Command-Line-Argumente"""
        
        # Validierung
        if args.validate:
            self._validate_and_exit(args)
        
        # PLZ ist erforderlich
        if not args.plz:
            print(f"{self.colors.FAIL}Fehler: PLZ ist erforderlich!{self.colors.END}")
            print("Verwende --help für mehr Informationen")
            sys.exit(1)
        
        # Lebenssituationen sind erforderlich
        if not args.situationen:
            print(f"{self.colors.FAIL}Fehler: Mindestens eine Lebenssituation ist erforderlich!{self.colors.END}")
            print("Verwende --help für mehr Informationen")
            sys.exit(1)
        
        # Profil-Daten zusammenstellen
        profil_updates = self._build_profil(args)
        
        # Anfrage verarbeiten
        try:
            if args.format == 'json':
                result = self.orchestrator.process_request_with_details(
                    self.session_id, args.plz, args.situationen, profil_updates
                )
                self._output_json(result)
            elif args.format == 'markdown':
                markdown = self.orchestrator.get_checkliste_markdown(
                    self.session_id, args.plz, args.situationen, profil_updates
                )
                self._output_markdown(markdown)
            else:
                result = self.orchestrator.process_request_with_details(
                    self.session_id, args.plz, args.situationen, profil_updates
                )
                self._output_text(result, verbose=args.verbose)
        
        except Exception as e:
            print(f"{self.colors.FAIL}Fehler: {e}{self.colors.END}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
    
    def _validate_and_exit(self, args: argparse.Namespace):
        """Validiert die Anfrage und beendet das Programm"""
        result = self.orchestrator.validate_request(
            args.plz or "",
            args.situationen
        )
        
        if result['gueltig']:
            print(f"{self.colors.OKGREEN}✓ Anfrage ist gültig{self.colors.END}")
        else:
            print(f"{self.colors.FAIL}✗ Anfrage ist ungültig{self.colors.END}")
            if result['fehler']:
                print(f"\n{self.colors.FAIL}Fehler:{self.colors.END}")
                for fehler in result['fehler']:
                    print(f"  - {fehler}")
            if result['warnungen']:
                print(f"\n{self.colors.WARNING}Warnungen:{self.colors.END}")
                for warnung in result['warnungen']:
                    print(f"  - {warnung}")
        
        sys.exit(0 if result['gueltig'] else 1)
    
    def _build_profil(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Baut das Profil aus den Command-Line-Argumenten"""
        profil = {}
        
        if args.alter is not None:
            profil['haushalt'] = profil.get('haushalt', {})
            profil['haushalt']['antragstellerin'] = profil['haushalt'].get('antragstellerin', {})
            profil['haushalt']['antragstellerin']['alter'] = args.alter
        
        if args.einkommen is not None:
            profil['haushalt'] = profil.get('haushalt', {})
            profil['haushalt']['antragstellerin'] = profil['haushalt'].get('antragstellerin', {})
            profil['haushalt']['antragstellerin']['einkommen_jaehrlich'] = args.einkommen
        
        if args.kinder > 0:
            profil['haushalt'] = profil.get('haushalt', {})
            profil['haushalt']['kinder'] = [{'alter': 0} for _ in range(args.kinder)]
        
        if args.schwanger:
            profil['situation'] = profil.get('situation', {})
            profil['situation']['schwangerschaft'] = {'vorhanden': True, 'anzahl_kinder': 1}
        
        if args.geburt:
            profil['situation'] = profil.get('situation', {})
            profil['situation']['geburt'] = {'vorhanden': True, 'anzahl_kinder': 1}
        
        return profil
    
    def _interactive_mode(self):
        """Interaktiver Modus"""
        print(self._get_header())
        
        # PLZ abfragen
        plz = self._input_plz()
        
        # Lebenssituationen abfragen
        situationen = self._input_situationen()
        
        # Profil-Daten abfragen
        profil_updates = self._input_profil()
        
        # AusgabefORMAT abfragen
        output_format = self._input_format()
        
        # Anfrage verarbeiten
        try:
            if output_format == 'json':
                result = self.orchestrator.process_request_with_details(
                    self.session_id, plz, situationen, profil_updates
                )
                self._output_json(result)
            elif output_format == 'markdown':
                markdown = self.orchestrator.get_checkliste_markdown(
                    self.session_id, plz, situationen, profil_updates
                )
                self._output_markdown(markdown)
            else:
                result = self.orchestrator.process_request_with_details(
                    self.session_id, plz, situationen, profil_updates
                )
                self._output_text(result, verbose=True)
        
        except Exception as e:
            print(f"\n{self.colors.FAIL}Fehler: {e}{self.colors.END}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def _get_header(self) -> str:
        """Gibt den Header zurück"""
        return f"""
{self.colors.HEADER}{self.colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                                                               ║
║     {self.colors.HEADER}🏛️  BuergerAI - Bürgerleistungen identifizieren{self.colors.END}{self.colors.HEADER}     ║
║                                                               ║
║  Teste, welche Leistungen dir in deiner Situation zustehen  ║
║                                                               ║
╚══════════════════════════════════════════════════════════════╝{self.colors.END}
"""
    
    def _input_plz(self) -> str:
        """Fragt nach der PLZ"""
        while True:
            try:
                plz = input(f"\n{self.colors.BOLD}Postleitzahl:{self.colors.END} ").strip()
                if len(plz) == 5 and plz.isdigit():
                    return plz
                print(f"{self.colors.FAIL}Ungültige PLZ. Bitte 5 Ziffern eingeben.{self.colors.END}")
            except (EOFError, KeyboardInterrupt):
                print("\nAbbruch durch Benutzer")
                sys.exit(0)
    
    def _input_situationen(self) -> List[str]:
        """Fragt nach den Lebenssituationen"""
        print(f"\n{self.colors.BOLD}Lebenssituationen (z.B. Schwangerschaft, Geburt, Heirat):{self.colors.END}")
        print("Verfügbare Optionen: Schwangerschaft, Geburt, Heirat, Umzug, Arbeitslosigkeit, Rente")
        
        situationen = []
        while True:
            try:
                situation = input(f"  {len(situationen) + 1}. Situation (Enter zum Beenden): ").strip()
                if not situation:
                    if situationen:
                        break
                    print(f"{self.colors.FAIL}Mindestens eine Situation ist erforderlich!{self.colors.END}")
                else:
                    situationen.append(situation)
            except (EOFError, KeyboardInterrupt):
                if situationen:
                    break
                print("\nAbbruch durch Benutzer")
                sys.exit(0)
        
        return situationen
    
    def _input_profil(self) -> Dict[str, Any]:
        """Fragt nach Profil-Daten"""
        profil = {}
        
        print(f"\n{self.colors.BOLD}Profil-Daten (optional, Enter zum Überspringen):{self.colors.END}")
        
        try:
            # Alter
            alter_input = input("  Alter: ").strip()
            if alter_input and alter_input.isdigit():
                profil['haushalt'] = profil.get('haushalt', {})
                profil['haushalt']['antragstellerin'] = profil['haushalt'].get('antragstellerin', {})
                profil['haushalt']['antragstellerin']['alter'] = int(alter_input)
            
            # Einkommen
            einkommen_input = input("  Jährliches Einkommen (€): ").strip()
            if einkommen_input:
                try:
                    einkommen = float(einkommen_input.replace('.', '').replace(',', '.'))
                    profil['haushalt'] = profil.get('haushalt', {})
                    profil['haushalt']['antragstellerin'] = profil['haushalt'].get('antragstellerin', {})
                    profil['haushalt']['antragstellerin']['einkommen_jaehrlich'] = einkommen
                except ValueError:
                    print(f"{self.colors.FAIL}Ungültiges Einkommen!{self.colors.END}")
            
            # Kinder
            kinder_input = input("  Anzahl Kinder: ").strip()
            if kinder_input and kinder_input.isdigit():
                kinder = int(kinder_input)
                if kinder > 0:
                    profil['haushalt'] = profil.get('haushalt', {})
                    profil['haushalt']['kinder'] = [{'alter': 0} for _ in range(kinder)]
            
            # Schwangerschaft
            schwanger_input = input("  Schwangerschaft? (j/n): ").strip().lower()
            if schwanger_input == 'j':
                profil['situation'] = profil.get('situation', {})
                profil['situation']['schwangerschaft'] = {'vorhanden': True, 'anzahl_kinder': 1}
            
            # Geburt
            geburt_input = input("  Geburt? (j/n): ").strip().lower()
            if geburt_input == 'j':
                profil['situation'] = profil.get('situation', {})
                profil['situation']['geburt'] = {'vorhanden': True, 'anzahl_kinder': 1}
        except (EOFError, KeyboardInterrupt):
            print("\nProfil-Eingabe abgebrochen")
        
        return profil
    
    def _input_format(self) -> str:
        """Fragt nach dem AusgabefORMAT"""
        print(f"\n{self.colors.BOLD}Ausgabeformat:{self.colors.END}")
        print("  1. Text (Standard)")
        print("  2. Markdown")
        print("  3. JSON")
        
        while True:
            try:
                choice = input("  Auswahl (1-3): ").strip()
                if choice == '1':
                    return 'text'
                elif choice == '2':
                    return 'markdown'
                elif choice == '3':
                    return 'json'
                print(f"{self.colors.FAIL}Ungültige Auswahl!{self.colors.END}")
            except (EOFError, KeyboardInterrupt):
                print("\nAbbruch durch Benutzer")
                sys.exit(0)
    
    def _output_text(self, result: Dict[str, Any], verbose: bool = False):
        """Gibt die Ergebnisse als formatierten Text aus"""
        print(self._get_header())
        
        # Hierarchie
        print(f"\n{self.colors.BOLD}📍 Gebietshierarchie:{self.colors.END}")
        for gebiet in result['hierarchie']:
            print(f"  → {gebiet['name']} ({gebiet['ebene']})")
        
        # Zusammenfassung
        print(f"\n{self.colors.BOLD}📋 Zusammenfassung:{self.colors.END}")
        stats = result['zusammenfassung']['statistik']
        print(f"  Leistungen gefunden: {stats['gesamt']}")
        print(f"    ✅ Anspruch JA: {stats['anspruch_ja']}")
        print(f"    ⚠️  Anspruch UNKLAR: {stats['anspruch_unklar']}")
        print(f"    ❌ Anspruch NEIN: {stats['anspruch_nein']}")
        print(f"    ⏰ Dringend: {stats['dringend']}")
        
        # Checkliste
        print(f"\n{self.colors.BOLD}📝 Checkliste:{self.colors.END}")
        
        for eintrag in result['checkliste']:
            self._output_eintrag(eintrag)
        
        # Nächste Schritte
        naechste = result['zusammenfassung']['naechste_schritte']
        if naechste:
            print(f"\n{self.colors.BOLD}🎯 Nächste Schritte:{self.colors.END}")
            for schritt in naechste[:3]:
                self._output_eintrag(schritt)
        
        # Gesamt-Bearbeitungsdauer
        gesamt_dauer = result['zusammenfassung']['gesamte_bearbeitungsdauer_tage']
        if gesamt_dauer > 0:
            print(f"\n{self.colors.BOLD}⏱️  Geschätzte Gesamt-Bearbeitungsdauer:{self.colors.END} {gesamt_dauer} Tage")
    
    def _output_eintrag(self, eintrag: Dict[str, Any]):
        """Gibt einen Checklisten-Eintrag aus"""
        anspruch_icons = {
            'ja': f"{self.colors.OKGREEN}✅{self.colors.END}",
            'unklar': f"{self.colors.WARNING}⚠️{self.colors.END}",
            'nein': f"{self.colors.FAIL}❌{self.colors.END}"
        }
        icon = anspruch_icons.get(eintrag['anspruch'], f"{self.colors.BOLD}❓{self.colors.END}")
        
        print(f"\n{icon} {self.colors.BOLD}{eintrag['leistung_name']}{self.colors.END}")
        print(f"   Anspruch: {eintrag['anspruch'].upper()}")
        
        if eintrag['begründung']:
            for grund in eintrag['begründung']:
                print(f"   ↳ {grund}")
        
        if eintrag.get('frist_tage'):
            print(f"   ⏰ Frist: {eintrag['frist_tage']} Tage")
        
        zustaendigkeit = eintrag.get('zustaendigkeit', {})
        if zustaendigkeit.get('behoerde_name'):
            print(f"   🏛️  Zuständig: {zustaendigkeit['behoerde_name']}")
        
        if eintrag.get('koste'):
            print(f"   💰 Kosten: {eintrag['koste']} €")
        
        if eintrag.get('formular_link'):
            print(f"   🔗 Formular: {eintrag['formular_link']}")
        
        if eintrag.get('abdeckungsstatus') != 'verifiziert':
            print(f"   ℹ️  Status: {eintrag['abdeckungsstatus']}")
    
    def _output_markdown(self, markdown: str):
        """Gibt Markdown aus"""
        print(markdown)
    
    def _output_json(self, result: Dict[str, Any]):
        """Gibt JSON aus"""
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


def main():
    """Hauptfunktion für die CLI"""
    cli = BuergerAICLI()
    cli.run()


if __name__ == '__main__':
    main()
