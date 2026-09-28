import { Link } from "react-router-dom";
import { useAnalyses } from "../hooks/useAnalyses";
import AnalysisCard from "../components/AnalysisCard";
import EmptyState from "../components/EmptyState";
import LoadingState from "../components/LoadingState";
import ErrorState from "../components/ErrorState";
import { IN_PROGRESS_STATUSES } from "../lib/format";

const STAT_CARDS: { key: "total" | "completed" | "failed" | "processing"; label: string; color: string }[] = [
  { key: "total", label: "Total analyses", color: "text-slate-900" },
  { key: "completed", label: "Completed", color: "text-emerald-600" },
  { key: "failed", label: "Failed", color: "text-rose-600" },
  { key: "processing", label: "Pending / processing", color: "text-amber-600" },
];

export default function DashboardPage() {
  // Statistics are derived from real list data (no dedicated stats
  // endpoint exists) — page_size caps how many recent analyses this
  // covers, which is acceptable for this MVP dashboard.
  const { data, loading, error, reload } = useAnalyses({ page: 1, page_size: 50 });

  const items = data?.items ?? [];
  const stats = {
    total: data?.pagination.total_items ?? 0,
    completed: items.filter((a) => a.status === "COMPLETED").length,
    failed: items.filter((a) => a.status === "FAILED").length,
    processing: items.filter((a) => IN_PROGRESS_STATUSES.includes(a.status)).length,
  };

  return (
    <div className="space-y-8">
      <section className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">AI Clinical Document Reviewer</h1>
          <p className="mt-1 max-w-xl text-sm text-slate-500">
            Upload clinical documentation and get a structured, evidence-grounded review — extracted findings, key
            observations, and clearly flagged uncertainty, ready for clinician verification.
          </p>
        </div>
        <Link
          to="/analyze"
          className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-sky-700"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
            <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
          </svg>
          New Analysis
        </Link>
      </section>

      <section className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {STAT_CARDS.map((card) => (
          <div key={card.key} className="rounded-xl border border-slate-200 bg-white px-4 py-4">
            <p className="text-xs font-medium text-slate-500">{card.label}</p>
            <p className={`mt-1.5 text-2xl font-semibold ${card.color}`}>{loading ? "—" : stats[card.key]}</p>
          </div>
        ))}
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">Recent analyses</h2>
          <Link to="/analyses" className="text-xs font-medium text-sky-600 hover:text-sky-700">
            View all →
          </Link>
        </div>

        {loading && <LoadingState label="Loading recent analyses…" />}
        {!loading && Boolean(error) && <ErrorState error={error} onRetry={reload} />}
        {!loading && !error && items.length === 0 && (
          <EmptyState
            title="No analyses yet"
            description="Submit your first clinical document to see it reviewed here."
            action={
              <Link to="/analyze" className="rounded-md bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-700">
                Start an analysis
              </Link>
            }
          />
        )}
        {!loading && !error && items.length > 0 && (
          <div className="space-y-2">
            {items.slice(0, 8).map((analysis) => (
              <AnalysisCard key={analysis.id} analysis={analysis} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
