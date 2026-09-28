import type { AnalysisStatus } from "../types/api";
import { STATUS_COLOR, STATUS_LABEL } from "../lib/format";

export default function AnalysisStatusBadge({ status }: { status: AnalysisStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${STATUS_COLOR[status]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
      {STATUS_LABEL[status]}
    </span>
  );
}
