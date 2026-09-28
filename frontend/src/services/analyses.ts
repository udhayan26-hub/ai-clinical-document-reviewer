import type { AnalysisResponse, AnalysisStatus, Page } from "../types/api";
import type { ClinicalReportResponse } from "../types/clinicalReport";
import { request } from "./apiClient";

export interface CreateAnalysisInput {
  text?: string;
  file?: File;
}

/**
 * POST /api/v1/analyses. Exactly one of text/file must be set — enforced
 * by the caller (the New Analysis page), not here. The backend now runs
 * the full pipeline synchronously before responding, so this call blocks
 * until the analysis reaches COMPLETED or FAILED — there is no
 * intermediate PENDING response to poll.
 */
export async function createAnalysis(input: CreateAnalysisInput): Promise<AnalysisResponse> {
  const formData = new FormData();
  if (input.text !== undefined) {
    formData.append("text", input.text);
  }
  if (input.file !== undefined) {
    formData.append("file", input.file);
  }
  return request<AnalysisResponse>("/v1/analyses", { method: "POST", body: formData });
}

export interface ListAnalysesParams {
  page?: number;
  page_size?: number;
  status?: AnalysisStatus;
}

export async function listAnalyses(params: ListAnalysesParams = {}): Promise<Page<AnalysisResponse>> {
  const query = new URLSearchParams();
  if (params.page) query.set("page", String(params.page));
  if (params.page_size) query.set("page_size", String(params.page_size));
  if (params.status) query.set("status", params.status);
  const qs = query.toString();
  return request<Page<AnalysisResponse>>(`/v1/analyses${qs ? `?${qs}` : ""}`);
}

export async function getAnalysis(id: string): Promise<AnalysisResponse> {
  return request<AnalysisResponse>(`/v1/analyses/${id}`);
}

/** Throws ApiError with code REPORT_NOT_READY (409) if not yet COMPLETED. */
export async function getReport(id: string): Promise<ClinicalReportResponse> {
  return request<ClinicalReportResponse>(`/v1/analyses/${id}/report`);
}
