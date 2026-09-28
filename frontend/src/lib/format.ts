import type { AnalysisStatus } from "../types/api";

export function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export const STATUS_LABEL: Record<AnalysisStatus, string> = {
  PENDING: "Pending",
  VALIDATING: "Validating",
  EXTRACTING: "Extracting",
  ANALYZING: "Analyzing",
  COMPLETED: "Completed",
  FAILED: "Failed",
};

/** Tailwind class groups for status pills/badges — one source of truth
 * for status color so it's consistent across cards, tables, and badges. */
export const STATUS_COLOR: Record<AnalysisStatus, string> = {
  PENDING: "bg-slate-100 text-slate-700 ring-slate-600/20",
  VALIDATING: "bg-amber-50 text-amber-700 ring-amber-600/20",
  EXTRACTING: "bg-amber-50 text-amber-700 ring-amber-600/20",
  ANALYZING: "bg-amber-50 text-amber-700 ring-amber-600/20",
  COMPLETED: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  FAILED: "bg-rose-50 text-rose-700 ring-rose-600/20",
};

export const IN_PROGRESS_STATUSES: AnalysisStatus[] = ["PENDING", "VALIDATING", "EXTRACTING", "ANALYZING"];

/**
 * The backend runs the whole pipeline synchronously within one POST
 * request — there is no intermediate status to poll. This maps the
 * *final* status/error_code back onto the conceptual pipeline stages so
 * the UI can still show which stage succeeded vs. failed, derived from
 * real API data rather than simulated progress.
 */
export type PipelineStageKey = "uploading" | "extracting" | "analyzing" | "validating" | "completed";

export interface PipelineStageState {
  key: PipelineStageKey;
  label: string;
  state: "done" | "failed" | "skipped" | "active" | "pending";
}

const EXTRACTION_ERROR_CODES = new Set([
  "DOCUMENT_BYTES_UNAVAILABLE",
  "EXTRACTION_FAILED",
  "CORRUPTED_FILE",
  "OCR_FAILED",
  "EMPTY_INPUT",
]);
const ANALYZING_ERROR_CODES = new Set([
  "AI_EXTRACTION_FAILED",
  "AI_GENERATION_FAILED",
  "AI_PROCESSING_FAILED",
  "EVIDENCE_MISMATCH",
  "UNSUPPORTED_AI_PROVIDER",
]);
const VALIDATION_ERROR_CODES = new Set(["REPORT_VALIDATION_FAILED"]);

export function buildPipelineStages(status: AnalysisStatus, errorCode: string | null): PipelineStageState[] {
  const stages: { key: PipelineStageKey; label: string }[] = [
    { key: "uploading", label: "Uploading" },
    { key: "extracting", label: "Extracting" },
    { key: "analyzing", label: "Analyzing" },
    { key: "validating", label: "Validating" },
    { key: "completed", label: "Completed" },
  ];

  if (status === "COMPLETED") {
    return stages.map((s) => ({ ...s, state: "done" }));
  }

  if (status === "FAILED") {
    let failedAt: PipelineStageKey = "analyzing"; // reasonable default: most failures are AI-related
    if (errorCode && EXTRACTION_ERROR_CODES.has(errorCode)) failedAt = "extracting";
    else if (errorCode && ANALYZING_ERROR_CODES.has(errorCode)) failedAt = "analyzing";
    else if (errorCode && VALIDATION_ERROR_CODES.has(errorCode)) failedAt = "validating";

    let reachedFailure = false;
    return stages.map((s) => {
      if (s.key === "uploading") return { ...s, state: "done" };
      if (s.key === failedAt) {
        reachedFailure = true;
        return { ...s, state: "failed" };
      }
      return { ...s, state: reachedFailure ? "skipped" : "done" };
    });
  }

  // In-flight (only visible client-side while the blocking POST is pending —
  // the backend has no intermediate state to report yet). "extracting" is
  // shown done because it's structurally guaranteed to have already run:
  // AnalysisService.run_pipeline() always finishes document normalization
  // (measured negligible, ~0.02ms) before ever calling the AI provider —
  // this isn't a guess, it's the real, fixed order of the code that runs
  // for every request. "analyzing" — the two real AI calls — is where
  // virtually all of the ~80s wait actually happens, so it's the only
  // stage shown as in-progress; the rest are genuinely not yet reached.
  return stages.map((s) => {
    if (s.key === "uploading" || s.key === "extracting") return { ...s, state: "done" };
    if (s.key === "analyzing") return { ...s, state: "active" };
    return { ...s, state: "pending" };
  });
}
