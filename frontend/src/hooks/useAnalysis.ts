import { useCallback, useEffect, useState } from "react";
import { getAnalysis, getReport } from "../services/analyses";
import type { AnalysisResponse } from "../types/api";
import type { ClinicalReportResponse } from "../types/clinicalReport";

interface State {
  analysis: AnalysisResponse | null;
  report: ClinicalReportResponse | null;
  reportError: unknown;
  loading: boolean;
  error: unknown;
}

/** Loads one analysis, and its report too if the analysis is COMPLETED.
 * A REPORT_NOT_READY (409) for a non-completed analysis is expected, not
 * a page-level error — surfaced separately via `reportError`. */
export function useAnalysisDetail(id: string | undefined) {
  const [state, setState] = useState<State>({ analysis: null, report: null, reportError: null, loading: true, error: null });

  const load = useCallback(() => {
    if (!id) return;
    setState({ analysis: null, report: null, reportError: null, loading: true, error: null });
    getAnalysis(id)
      .then(async (analysis) => {
        if (analysis.status !== "COMPLETED") {
          setState({ analysis, report: null, reportError: null, loading: false, error: null });
          return;
        }
        try {
          const report = await getReport(id);
          setState({ analysis, report, reportError: null, loading: false, error: null });
        } catch (reportError) {
          setState({ analysis, report: null, reportError, loading: false, error: null });
        }
      })
      .catch((error: unknown) => {
        setState({ analysis: null, report: null, reportError: null, loading: false, error });
      });
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  return { ...state, reload: load };
}
