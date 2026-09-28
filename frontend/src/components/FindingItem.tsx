import type { SourcedFinding } from "../types/clinicalReport";
import ConfidenceBadge from "./ConfidenceBadge";
import EvidenceCard from "./EvidenceCard";

interface Props {
  title: string;
  meta?: string | null;
  finding: SourcedFinding;
}

/** One row inside a ReportSection list (symptoms, diagnoses, medications,
 * ...) — every finding shape shares confidence/evidence/inferred, so this
 * is the one place that renders them consistently. */
export default function FindingItem({ title, meta, finding }: Props) {
  return (
    <li className="border-b border-slate-100 py-3 last:border-0">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-900">{title}</p>
          {meta && <p className="text-xs text-slate-500">{meta}</p>}
        </div>
        <ConfidenceBadge confidence={finding.confidence} inferred={finding.inferred} />
      </div>
      <EvidenceCard evidence={finding.evidence} />
    </li>
  );
}
