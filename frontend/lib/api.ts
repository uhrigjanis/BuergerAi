// API Client for BuergerAI Frontend
// Optimiert für GitHub Codespaces und lokale Entwicklung

import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  AnfrageRequest,
  AnfrageResult,
  ChecklistEntry,
  ValidierungsErgebnis,
  Gebiet,
  HierarchieEntry,
  Leistung
} from '@/types';

// ============================================================================
// API Configuration - Intelligente URL-Erkennung für Codespaces
// ============================================================================

/**
 * Normalisiert eine API-URL und stellt sicher, dass es genau ein Protokoll gibt
 * und keine doppelten Slashes oder Protokolle enthalten sind.
 */
function normalizeApiUrl(rawUrl?: string): string {
  if (!rawUrl) {
    return 'http://localhost:8000';
  }
  
  // Entferne alle Protokolle (http://, https://) vom Anfang
  let url = rawUrl.replace(/^https?:\/\//, '');
  
  // Entferne führende Slashes
  url = url.replace(/^\/+/, '');
  
  // Entferne eventuell übrig gebliebene doppelte Protokolle
  url = url.replace(/^https?:\/\//, '');
  
  // Füge genau ein Protokoll hinzu
  if (url.startsWith('localhost') || url.startsWith('127.0.0.1')) {
    return `http://${url}`;
  }
  
  // Für Codespaces und externe URLs: immer https
  return `https://${url}`;
}

/**
 * Erkennt automatisch, ob wir in GitHub Codespaces laufen
 * und konstruiert die passende Backend-URL
 */
function getBackendUrl(): string {
  // 1. Prüfe, ob NEXT_PUBLIC_API_URL explizit gesetzt ist
  const explicitUrl = process.env.NEXT_PUBLIC_API_URL;
  if (explicitUrl) {
    return normalizeApiUrl(explicitUrl);
  }
  
  // 2. Versuche, die Codespaces-Umgebung zu erkennen
  // In Codespaces ist CODESPACE_NAME gesetzt
  if (typeof process !== 'undefined' && process.env.CODESPACE_NAME) {
    // Backend-Port in Codespaces
    return `https://${process.env.CODESPACE_NAME}-8000.githubpreview.dev`;
  }
  
  // 3. Fallback für lokale Entwicklung
  return 'http://localhost:8000';
}

// API Base URL - wird automatisch für Codespaces und lokal angepasst
const API_BASE_URL = getBackendUrl();

// Create axios instance with default configuration
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    // In Entwicklung: Logge die Request-URL
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      const status = error.response.status;
      
      if (status === 400) {
        throw new Error('Ungültige Anfrage: ' + (error.response.data as any)?.detail || 'Bitte überprüfen Sie Ihre Eingaben');
      }
      if (status === 404) {
        throw new Error('Ressource nicht gefunden');
      }
      if (status === 500) {
        throw new Error('Serverfehler: Bitte versuchen Sie es später noch einmal');
      }
    } else if (error.request) {
      throw new Error('Keine Antwort vom Server. Bitte überprüfen Sie Ihre Internetverbindung oder ob das Backend läuft.');
    } else {
      throw new Error('Anfragefehler: ' + error.message);
    }
  }
);

// ============================================================================
// API Functions
// ============================================================================

// Health Check
export const checkHealth = async (): Promise<boolean> => {
  try {
    const response = await apiClient.get('/api/health');
    return response.data.status === 'healthy';
  } catch {
    return false;
  }
};

// Main request: Get checklist with details
export const fetchChecklist = async (
  plz: string,
  situationen: string[],
  profil?: object
): Promise<AnfrageResult> => {
  const request: AnfrageRequest = {
    plz,
    lebenssituationen: situationen,
    profil,
  };

  const response = await apiClient.post('/api/anfrage/details', request);
  
  const result: AnfrageResult = {
    checkliste: response.data.checkliste || [],
    zusammenfassung: response.data.zusammenfassung || {
      statistik: {
        gesamt: 0,
        anspruch_ja: 0,
        anspruch_unklar: 0,
        anspruch_nein: 0,
        dringend: 0,
        mit_formular: 0,
        kostenpflichtig: 0,
        gesamt_bearbeitungsdauer_tage: 0,
      },
      naechste_schritte: [],
    },
    profil: profil || {},
    hierarchie: response.data.hierarchie || [],
  };

  return result;
};

// Simple checklist request
export const fetchSimpleChecklist = async (
  plz: string,
  situationen: string[]
): Promise<ChecklistEntry[]> => {
  const request = {
    plz,
    lebenssituationen: situationen,
  };

  const response = await apiClient.post('/api/anfrage', request);
  return response.data.checkliste || [];
};

// Get checklist as markdown
export const fetchMarkdownChecklist = async (
  plz: string,
  situationen: string[]
): Promise<string> => {
  const params = new URLSearchParams({
    plz,
    situationen: situationen.join(','),
  });

  const response = await apiClient.get(`/api/anfrage/markdown?${params}`);
  return response.data.markdown || '';
};

// Validate request
export const validateRequest = async (
  plz: string,
  situationen: string[]
): Promise<ValidierungsErgebnis> => {
  const request = {
    plz,
    lebenssituationen: situationen,
  };

  const response = await apiClient.post('/api/validate', request);
  return response.data;
};

// Get area by PLZ
export const getGebietByPlz = async (plz: string): Promise<Gebiet | null> => {
  try {
    const response = await apiClient.get(`/api/gebiete/plz/${plz}`);
    return response.data.gebiet || null;
  } catch {
    return null;
  }
};

// Get hierarchy for PLZ
export const getHierarchie = async (plz: string): Promise<HierarchieEntry[]> => {
  try {
    const response = await apiClient.get(`/api/gebiete/hierarchie/${plz}`);
    return response.data.hierarchie || [];
  } catch {
    return [];
  }
};

// Get all services
export const getAllLeistungen = async (): Promise<Leistung[]> => {
  const response = await apiClient.get('/api/leistungen');
  return response.data.leistungen || [];
};

// Search services by situation
export const searchLeistungen = async (
  situationen: string[],
  plz?: string
): Promise<any[]> => {
  const params: Record<string, string> = {
    situationen: situationen.join(','),
  };
  
  if (plz) {
    params.plz = plz;
  }

  const queryString = new URLSearchParams(params).toString();
  const response = await apiClient.get(`/api/leistungen/suche?${queryString}`);
  return response.data.varianten || [];
};

// ============================================================================
// Utility Functions
// ============================================================================

// Format PLZ to ensure it's 5 digits
export const formatPlz = (plz: string): string => {
  const cleaned = plz.replace(/\D/g, '');
  return cleaned.padStart(5, '0');
};

// Validate PLZ format
export const isValidPlz = (plz: string): boolean => {
  const cleaned = plz.replace(/\D/g, '');
  return cleaned.length === 5 && /^\d{5}$/.test(cleaned);
};

// Get available life situations from backend
export const getAvailableSituationen = async (): Promise<string[]> => {
  try {
    const leistungen = await getAllLeistungen();
    const situationenSet = new Set<string>();
    
    leistungen.forEach((leistung) => {
      leistung.tags?.forEach((tag) => {
        const lifeSituations = [
          'Schwangerschaft', 'Geburt', 'Heirat', 'Trennung', 'Tod',
          'Arbeitslosigkeit', 'Erkrankung', 'Pflege', 'Umzug',
          'Ausbildung', 'Renteneintritt', 'Adoption', 'Scheidung',
          'Elternzeit', 'Kinderbetreuung', 'Wohnungssuche', 'Insolvenz'
        ];
        
        if (lifeSituations.includes(tag)) {
          situationenSet.add(tag);
        }
      });
    });
    
    // Add common life situations
    const commonSituationen = [
      'Schwangerschaft', 'Geburt', 'Heirat', 'Trennung', 'Scheidung',
      'Tod', 'Arbeitslosigkeit', 'Erkrankung', 'Pflege', 'Umzug',
      'Ausbildung', 'Renteneintritt', 'Adoption', 'Elternzeit',
      'Kinderbetreuung', 'Wohnungssuche', 'Insolvenz', 'Schwerbehinderung'
    ];
    
    commonSituationen.forEach((s) => situationenSet.add(s));
    
    return Array.from(situationenSet).sort();
  } catch {
    return [
      'Schwangerschaft',
      'Geburt',
      'Heirat',
      'Trennung',
      'Scheidung',
      'Tod',
      'Arbeitslosigkeit',
      'Erkrankung',
      'Pflege',
      'Umzug',
      'Ausbildung',
      'Renteneintritt',
      'Adoption',
      'Elternzeit',
      'Kinderbetreuung',
      'Wohnungssuche',
      'Insolvenz',
      'Schwerbehinderung'
    ];
  }
};

// Get the current API base URL (for debugging)
export const getApiBaseUrl = (): string => {
  return API_BASE_URL;
};

// ============================================================================
// Export
// ============================================================================

export default apiClient;
export {
  apiClient,
  API_BASE_URL,
};
