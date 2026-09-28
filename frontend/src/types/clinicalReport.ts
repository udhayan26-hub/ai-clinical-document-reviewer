/**
 * Types mirroring backend/app/schemas/clinical_report.py — the AI/ML
 * structured report contract. Keep in sync manually (see
 * docs/decisions/002-backend.md for the planned codegen follow-up).
 *
 * Design note ("don't make unsupported information appear factual"):
 * every finding carries `confidence`, `evidence` (verbatim source
 * quotes), and `inferred`. The UI must visually distinguish
 * `inferred: true` / non-HIGH-confidence findings from directly-quoted,
 * high-confidence ones — never render them identically.
 */

export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";

export interface EvidenceSpan {
  quote: string;
  context: string | null;
}

/** Common provenance fields present on every clinical finding type. */
export interface SourcedFinding {
  confidence: ConfidenceLevel;
  evidence: EvidenceSpan[];
  inferred: boolean;
}

export interface PatientInformation extends SourcedFinding {
  name: string | null;
  age: string | null;
  sex: string | null;
  date_of_birth: string | null;
  additional_identifiers: Record<string, string>;
}

export interface Symptom extends SourcedFinding {
  description: string;
  onset: string | null;
  severity: string | null;
}

export interface Diagnosis extends SourcedFinding {
  condition: string;
  icd10_code: string | null;
  status: string | null;
}

export interface Medication extends SourcedFinding {
  name: string;
  dosage: string | null;
  frequency: string | null;
  route: string | null;
}

export interface VitalSign extends SourcedFinding {
  name: string;
  value: string;
  unit: string | null;
  recorded_at: string | null;
}

export interface Allergy extends SourcedFinding {
  substance: string;
  reaction: string | null;
  severity: string | null;
}

export interface ClinicalObservation extends SourcedFinding {
  description: string;
  category: string | null;
}

export interface ClinicalConcern extends SourcedFinding {
  description: string;
  severity: string | null;
  recommended_action: string | null;
}

export interface MissingInformationItem {
  field: string;
  reason: string | null;
}

export interface PotentialInconsistency {
  description: string;
  related_fields: string[];
  evidence: EvidenceSpan[];
}

export interface ClinicalReport {
  report_summary: string;
  patient_information: PatientInformation;
  symptoms: Symptom[];
  diagnoses: Diagnosis[];
  medications: Medication[];
  vitals: VitalSign[];
  allergies: Allergy[];
  clinical_observations: ClinicalObservation[];
  clinical_concerns: ClinicalConcern[];
  missing_information: MissingInformationItem[];
  potential_inconsistencies: PotentialInconsistency[];
  requires_review: boolean;
}

/** GET /api/v1/analyses/{analysis_id}/report response body. */
export interface ClinicalReportResponse {
  analysis_id: string;
  report: ClinicalReport;
  ai_provider: string;
  ai_model_name: string;
  generated_at: string;
}
