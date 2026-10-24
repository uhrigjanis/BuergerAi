'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  TextField,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Paper,
  Typography,
  Chip,
  Divider,
  Collapse,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  ExpandMore,
  ExpandLess,
  Info as InfoIcon,
  Check as CheckIcon,
  Close as CloseIcon
} from '@mui/icons-material';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as zod from 'zod';
import { getAvailableSituationen, isValidPlz, formatPlz } from '@/lib/api';
import { FormData } from '@/types';

// ============================================================================
// Form Validation Schema
// ============================================================================

const formSchema = zod.object({
  plz: zod
    .string()
    .min(1, 'Bitte geben Sie eine PLZ ein')
    .refine((val) => isValidPlz(val), {
      message: 'Bitte geben Sie eine gültige 5-stellige PLZ ein',
    }),
  situationen: zod
    .array(zod.string())
    .min(1, 'Bitte wählen Sie mindestens eine Lebenssituation aus'),
});

type FormValues = zod.infer<typeof formSchema>;

// ============================================================================
// Props Interface
// ============================================================================

interface IntakeFormProps {
  onSubmit: (data: FormData) => Promise<void>;
  isLoading?: boolean;
}

// ============================================================================
// Common Life Situations
// ============================================================================

const COMMON_SITUATIONEN = [
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

const SITUATIONEN_DESCRIPTIONS: Record<string, string> = {
  'Schwangerschaft': 'Sie erwarten ein Kind oder sind schwanger',
  'Geburt': 'Sie haben gerade ein Kind bekommen',
  'Heirat': 'Sie haben geheiratet oder planen zu heiraten',
  'Trennung': 'Sie leben getrennt von Ihrem Partner',
  'Scheidung': 'Sie lassen sich scheiden oder sind geschieden',
  'Tod': 'Ein Familienmitglied ist verstorben',
  'Arbeitslosigkeit': 'Sie sind arbeitslos geworden',
  'Erkrankung': 'Sie oder ein Familienmitglied sind erkrankt',
  'Pflege': 'Sie pflegen einen Angehörigen',
  'Umzug': 'Sie ziehen um oder sind umgezogen',
  'Ausbildung': 'Sie beginnen eine Ausbildung oder studieren',
  'Renteneintritt': 'Sie gehen in Rente oder sind Rentner',
  'Adoption': 'Sie adoptieren ein Kind',
  'Elternzeit': 'Sie nehmen Elternzeit oder sind in Elternzeit',
  'Kinderbetreuung': 'Sie benötigen Kinderbetreuung',
  'Wohnungssuche': 'Sie suchen eine Wohnung',
  'Insolvenz': 'Sie sind von Insolvenz betroffen',
  'Schwerbehinderung': 'Sie oder ein Familienmitglied haben eine Schwerbehinderung',
};

// ============================================================================
// Component
// ============================================================================

const IntakeForm: React.FC<IntakeFormProps> = ({ onSubmit, isLoading = false }) => {
  const [availableSituationen, setAvailableSituationen] = useState<string[]>([]);
  const [expanded, setExpanded] = useState(true);
  const [infoOpen, setInfoOpen] = useState<Record<string, boolean>>({});

  const {
    control,
    handleSubmit,
    formState: { errors, isValid },
    watch,
    setValue,
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      plz: '',
      situationen: [],
    },
    mode: 'onChange',
  });

  const selectedSituationen = watch('situationen', []);
  const plzValue = watch('plz', '');

  // Load available situations on mount
  useEffect(() => {
    const loadSituationen = async () => {
      try {
        const situations = await getAvailableSituationen();
        setAvailableSituationen(situations);
      } catch {
        setAvailableSituationen(COMMON_SITUATIONEN);
      }
    };
    loadSituationen();
  }, []);

  // Handle PLZ change - auto format
  const handlePlzChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    const digitsOnly = value.replace(/\D/g, '');
    const limited = digitsOnly.slice(0, 5);
    setValue('plz', limited);
  };

  // Handle PLZ blur - format to 5 digits
  const handlePlzBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    const value = e.target.value;
    if (value && value.length < 5) {
      setValue('plz', formatPlz(value));
    }
  };

  // Toggle situation selection
  const toggleSituation = (situation: string) => {
    const current = selectedSituationen || [];
    const newSelection = current.includes(situation)
      ? current.filter((s) => s !== situation)
      : [...current, situation];
    setValue('situationen', newSelection);
  };

  // Check if situation is selected
  const isSelected = (situation: string): boolean => {
    return (selectedSituationen || []).includes(situation);
  };

  // Get situations to display
  const displaySituationen = availableSituationen.length > 0
    ? availableSituationen
    : COMMON_SITUATIONEN;

  // Toggle info for a situation
  const toggleInfo = (situation: string) => {
    setInfoOpen((prev) => ({
      ...prev,
      [situation]: !prev[situation],
    }));
  };

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
      {/* PLZ Input */}
      <Box mb={4}>
        <Controller
          name="plz"
          control={control}
          render={({ field }) => (
            <TextField
              {...field}
              label="Postleitzahl"
              placeholder="z.B. 80331"
              fullWidth
              variant="outlined"
              error={!!errors.plz}
              helperText={errors.plz?.message}
              inputProps={{ maxLength: 5 }}
              onChange={handlePlzChange}
              onBlur={handlePlzBlur}
              InputLabelProps={{ shrink: true }}
            />
          )}
        />
      </Box>

      {/* Situations Selection Header */}
      <Box mb={2}>
        <Typography variant="subtitle1" component="h3" sx={{ fontWeight: 600 }}>
          Lebenssituationen
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Wählen Sie alle zutreffenden Lebenssituationen aus
        </Typography>
      </Box>

      {/* Error Message for Situations */}
      {errors.situationen && (
        <Typography color="error" variant="body2" sx={{ mb: 2 }}>
          {errors.situationen.message}
        </Typography>
      )}

      {/* Situations Grid */}
      <Paper
        elevation={0}
        variant="outlined"
        sx={{
          mb: 3,
          p: 2,
          backgroundColor: 'background.paper',
          borderRadius: 2,
        }}
      >
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          mb={2}
          onClick={() => setExpanded(!expanded)}
          sx={{ cursor: 'pointer' }}
        >
          <Typography variant="body1" sx={{ fontWeight: 500 }}>
            {selectedSituationen.length > 0
              ? `${selectedSituationen.length} ausgewählt`
              : 'Wählen Sie Ihre Lebenssituationen'}
          </Typography>
          {selectedSituationen.length > 0 && (
            <Chip
              label={selectedSituationen.length}
              size="small"
              color="primary"
              sx={{ mr: 1 }}
            />
          )}
          <IconButton size="small" onClick={(e) => {
            e.stopPropagation();
            setExpanded(!expanded);
          }}>
            {expanded ? <ExpandLess /> : <ExpandMore />}
          </IconButton>
        </Box>

        <Collapse in={expanded}>
          <FormGroup row={false}>
            <Box
              display="grid"
              gridTemplateColumns="repeat(auto-fill, minmax(280px, 1fr))"
              gap={2}
            >
              {displaySituationen.map((situation) => {
                const description = SITUATIONEN_DESCRIPTIONS[situation] || '';
                return (
                  <Box key={situation}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={isSelected(situation)}
                          onChange={() => toggleSituation(situation)}
                          onClick={(e) => e.stopPropagation()}
                          color="primary"
                          icon={<span />}
                          checkedIcon={<CheckIcon />}
                        />
                      }
                      label={
                        <Box
                          display="flex"
                          alignItems="center"
                          justifyContent="space-between"
                          width="100%"
                        >
                          <Typography variant="body1">{situation}</Typography>
                          {description && (
                            <Tooltip title={description} arrow>
                              <IconButton
                                size="small"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  toggleInfo(situation);
                                }}
                                sx={{ p: 0.5 }}
                              >
                                <InfoIcon
                                  fontSize="small"
                                  color={infoOpen[situation] ? 'primary' : 'action'}
                                />
                              </IconButton>
                            </Tooltip>
                          )}
                        </Box>
                      }
                      sx={{
                        width: '100%',
                        m: 0,
                        borderRadius: 1,
                        '&:hover': {
                          backgroundColor: 'action.hover',
                        },
                      }}
                      component="div"
                    />
                    {description && infoOpen[situation] && (
                      <Box
                        sx={{
                          pl: 4,
                          pb: 1,
                          pt: 0.5,
                          color: 'text.secondary',
                          fontSize: '0.875rem',
                        }}
                      >
                        {description}
                      </Box>
                    )}
                  </Box>
                );
              })}
            </Box>
          </FormGroup>
        </Collapse>

        {/* Selected Situations Preview */}
        {selectedSituationen.length > 0 && (
          <Box mt={2}>
            <Divider sx={{ my: 1 }} />
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
              Ausgewählt:
            </Typography>
            <Box display="flex" flexWrap="wrap" gap={1}>
              {selectedSituationen.map((situation) => (
                <Chip
                  key={situation}
                  label={situation}
                  size="small"
                  color="primary"
                  onDelete={() => toggleSituation(situation)}
                  deleteIcon={<CloseIcon fontSize="small" />}
                />
              ))}
            </Box>
          </Box>
        )}
      </Paper>

      {/* Submit Button */}
      <Box display="flex" justifyContent="flex-end" mt={2}>
        <Button
          type="submit"
          variant="contained"
          size="large"
          disabled={!isValid || isLoading}
          sx={{ minWidth: 150 }}
        >
          {isLoading ? 'Lädt...' : 'Leistungen prüfen'}
        </Button>
      </Box>
    </Box>
  );
};

export default IntakeForm;
