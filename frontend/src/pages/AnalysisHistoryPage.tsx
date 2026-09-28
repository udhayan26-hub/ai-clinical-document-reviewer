import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAnalyses } from "../hooks/useAnalyses";
import AnalysisStatusBadge from "../components/AnalysisStatusBadge";
import EmptyState from "../components/EmptyState";
import LoadingState from "../components/LoadingState";
import ErrorState from "../components/ErrorState";
import { formatDateTime } from "../lib/format";

const PAGE_SIZE = 20;

export default function AnalysisHistoryPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useAnalyses({ page, page_size: PAGE_SIZE, status: "COMPLETED" });

  const items = data?.items ?? [];
  const pagination = data?.pagination;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Analysis History</h1>
        <p className="mt-1 text-sm text-slate-500">Every successfully completed review, most recent first.</p>
      </div>

      {loading && <LoadingState label="Loading analysis history…" />}
      {!loading && Boolean(error) && <ErrorState error={error} onRetry={reload} />}
      {!loading && !error && items.length === 0 && (
        <EmptyState title="No analyses yet" description="Submissions will appear here once you run your first analysis." />
      )}

      {!loading && !error && items.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  {["Analysis", "Type", "Status", "Created", "Completed", "Report"].map((h) => (
                    <th key={h} className="whitespace-nowrap px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((analysis) => (
                  <tr
                    key={analysis.id}
                    onClick={() => navigate(`/analyses/${analysis.id}`)}
                    className="cursor-pointer hover:bg-slate-50"
                  >
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-600">
                      {analysis.id.slice(0, 8)}…
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium uppercase text-slate-600">
                        {analysis.document.source_type}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <AnalysisStatusBadge status={analysis.status} />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-slate-600">{formatDateTime(analysis.created_at)}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-slate-600">{formatDateTime(analysis.completed_at)}</td>
                    <td className="whitespace-nowrap px-4 py-3">
                      {analysis.report_available ? (
                        <span className="text-emerald-600">Available</span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {pagination && pagination.total_pages > 1 && (
            <div className="flex items-center justify-between text-sm">
              <p className="text-slate-500">
                Page {pagination.page} of {pagination.total_pages} · {pagination.total_items} total
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                  className="rounded-md px-3 py-1.5 text-sm font-medium text-slate-600 ring-1 ring-inset ring-slate-300 hover:bg-white disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  type="button"
                  disabled={page >= pagination.total_pages}
                  onClick={() => setPage((p) => p + 1)}
                  className="rounded-md px-3 py-1.5 text-sm font-medium text-slate-600 ring-1 ring-inset ring-slate-300 hover:bg-white disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
