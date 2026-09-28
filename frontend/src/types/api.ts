/**
 * Types mirroring backend/app/schemas/{analysis,document,common}.py.
 * Keep these in sync manually until an OpenAPI-codegen step is added
 * (see docs/decisions/002-backend.md).
 */

export type AnalysisStatus =
  | "PENDING"
  | "VALIDATING"
  | "EXTRACTING"
  | "ANALYZING"
  | "COMPLETED"
  | "FAILED";

export type DocumentSourceType = "TEXT" | "IMAGE" | "PDF";

export interface DocumentSummary {
  id: string;
  source_type: DocumentSourceType;
  original_filename: string | null;
  content_type: string | null;
  size_bytes: number;
  created_at: string; // ISO 8601
}

export interface AnalysisResponse {
  id: string;
  status: AnalysisStatus;
  document: DocumentSummary;
  error_code: string | null;
  error_message: string | null;
  report_available: boolean;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface Pagination {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface Page<T> {
  items: T[];
  pagination: Pagination;
}

/** Query params accepted by GET /api/v1/analyses. */
export interface AnalysisListQuery {
  page?: number;
  page_size?: number;
  status?: AnalysisStatus;
}

/**
 * POST /api/v1/analyses is multipart/form-data with exactly one of
 * `text` or `file` set — there is no JSON request body, so this type
 * documents the form fields rather than a serializable object.
 */
export interface CreateAnalysisFormFields {
  text?: string;
  file?: File;
}

export interface ErrorDetail {
  code: string;
  message: string;
  details: Record<string, unknown> | null;
  request_id: string;
}

export interface ErrorResponse {
  error: ErrorDetail;
}
