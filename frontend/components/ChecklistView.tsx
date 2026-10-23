'use client';

import React, { useState, useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Chip,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton,
  Tooltip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Collapse,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress,
  Alert,
  Stack
} from '@mui/material';
import {
  ExpandMore,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Help as HelpIcon,
  Info as InfoIcon,
  AccessTime as TimeIcon,
  AttachMoney as MoneyIcon,
  Description as DescriptionIcon,
  LocationOn as LocationIcon,
  Link as LinkIcon,
  Warning as WarningIcon,
  FilterAlt as FilterIcon
} from '@mui/icons-material';
import { AnfrageResult, ChecklistEntry, ChecklistStatistik } from '@/types';

// ============================================================================
// Props Interface
// ============================================================================

interface ChecklistViewProps {
  result: AnfrageResult;
}

// ============================================================================
// Helper Functions
// ============================================================================

const getStatusColor = (anspruch: string) => {
  switch (anspruch) {
    case 'ja':
      return 'success';
    case 'nein':
      return 'error';
    case 'unklar':
      return 'warning';
    default:
      return 'default';
  }
};

const getStatusLabel = (anspruch: string) => {
  switch (anspruch) {
    case 'ja':
      return 'Anspruch besteht';
    case 'nein':
      return 'Kein Anspruch';
    case 'unklar':
      return 'Unklar';
    default:
      return Anspruch;
  }
};

const getAbdeckungsstatusColor = (status: string) => {
  switch (status) {
    case 'verifiziert':
      return 'success';
    case 'landesebene':
      return 'info';
    case 'unbekannt':
      return 'warning';
    default:
      return 'default';
  }
};

const getAbdeckungsstatusLabel = (status: string) => {
  switch (status) {
    case 'verifiziert':
      return 'Verifiziert';
    case 'landesebene':
      return 'Länderebene';
    case 'unbekannt':
      return 'Unbekannt';
    default:
      return status;
  }
};

// ============================================================================
// Sub-Components
// ============================================================================

// Status Badge Component
const StatusBadge: React.FC<{ anspruch: string; abdeckungsstatus: string }> = ({
  anspruch,
  abdeckungsstatus,
}) => {
  return (
    <Box display="flex" gap={1} alignItems="center">
      <Chip
        label={getStatusLabel(anspruch)}
        color={getStatusColor(anspruch) as any}
        size="small"
        icon={
          anspruch === 'ja' ? <CheckCircleIcon fontSize="small" /> :
            anspruch === 'nein' ? <CancelIcon fontSize="small" /> :
              <HelpIcon fontSize="small" />
        }
      />
      <Chip
        label={getAbdeckungsstatusLabel(abdeckungsstatus)}
        color={getAbdeckungsstatusColor(abdeckungsstatus) as any}
        size="small"
        variant="outlined"
      />
    </Box>
  );
};

// Deadline Badge Component
const DeadlineBadge: React.FC<{ fristTage?: number; dringend?: boolean }> = ({
  fristTage,
  dringend,
}) => {
  if (!fristTage && !dringend) return null;

  const color = dringend ? 'error' : fristTage && fristTage <= 30 ? 'warning' : 'info';
  const label = dringend
    ? 'Dringend!'
    : fristTage
      ? `Frist: ${fristTage} Tage`
      : '';

  if (!label) return null;

  return (
    <Chip
      label={label}
      color={color as any}
      size="small"
      icon={<TimeIcon fontSize="small" />}
    />
  );
};

// Cost Badge Component
const CostBadge: React.FC<{ koste?: number; kostenpflichtig?: boolean }> = ({
  koste,
  kostenpflichtig,
}) => {
  if (!koste && !kostenpflichtig) return null;

  const label = koste
    ? `Kosten: ${koste} €`
    : kostenpflichtig
      ? 'Kostenpflichtig'
      : '';

  if (!label) return null;

  return (
    <Chip
      label={label}
      color="secondary"
      size="small"
      icon={<MoneyIcon fontSize="small" />}
    />
  );
};

// Processing Time Badge Component
const ProcessingTimeBadge: React.FC<{ bearbeitungsdauerTage?: number }> = ({
  bearbeitungsdauerTage,
}) => {
  if (!bearbeitungsdauerTage) return null;

  return (
    <Chip
      label={`Bearbeitung: ~${bearbeitungsdauerTage} Tage`}
      color="info"
      size="small"
      icon={<AccessTime fontSize="small" />}
      variant="outlined"
    />
  );
};

// Documents List Component
const DocumentsList: React.FC<{ unterlagen: any[] }> = ({ unterlagen }) => {
  if (!unterlagen || unterlagen.length === 0) return null;

  return (
    <Box mt={1}>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
        <DescriptionIcon fontSize="small" color="primary" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
        Benötigte Unterlagen:
      </Typography>
      <List dense>
        {unterlagen.map((unterlage, index) => (
          <ListItem key={index} disablePadding>
            <ListItemIcon sx={{ minWidth: 24 }}>
              {unterlage.pflicht ? (
                <CheckCircleIcon fontSize="small" color="error" />
              ) : (
                <InfoIcon fontSize="small" color="action" />
              )}
            </ListItemIcon>
            <ListItemText
              primary={unterlage.name}
              secondary={unterlage.beschreibung}
              primaryTypographyProps={{ variant: 'body2' }}
              secondaryTypographyProps={{ variant: 'caption', color: 'text.secondary' }}
            />
          </ListItem>
        ))}
      </List>
    </Box>
  );
};

// Steps List Component
const StepsList: React.FC<{ schritte: any[] }> = ({ schritte }) => {
  if (!schritte || schritte.length === 0) return null;

  return (
    <Box mt={1}>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
        <InfoIcon fontSize="small" color="primary" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
        Schritte:
      </Typography>
      <List dense>
        {schritte.map((schritt, index) => (
          <ListItem key={index} disablePadding>
            <ListItemIcon sx={{ minWidth: 24 }}>
              <Typography variant="body2" color="text.secondary">
                {index + 1}.
              </Typography>
            </ListItemIcon>
            <ListItemText
              primary={schritt.beschreibung}
              secondary={schritt.geschatzte_dauer_minuten
                ? `ca. ${schritt.geschatzte_dauer_minuten} Minuten`
                : ''}
              primaryTypographyProps={{ variant: 'body2' }}
              secondaryTypographyProps={{ variant: 'caption', color: 'text.secondary' }}
            />
          </ListItem>
        ))}
      </List>
    </Box>
  );
};

// Authority Info Component
const AuthorityInfo: React.FC<{ zustaendigkeit: any }> = ({ zustaendigkeit }) => {
  if (!zustaendigkeit || !zustaendigkeit.behoerde_name) return null;

  const hasContact = zustaendigkeit.behoerde_kontakt || 
    zustaendigkeit.telefon || 
    zustaendigkeit.email ||
    zustaendigkeit.portal_link;

  return (
    <Box mt={1}>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
        <LocationIcon fontSize="small" color="primary" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
        Zuständige Behörde:
      </Typography>
      <Typography variant="body2" sx={{ mb: hasContact ? 1 : 0 }}>
        {zustaendigkeit.behoerde_name}
      </Typography>
      
      {hasContact && (
        <Box display="flex" flexDirection="column" gap={0.5}>
          {zustaendigkeit.portal_link && (
            <Typography variant="body2">
              <LinkIcon fontSize="small" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
              <a href={zustaendigkeit.portal_link} target="_blank" rel="noopener noreferrer">
                Online-Portal
              </a>
            </Typography>
          )}
          {zustaendigkeit.telefon && (
            <Typography variant="body2">
              <Box component="span" sx={{ mr: 0.5 }}>
                📞
              </Box>
              {zustaendigkeit.telefon}
            </Typography>
          )}
          {zustaendigkeit.email && (
            <Typography variant="body2">
              <Box component="span" sx={{ mr: 0.5 }}>
                ✉️
              </Box>
              {zustaendigkeit.email}
            </Typography>
          )}
          {zustaendigkeit.post_adresse && (
            <Typography variant="body2">
              <Box component="span" sx={{ mr: 0.5 }}>
                📍
              </Box>
              {zustaendigkeit.post_adresse}
            </Typography>
          )}
        </Box>
      )}
    </Box>
  );
};

// Form Link Component
const FormLink: React.FC<{ formularLink?: string; formularBezeichnung?: string }> = ({
  formularLink,
  formularBezeichnung,
}) => {
  if (!formularLink) return null;

  return (
    <Box mt={1}>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
        <DescriptionIcon fontSize="small" color="primary" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
        Antragsformular:
      </Typography>
      <Button
        variant="outlined"
        startIcon={<DescriptionIcon />}
        onClick={() => window.open(formularLink, '_blank')}
        size="small"
      >
        {formularBezeichnung || 'Formular herunterladen'}
      </Button>
    </Box>
  );
};

// ============================================================================
// Checklist Entry Card Component
// ============================================================================

interface ChecklistEntryCardProps {
  entry: ChecklistEntry;
  index: number;
}

const ChecklistEntryCard: React.FC<ChecklistEntryCardProps> = ({ entry, index }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <Paper
      elevation={0}
      variant="outlined"
      sx={{
        mb: 2,
        p: 2,
        borderRadius: 2,
        borderLeft: 4,
        borderLeftColor: getStatusColor(entry.anspruch) + '.main',
        '&:hover': {
          boxShadow: 2,
        },
      }}
    >
      <Accordion expanded={expanded} onChange={() => setExpanded(!expanded)} sx={{ boxShadow: 'none' }}>
        <AccordionSummary
          expandIcon={<ExpandMore />}
          sx={{
            minHeight: 'unset',
            '& .MuiAccordionSummary-content': {
              margin: 0,
            },
            '&.Mui-expanded': {
              minHeight: 'unset',
            },
          }}
        >
          <Box display="flex" flexDirection="column" width="100%">
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
              <Typography variant="h6" component="h3" sx={{ fontWeight: 600 }}>
                {index + 1}. {entry.leistung_name}
              </Typography>
              <StatusBadge anspruch={entry.anspruch} abdeckungsstatus={entry.abdeckungsstatus} />
            </Box>
            
            {entry.leistung_kurzbeschreibung && (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                {entry.leistung_kurzbeschreibung}
              </Typography>
            )}
            
            <Box display="flex" flexWrap="wrap" gap={1}>
              <DeadlineBadge fristTage={entry.frist_tage} dringend={entry.dringend} />
              <CostBadge koste={entry.koste} kostenpflichtig={entry.koste !== undefined && entry.koste > 0} />
              <ProcessingTimeBadge bearbeitungsdauerTage={entry.bearbeitungsdauer_tage} />
              {entry.online_antrag_moeglich && (
                <Chip
                  label="Online möglich"
                  color="success"
                  size="small"
                  icon={<CheckCircleIcon fontSize="small" />}
                />
              )}
            </Box>
            
            {entry.begründung && entry.begründung.length > 0 && (
              <Box mt={1}>
                <Typography variant="caption" color="text.secondary">
                  Begründung: {entry.begründung.join(', ')}
                </Typography>
              </Box>
            )}
          </Box>
        </AccordionSummary>
        
        <AccordionDetails sx={{ pt: 2 }}>
          <Divider sx={{ my: 2 }} />
          
          {/* Full Description */}
          {entry.leistung_beschreibung && (
            <Box mb={2}>
              <Typography variant="body2" paragraph>
                {entry.leistung_beschreibung}
              </Typography>
            </Box>
          )}
          
          {/* Tags */}
          {entry.tags && entry.tags.length > 0 && (
            <Box mb={2}>
              <Box display="flex" flexWrap="wrap" gap={1}>
                {entry.tags.map((tag) => (
                  <Chip key={tag} label={tag} size="small" variant="outlined" />
                ))}
              </Box>
            </Box>
          )}
          
          {/* Authority Info */}
          <AuthorityInfo zustaendigkeit={entry.zustaendigkeit} />
          
          {/* Form Link */}
          <FormLink formularLink={entry.formular_link} formularBezeichnung={entry.formular_bezeichnung} />
          
          {/* Documents */}
          <DocumentsList unterlagen={entry.unterlagen} />
          
          {/* Steps */}
          <StepsList schritte={entry.schritte} />
          
          {/* Sources */}
          {entry.quellen && entry.quellen.length > 0 && (
            <Box mt={2}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                Quellen:
              </Typography>
              <List dense>
                {entry.quellen.map((quelle, index) => (
                  <ListItem key={index} disablePadding>
                    <ListItemIcon sx={{ minWidth: 24 }}>
                      <Typography variant="body2" color="text.secondary">
                        {index + 1}.
                      </Typography>
                    </ListItemIcon>
                    <ListItemText
                      primary={quelle}
                      primaryTypographyProps={{ variant: 'body2' }}
                    />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}
          
          {/* Validity Period */}
          {(entry.gueltig_ab || entry.gueltig_bis) && (
            <Box mt={2}>
              <Typography variant="caption" color="text.secondary">
                Gültig: {entry.gueltig_ab} – {entry.gueltig_bis || 'unbefristet'}
              </Typography>
            </Box>
          )}
        </AccordionDetails>
      </Accordion>
    </Paper>
  );
};

// ============================================================================
// Summary Component
// ============================================================================

interface SummaryProps {
  statistik: ChecklistStatistik;
  hierarchie: any[];
}

const Summary: React.FC<SummaryProps> = ({ statistik, hierarchie }) => {
  const progress = (
    (statistik.anspruch_ja + statistik.anspruch_unklar) / 
    (statistik.gesamt || 1) * 100
  );

  return (
    <Paper
      elevation={0}
      variant="outlined"
      sx={{
        mb: 3,
        p: 3,
        borderRadius: 2,
        backgroundColor: 'background.paper',
      }}
    >
      <Typography variant="h5" component="h2" sx={{ fontWeight: 600, mb: 2 }}>
        <InfoIcon color="primary" sx={{ verticalAlign: 'middle', mr: 1 }} />
        Zusammenfassung
      </Typography>

      {/* Progress Bar */}
      <Box mb={2}>
        <Typography variant="body2" sx={{ mb: 1 }}>
          Möglicher Anspruch: {statistik.anspruch_ja + statistik.anspruch_unklar} von {statistik.gesamt} Leistungen
        </Typography>
        <LinearProgress
          variant="determinate"
          value={progress}
          sx={{
            height: 8,
            borderRadius: 4,
            backgroundColor: 'divider',
            '& .MuiLinearProgress-bar': {
              backgroundColor: 'success.main',
            },
          }}
        />
        <Box display="flex" justifyContent="space-between" mt={0.5}>
          <Typography variant="caption" color="success.main">
            {Math.round(progress)}% Chance
          </Typography>
        </Box>
      </Box>

      {/* Statistics Grid */}
      <Box display="grid" gridTemplateColumns="repeat(auto-fit, minmax(150px, 1fr))" gap={2} mb={2}>
        <Box textAlign="center">
          <Typography variant="h4" component="div" sx={{ fontWeight: 700, color: 'success.main' }}>
            {statistik.anspruch_ja}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Anspruch ja
          </Typography>
        </Box>
        <Box textAlign="center">
          <Typography variant="h4" component="div" sx={{ fontWeight: 700, color: 'warning.main' }}>
            {statistik.anspruch_unklar}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Unklar
          </Typography>
        </Box>
        <Box textAlign="center">
          <Typography variant="h4" component="div" sx={{ fontWeight: 700, color: 'error.main' }}>
            {statistik.anspruch_nein}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Kein Anspruch
          </Typography>
        </Box>
        {statistik.dringend > 0 && (
          <Box textAlign="center">
            <Typography variant="h4" component="div" sx={{ fontWeight: 700, color: 'error.main' }}>
              {statistik.dringend}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Dringend
            </Typography>
          </Box>
        )}
      </Box>

      {/* Hierarchy Info */}
      {hierarchie && hierarchie.length > 0 && (
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
            <LocationIcon fontSize="small" color="primary" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
            Zuständig für:
          </Typography>
          <Box display="flex" flexWrap="wrap" gap={1}>
            {hierarchie.map((gebiet) => (
              <Chip
                key={gebiet.id}
                label={`${gebiet.name} (${gebiet.ebene})`}
                size="small"
                variant="outlined"
              />
            ))}
          </Box>
        </Box>
      )}

      {/* Processing Time Summary */}
      {statistik.gesamt_bearbeitungsdauer_tage > 0 && (
        <Box mt={2}>
          <Typography variant="body2" color="text.secondary">
            <AccessTime fontSize="small" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
            Geschätzte Gesamtbearbeitungszeit: {statistik.gesamt_bearbeitungsdauer_tage} Tage
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

// ============================================================================
// Filter Controls Component
// ============================================================================

interface FilterControlsProps {
  onFilterChange: (filter: string) => void;
  totalCount: number;
  filteredCount: number;
}

const FilterControls: React.FC<FilterControlsProps> = ({ onFilterChange, totalCount, filteredCount }) => {
  const [filter, setFilter] = useState('alle');

  const handleFilterChange = (newFilter: string) => {
    setFilter(newFilter);
    onFilterChange(newFilter);
  };

  return (
    <Box display="flex" alignItems="center" gap={2} mb={2} flexWrap="wrap">
      <Typography variant="body2" color="text.secondary">
        Zeige: {filteredCount} von {totalCount} Leistungen
      </Typography>
      <Box display="flex" gap={1}>
        <Chip
          label="Alle"
          color={filter === 'alle' ? 'primary' : 'default'}
          onClick={() => handleFilterChange('alle')}
          clickable
          size="small"
        />
        <Chip
          label="Anspruch ja"
          color={filter === 'ja' ? 'success' : 'default'}
          onClick={() => handleFilterChange('ja')}
          clickable
          size="small"
        />
        <Chip
          label="Unklar"
          color={filter === 'unklar' ? 'warning' : 'default'}
          onClick={() => handleFilterChange('unklar')}
          clickable
          size="small"
        />
        <Chip
          label="Kein Anspruch"
          color={filter === 'nein' ? 'error' : 'default'}
          onClick={() => handleFilterChange('nein')}
          clickable
          size="small"
        />
        <Chip
          label="Dringend"
          color={filter === 'dringend' ? 'error' : 'default'}
          onClick={() => handleFilterChange('dringend')}
          clickable
          size="small"
        />
      </Box>
    </Box>
  );
};

// ============================================================================
// Main Component
// ============================================================================

const ChecklistView: React.FC<ChecklistViewProps> = ({ result }) => {
  const [filter, setFilter] = useState<string>('alle');

  // Filter checklist entries
  const filteredChecklist = useMemo(() => {
    if (filter === 'alle') return result.checkliste;
    
    return result.checkliste.filter((entry) => {
      if (filter === 'ja') return entry.anspruch === 'ja';
      if (filter === 'nein') return entry.anspruch === 'nein';
      if (filter === 'unklar') return entry.anspruch === 'unklar';
      if (filter === 'dringend') return entry.dringend === true;
      return true;
    });
  }, [result.checkliste, filter]);

  // Handle filter change
  const handleFilterChange = (newFilter: string) => {
    setFilter(newFilter);
  };

  // Group entries by claim status
  const groupedEntries = useMemo(() => {
    const groups: Record<string, ChecklistEntry[]> = {
      ja: [],
      unklar: [],
      nein: [],
    };

    filteredChecklist.forEach((entry) => {
      if (entry.anspruch === 'ja') {
        groups.ja.push(entry);
      } else if (entry.anspruch === 'unklar') {
        groups.unklar.push(entry);
      } else {
        groups.nein.push(entry);
      }
    });

    return groups;
  }, [filteredChecklist]);

  // Count entries for each group
  const groupCounts = {
    ja: groupedEntries.ja.length,
    unklar: groupedEntries.unklar.length,
    nein: groupedEntries.nein.length,
  };

  // Show warning if no entries match filter
  const hasNoResults = filteredChecklist.length === 0 && result.checkliste.length > 0;

  return (
    <Box>
      {/* Summary */}
      <Summary
        statistik={result.zusammenfassung.statistik}
        hierarchie={result.hierarchie}
      />

      {/* Filter Controls */}
      <FilterControls
        onFilterChange={handleFilterChange}
        totalCount={result.checkliste.length}
        filteredCount={filteredChecklist.length}
      />

      {/* Warning for no results */}
      {hasNoResults && (
        <Alert
          severity="info"
          onClose={() => setFilter('alle')}
          sx={{ mb: 2 }}
        >
          Keine Leistungen gefunden, die dem aktuellen Filter entsprechen. 
          <Button color="inherit" size="small" onClick={() => setFilter('alle')}>
            Filter zurücksetzen
          </Button>
        </Alert>
      )}

      {/* Next Steps Section */}
      {result.zusammenfassung.naechste_schritte && 
        result.zusammenfassung.naechste_schritte.length > 0 && (
          <Box mb={3}>
            <Paper
              elevation={0}
              variant="outlined"
              sx={{
                p: 2,
                borderRadius: 2,
                borderLeft: 4,
                borderLeftColor: 'primary.main',
              }}
            >
              <Typography variant="h6" component="h3" sx={{ fontWeight: 600, mb: 2 }}>
                <WarningIcon color="primary" sx={{ verticalAlign: 'middle', mr: 1 }} />
                Nächste Schritte (Priorisiert)
              </Typography>
              <List dense>
                {result.zusammenfassung.naechste_schritte.map((entry, index) => (
                  <ListItem key={index} disablePadding>
                    <ListItemIcon sx={{ minWidth: 24 }}>
                      <Typography variant="body2" color="primary" sx={{ fontWeight: 600 }}>
                        {index + 1}.
                      </Typography>
                    </ListItemIcon>
                    <ListItemText
                      primary={entry.leistung_name}
                      secondary={
                        <StatusBadge anspruch={entry.anspruch} abdeckungsstatus={entry.abdeckungsstatus} />
                      }
                      primaryTypographyProps={{ variant: 'body1' }}
                    />
                  </ListItem>
                ))}
              </List>
            </Paper>
          </Box>
        )}

      {/* Grouped Checklist Entries */}
      <Box>
        {/* Ja Group */}
        {groupCounts.ja > 0 && (
          <Box mb={3}>
            <Typography
              variant="h6"
              component="h3"
              sx={{
                fontWeight: 600,
                color: 'success.main',
                mb: 1,
                display: 'flex',
                alignItems: 'center',
                gap: 1,
              }}
            >
              <CheckCircleIcon />
              Anspruch besteht ({groupCounts.ja})
            </Typography>
            {groupedEntries.ja.map((entry, index) => (
              <ChecklistEntryCard
                key={`${entry.leistung_id}-${entry.variante_id}`}
                entry={entry}
                index={index}
              />
            ))}
          </Box>
        )}

        {/* Unklar Group */}
        {groupCounts.unklar > 0 && (
          <Box mb={3}>
            <Typography
              variant="h6"
              component="h3"
              sx={{
                fontWeight: 600,
                color: 'warning.main',
                mb: 1,
                display: 'flex',
                alignItems: 'center',
                gap: 1,
              }}
            >
              <HelpIcon />
              Unklar ({groupCounts.unklar})
            </Typography>
            {groupedEntries.unklar.map((entry, index) => (
              <ChecklistEntryCard
                key={`${entry.leistung_id}-${entry.variante_id}`}
                entry={entry}
                index={index}
              />
            ))}
          </Box>
        )}

        {/* Nein Group */}
        {groupCounts.nein > 0 && (
          <Box mb={3}>
            <Typography
              variant="h6"
              component="h3"
              sx={{
                fontWeight: 600,
                color: 'error.main',
                mb: 1,
                display: 'flex',
                alignItems: 'center',
                gap: 1,
              }}
            >
              <CancelIcon />
              Kein Anspruch ({groupCounts.nein})
            </Typography>
            {groupedEntries.nein.map((entry, index) => (
              <ChecklistEntryCard
                key={`${entry.leistung_id}-${entry.variante_id}`}
                entry={entry}
                index={index}
              />
            ))}
          </Box>
        )}
      </Box>

      {/* Empty State */}
      {result.checkliste.length === 0 && (
        <Paper
          elevation={0}
          variant="outlined"
          sx={{
            p: 4,
            textAlign: 'center',
            borderRadius: 2,
          }}
        >
          <InfoIcon color="action" sx={{ fontSize: 48, mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Keine Leistungen gefunden
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Für Ihre angegebene Postleitzahl und Lebenssituation wurden keine Leistungen gefunden.
          </Typography>
        </Paper>
      )}
    </Box>
  );
};

export default ChecklistView;
