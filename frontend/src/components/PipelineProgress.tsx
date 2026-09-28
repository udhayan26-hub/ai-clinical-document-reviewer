import type { AnalysisStatus } from "../types/api";
import { buildPipelineStages } from "../lib/format";

interface Props {
  status: AnalysisStatus | "IN_FLIGHT";
  errorCode?: string | null;
}

const ICON = {
  done: (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
      <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
    </svg>
  ),
  failed: (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
    </svg>
  ),
};

export default function PipelineProgress({ status, errorCode = null }: Props) {
  const stages = buildPipelineStages(status === "IN_FLIGHT" ? "PENDING" : status, errorCode);

  return (
    <ol className="flex flex-col gap-0 sm:flex-row sm:items-center sm:gap-0">
      {stages.map((stage, index) => (
        <li key={stage.key} className="flex flex-1 items-center">
          <div className="flex flex-col items-center gap-1.5 sm:flex-1">
            <div
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                stage.state === "done"
                  ? "bg-emerald-100 text-emerald-700"
                  : stage.state === "failed"
                    ? "bg-rose-100 text-rose-700"
                    : stage.state === "active"
                      ? "bg-sky-100 text-sky-700"
                      : "bg-slate-100 text-slate-400"
              }`}
            >
              {stage.state === "done" && ICON.done}
              {stage.state === "failed" && ICON.failed}
              {stage.state === "active" && <span className="h-3 w-3 animate-spin rounded-full border-2 border-sky-300 border-t-sky-700" />}
              {(stage.state === "skipped" || stage.state === "pending") && <span>{index + 1}</span>}
            </div>
            <span
              className={`text-[11px] font-medium ${
                stage.state === "failed"
                  ? "text-rose-700"
                  : stage.state === "skipped" || stage.state === "pending"
                    ? "text-slate-400"
                    : "text-slate-700"
              }`}
            >
              {stage.label}
            </span>
          </div>
          {index < stages.length - 1 && (
            <div className={`hidden h-px flex-1 sm:block ${stage.state === "done" ? "bg-emerald-200" : "bg-slate-200"}`} />
          )}
        </li>
      ))}
    </ol>
  );
}
