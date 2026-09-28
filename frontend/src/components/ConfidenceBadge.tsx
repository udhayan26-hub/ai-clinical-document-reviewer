import type { ConfidenceLevel } from "../types/clinicalReport";

const COLOR: Record<ConfidenceLevel, string> = {
  HIGH: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  MEDIUM: "bg-amber-50 text-amber-700 ring-amber-600/20",
  LOW: "bg-rose-50 text-rose-700 ring-rose-600/20",
};

interface Props {
  confidence: ConfidenceLevel;
  inferred?: boolean;
}

/** Never renders an inferred/non-HIGH finding the same as a directly-quoted,
 * high-confidence one — see frontend/src/types/clinicalReport.ts. */
export default function ConfidenceBadge({ confidence, inferred }: Props) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${COLOR[confidence]}`}>
        {confidence}
      </span>
      {inferred && (
        <span
          className="inline-flex items-center rounded-full bg-violet-50 px-2 py-0.5 text-[11px] font-medium text-violet-700 ring-1 ring-inset ring-violet-600/20"
          title="Interpreted/summarized by the AI, not a direct quote from the document"
        >
          Inferred
        </span>
      )}
    </span>
  );
}
