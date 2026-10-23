// TypeScript Type Definitions for BuergerAI Frontend

// ============================================================================
// Core Types
// ============================================================================

export type Abdeckungsstatus = 'verifiziert' | 'landesebene' | 'unbekannt';
export type AnspruchStatus = 'ja' | 'nein' | 'unklar';
export type Ebene = 'bund' | 'land' | 'kreis' | 'gemeinde';

// ============================================================================
// Checklist Entry Types
// ============================================================================

export interface Unterlage {
  name: string;
  beschreibung?: string;
  pflicht: boolean;
}

export interface Verfahrensschritt {
  beschreibung: string;
  geschatzte_dauer_minuten?: number;
}

export interface Zustaendigkeit {
  behoerde_name: string;
  behoerde_kontakt?: string;
  portal_link?: string;
  post_adresse?: string;
  email?: string;
  telefon?: string;
}

export interface ChecklistEntry {
  leistung_id: string;
  leistung_name: string;
  leistung_beschreibung?: string;
  leistung_kurzbeschreibung?: string;
  variante_id: string;
  anspruch: AnspruchStatus;
  begründung: string[];
  zustaendigkeit: Zustaendigkeit;
  frist_tage?: number;
  frist_beschreibung?: string;
  unterlagen: Unterlage[];
  formular_link?: string;
  formular_bezeichnung?: string;
  schritte: Verfahrensschritt[];
  bearbeitungsdauer_tage?: number;
  koste?: number;
  koste_beschreibung?: string;
  quellen: string[];
  abdeckungsstatus: Abdeckungsstatus;
  gueltig_ab?: string;
  gueltig_bis?: string;
  tags: string[];
  kategorien: string[];
  dringend: boolean;
  online_antrag_moeglich: boolean;
  details?: Record<string, unknown>;
}

// ============================================================================
// Summary Statistics Types
// ============================================================================

export interface ChecklistStatistik {
  gesamt: number;
  anspruch_ja: number;
  anspruch_unklar: number;
  anspruch_nein: number;
  dringend: number;
  mit_formular: number;
  kostenpflichtig: number;
  gesamt_bearbeitungsdauer_tage: number;
}

export interface HierarchieEntry {
  id: string;
  name: string;
  ebene: Ebene;
  ags: string;
}

// ============================================================================
// Request and Response Types
// ============================================================================

export interface AnfrageRequest {
  plz: string;
  lebenssituationen: string[];
  profil?: Profil;
  session_id?: string;
}

export interface AnfrageResult {
  checkliste: ChecklistEntry[];
  zusammenfassung: {
    statistik: ChecklistStatistik;
    naechste_schritte: ChecklistEntry[];
  };
  profil?: Profil;
  hierarchie: HierarchieEntry[];
}

// ============================================================================
// Profile Types
// ============================================================================

export interface Haushaltsmitglied {
  alter?: number;
  einkommen_jaehrlich?: number;
  einkommen_monatlich?: number;
  in_ausbildung?: boolean;
  behindert?: boolean;
  schwanger?: boolean;
  staatsangehoerigkeit?: string;
  aufenthaltsstatus?: string;
}

export interface Kind {
  alter?: number;
  behindert?: boolean;
  in_ausbildung?: boolean;
}

export interface Haushalt {
  anzahl_personen?: number;
  anzahl_kinder?: number;
  anzahl_erwachsene?: number;
  einkommen_gesamthaushalt?: number;
  wohnsitz_plz?: string;
  wohnsitz_ort?: string;
  mietkosten?: number;
  eigentum?: boolean;
  antragstellerin?: Haushaltsmitglied;
  partner?: Haushaltsmitglied;
  kinder?: Kind[];
}

export interface Situation {
  schwangerschaft?: {
    vorhanden: boolean;
    schwangerschaftswoche?: number;
    erwartetes_geburtsdatum?: string;
  };
  geburt?: {
    vorhanden: boolean;
    geburtsdatum?: string;
    anzahl_kinder?: number;
    mehrlingsgeburt?: boolean;
  };
  heirat?: {
    vorhanden: boolean;
    datumsangabe?: string;
  };
  trennung?: {
    vorhanden: boolean;
    datumsangabe?: string;
  };
  tod?: {
    vorhanden: boolean;
    datumsangabe?: string;
  };
  arbeitslosigkeit?: {
    vorhanden: boolean;
    seit_datum?: string;
  };
  erkrankung?: {
    vorhanden: boolean;
    schwerbehinderung?: boolean;
    pflegestufe?: number;
  };
  pflege?: {
    vorhanden: boolean;
    pflegestufe?: number;
  };
  umzug?: {
    vorhanden: boolean;
    umzugsdatum?: string;
    neue_plz?: string;
  };
  ausbildung?: {
    vorhanden: boolean;
    ausbildungstyp?: string;
  };
  renteneintritt?: {
    vorhanden: boolean;
    datumsangabe?: string;
  };
}

export interface Profil {
  haushalt?: Haushalt;
  situation?: Situation;
  metadata?: {
    created_at?: string;
    updated_at?: string;
    session_id?: string;
  };
}

// ============================================================================
// Area Types
// ============================================================================

export interface Gebiet {
  id: string;
  name: string;
  ebene: Ebene;
  ags: string;
  plz?: string[];
  übergeordnete_id?: string;
  untergeordnete_ids?: string[];
}

// ============================================================================
// Service Types
// ============================================================================

export interface Leistung {
  id: string;
  name: string;
  beschreibung: string;
  kurzbeschreibung: string;
  tags: string[];
  kategorien: string[];
}

// ============================================================================
// Validation Types
// ============================================================================

export interface ValidierungsErgebnis {
  gueltig: boolean;
  fehler: string[];
  warnungen: string[];
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiResponse<T> {
  erfolg: boolean;
  data?: T;
  error?: string;
}

export interface HealthCheckResponse {
  status: string;
  version: string;
  service: string;
}

// ============================================================================
// Form Types
// ============================================================================

export interface FormData {
  plz: string;
  situationen: string[];
  profil?: Partial<Profil>;
}

// ============================================================================
// UI State Types
// ============================================================================

export interface AppState {
  currentStep: number;
  isLoading: boolean;
  error: string | null;
  checklist: ChecklistEntry[];
  result: AnfrageResult | null;
  submitted: boolean;
}
