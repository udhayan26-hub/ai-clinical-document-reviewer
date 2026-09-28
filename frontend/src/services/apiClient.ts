import type { ErrorResponse } from "../types/api";

const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000/api";

/**
 * A backend error, normalized from the API's error envelope
 * (`{ error: { code, message, details, request_id } }`). Thrown by
 * `request()` for any non-2xx response, and for network failures (the
 * API being unreachable), so callers only ever need one catch shape.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown> | null;
  readonly requestId: string | null;

  constructor(
    status: number,
    code: string,
    message: string,
    details: Record<string, unknown> | null = null,
    requestId: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }

  /** True when the API could not be reached at all (backend down, CORS, offline). */
  get isNetworkError(): boolean {
    return this.status === 0;
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "Could not reach the server. Check your connection and try again.");
  }

  if (!response.ok) {
    let body: ErrorResponse | null = null;
    try {
      body = (await response.json()) as ErrorResponse;
    } catch {
      // response wasn't JSON (e.g. a proxy error page) — fall through to the generic error below
    }
    if (body?.error) {
      throw new ApiError(response.status, body.error.code, body.error.message, body.error.details, body.error.request_id);
    }
    throw new ApiError(response.status, "UNKNOWN_ERROR", `Request failed with status ${response.status}.`);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
