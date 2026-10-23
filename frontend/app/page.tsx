'use client'

import { useState, useEffect } from 'react'
import {
  Container,
  Typography,
  Box,
  Paper,
  Stepper,
  Step,
  StepLabel,
  Button,
  CircularProgress,
  Alert,
  Divider
} from '@mui/material'
import { CheckCircle, Search, Description, Info } from '@mui/icons-material'

import IntakeForm from '@/components/IntakeForm'
import ChecklistView from '@/components/ChecklistView'
import { AnfrageResult, ChecklistEntry } from '@/types'
import { fetchChecklist } from '@/lib/api'

// Schritte im Workflow
type Step = {
  label: string
  icon: React.ReactNode
}

const steps: Step[] = [
  { label: 'Situation eingeben', icon: <Search /> },
  { label: 'Leistungen prüfen', icon: <Description /> },
  { label: 'Checkliste anzeigen', icon: <CheckCircle /> },
]

export default function Home() {
  const [activeStep, setActiveStep] = useState(0)
  const [checklist, setChecklist] = useState<ChecklistEntry[]>([])
  const [result, setResult] = useState<AnfrageResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)

  // Zurück zum Formular
  const handleReset = () => {
    setActiveStep(0)
    setChecklist([])
    setResult(null)
    setError(null)
    setSubmitted(false)
  }

  // Formular-Submit
  const handleSubmit = async (data: {
    plz: string
    situationen: string[]
    profil?: any
  }) => {
    setLoading(true)
    setError(null)
    
    try {
      setActiveStep(1)
      
      // API-Aufruf
      const response = await fetchChecklist(data.plz, data.situationen, data.profil)
      
      setChecklist(response.checkliste)
      setResult({
        checkliste: response.checkliste,
        zusammenfassung: response.zusammenfassung,
        profil: data.profil,
        hierarchie: response.hierarchie || []
      })
      
      setActiveStep(2)
      setSubmitted(true)
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ein Fehler ist aufgetreten')
      setActiveStep(0)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box textAlign="center" mb={6}>
        <Typography variant="h2" component="h1" gutterBottom sx={{ fontWeight: 700 }}>
          🏛️ BuergerAI
        </Typography>
        <Typography variant="h5" color="text.secondary">
          Finde heraus, welche Leistungen dir in deiner Situation zustehen
        </Typography>
      </Box>

      {/* Stepper */}
      <Paper elevation={0} sx={{ mb: 4, p: 3, backgroundColor: 'background.paper' }}>
        <Stepper activeStep={activeStep} alternativeLabel>
          {steps.map((step, index) => (
            <Step key={index} completed={activeStep > index}>
              <StepLabel icon={step.icon}>{step.label}</StepLabel>
            </Step>
          ))}
        </Stepper>
      </Paper>

      {/* Fehleranzeige */}
      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Ladeindikator */}
      {loading && (
        <Box display="flex" justifyContent="center" my={6}>
          <CircularProgress size={60} />
        </Box>
      )}

      {/* Hauptinhalt */}
      {!submitted && !loading && (
        <Paper elevation={3} sx={{ p: 4 }}>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
            Situation eingeben
          </Typography>
          <Typography variant="body1" color="text.secondary" paragraph>
            Gib deine Postleitzahl und Lebenssituation ein, um passende Leistungen zu finden.
          </Typography>
          
          <IntakeForm onSubmit={handleSubmit} />
        </Paper>
      )}

      {/* Checklisten-Ansicht */}
      {submitted && !loading && result && (
        <Box>
          <Paper elevation={3} sx={{ p: 4, mb: 3 }}>
            <ChecklistView result={result} />
          </Paper>
          
          <Box display="flex" justifyContent="center" gap={2}>
            <Button 
              variant="contained" 
              onClick={handleReset}
              startIcon={<Search />}
            >
              Neue Suche
            </Button>
          </Box>
        </Box>
      )}

      {/* Info-Bereich */}
      <Divider sx={{ my: 6 }} />
      
      <Paper elevation={0} sx={{ p: 4, backgroundColor: 'background.paper' }}>
        <Box display="flex" alignItems="center" mb={2}>
          <Info color="primary" sx={{ mr: 2 }} />
          <Typography variant="h6" component="h3">
            Wie funktioniert BuergerAI?
          </Typography>
        </Box>
        
        <Typography variant="body2" color="text.secondary" paragraph>
          BuergerAI hilft dir, alle Leistungen zu finden, die dir in deiner aktuellen Lebenssituation 
          zustehen. Die Daten basieren auf offiziellen Quellen und werden regelmäßig aktualisiert.
        </Typography>
        
        <Box component="ul" sx={{ pl: 3, m: 0 }}>
          <Typography variant="body2" component="li" sx={{ mb: 1 }}>
            ✅ Offizielle Daten aus behördlichen Quellen
          </Typography>
          <Typography variant="body2" component="li" sx={{ mb: 1 }}>
            ✅ Individuelle Prüfung deiner Situation
          </Typography>
          <Typography variant="body2" component="li" sx={{ mb: 1 }}>
            ✅ Klare Handlungsanweisungen mit Fristen und Unterlagen
          </Typography>
          <Typography variant="body2" component="li" sx={{ mb: 1 }}>
            ✅ Keine Speicherung deiner Daten
          </Typography>
        </Box>
      </Paper>
    </Container>
  )
}
