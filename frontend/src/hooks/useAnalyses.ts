import { useCallback, useEffect, useState } from "react";
import { listAnalyses, type ListAnalysesParams } from "../services/analyses";
import type { AnalysisResponse, Page } from "../types/api";

interface State {
  data: Page<AnalysisResponse> | null;
  loading: boolean;
  error: unknown;
}

export function useAnalyses(params: ListAnalysesParams) {
  const [state, setState] = useState<State>({ data: null, loading: true, error: null });
  const key = JSON.stringify(params);

  const load = useCallback(() => {
    setState((s) => ({ ...s, loading: true, error: null }));
    listAnalyses(params)
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((error) => setState({ data: null, loading: false, error }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    load();
  }, [load]);

  return { ...state, reload: load };
}
