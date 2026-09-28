import type { EvidenceSpan } from "../types/clinicalReport";

/** Visually connects a finding to the exact source text it came from —
 * never rendered for an inferred finding with no evidence (there is none). */
export default function EvidenceCard({ evidence }: { evidence: EvidenceSpan[] }) {
  if (evidence.length === 0) return null;
  return (
    <div className="mt-2 space-y-1.5">
      {evidence.map((span, i) => (
        <blockquote
          key={i}
          className="border-l-2 border-sky-300 bg-sky-50/60 px-3 py-1.5 text-[12.5px] italic leading-relaxed text-slate-700"
        >
          “{span.quote}”
          {span.context && <span className="ml-1 not-italic text-slate-400">— {span.context}</span>}
        </blockquote>
      ))}
    </div>
  );
}
