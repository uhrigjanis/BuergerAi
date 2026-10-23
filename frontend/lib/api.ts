// API Client for BuergerAI Frontend

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
// API Configuration
// ============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
    // Can add auth token here if needed
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
    // Handle specific error cases
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
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
      // The request was made but no response was received
      throw new Error('Keine Antwort vom Server. Bitte überprüfen Sie Ihre Internetverbindung.');
    } else {
      // Something happened in setting up the request
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

// Main request: Get checklist
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
  
  // Transform the response to match our expected format
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
  // Remove all non-digit characters
  const cleaned = plz.replace(/\D/g, '');
  // Pad with leading zeros if necessary
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
      leistung.tags.forEach((tag) => {
        // Extract life situations from tags
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
    
    // Add common life situations that might not be in tags
    const commonSituationen = [
      'Schwangerschaft', 'Geburt', 'Heirat', 'Trennung', 'Scheidung',
      'Tod', 'Arbeitslosigkeit', 'Erkrankung', 'Pflege', 'Umzug',
      'Ausbildung', 'Renteneintritt', 'Adoption', 'Elternzeit',
      'Kinderbetreuung', 'Wohnungssuche', 'Insolvenz', 'Schwerbehinderung'
    ];
    
    commonSituationen.forEach((s) => situationenSet.add(s));
    
    return Array.from(situationenSet).sort();
  } catch {
    // Return default list if API fails
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

// ============================================================================
// Export
// ============================================================================

export default apiClient;
export {
  apiClient,
  API_BASE_URL,
};
