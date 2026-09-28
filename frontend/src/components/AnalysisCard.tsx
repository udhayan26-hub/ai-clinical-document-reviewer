import { Link } from "react-router-dom";
import type { AnalysisResponse } from "../types/api";
import { formatDateTime } from "../lib/format";
import AnalysisStatusBadge from "./AnalysisStatusBadge";

export default function AnalysisCard({ analysis }: { analysis: AnalysisResponse }) {
  return (
    <Link
      to={`/analyses/${analysis.id}`}
      className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white px-4 py-3.5 transition-colors hover:border-slate-300 hover:bg-slate-50"
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium uppercase tracking-wide text-slate-600">
            {analysis.document.source_type}
          </span>
          <p className="truncate text-sm font-medium text-slate-900">
            {analysis.document.original_filename ?? "Pasted clinical text"}
          </p>
        </div>
        <p className="mt-1 text-xs text-slate-500">Submitted {formatDateTime(analysis.created_at)}</p>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <AnalysisStatusBadge status={analysis.status} />
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4 text-slate-400">
          <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
        </svg>
      </div>
    </Link>
  );
}
