import { useParams } from "react-router-dom";
import { useAnalysisDetail } from "../hooks/useAnalysis";
import AnalysisStatusBadge from "../components/AnalysisStatusBadge";
import PipelineProgress from "../components/PipelineProgress";
import ReportSection from "../components/ReportSection";
import FindingItem from "../components/FindingItem";
import WarningBanner from "../components/WarningBanner";
import LoadingState from "../components/LoadingState";
import ErrorState from "../components/ErrorState";
import { formatDateTime, getFailureMessage } from "../lib/format";
import type { ClinicalReport, SourcedFinding } from "../types/clinicalReport";

export default function AnalysisDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { analysis, report, reportError, loading, error, reload } = useAnalysisDetail(id);

  if (loading) return <LoadingState label="Loading analysis…" />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (!analysis) return <ErrorState error={new Error("Analysis not found.")} />;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-mono text-xs text-slate-400">{analysis.id}</p>
            <div className="mt-1 flex items-center gap-2">
              <h1 className="text-lg font-semibold text-slate-900">
                {analysis.document.original_filename ?? "Pasted clinical text"}
              </h1>
              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium uppercase text-slate-600">
                {analysis.document.source_type}
              </span>
            </div>
          </div>
          <AnalysisStatusBadge status={analysis.status} />
        </div>

        <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-1 text-xs text-slate-500 sm:grid-cols-4">
          <div>
            <dt className="font-medium text-slate-400">Submitted</dt>
            <dd>{formatDateTime(analysis.created_at)}</dd>
          </div>
          <div>
            <dt className="font-medium text-slate-400">Completed</dt>
            <dd>{formatDateTime(analysis.completed_at)}</dd>
          </div>
          {report && (
            <>
              <div>
                <dt className="font-medium text-slate-400">Provider</dt>
                <dd>{report.ai_provider}</dd>
              </div>
              <div>
                <dt className="font-medium text-slate-400">Model</dt>
                <dd>{report.ai_model_name}</dd>
              </div>
            </>
          )}
        </dl>

        {analysis.status !== "COMPLETED" && (
          <div className="mt-5 border-t border-slate-100 pt-5">
            <PipelineProgress status={analysis.status} errorCode={analysis.error_code} />
          </div>
        )}
      </div>

      {analysis.status === "FAILED" &&
        (() => {
          const { headline, message } = getFailureMessage(analysis.error_code);
          return (
            <WarningBanner tone="danger" title={headline}>
              <p>{message}</p>
              {analysis.error_code && (
                <p className="mt-1 font-mono text-[11px] opacity-75">Technical code: {analysis.error_code}</p>
              )}
            </WarningBanner>
          );
        })()}

      {(analysis.status === "PENDING" ||
        analysis.status === "VALIDATING" ||
        analysis.status === "EXTRACTING" ||
        analysis.status === "ANALYZING") && (
        <WarningBanner tone="info" title="Still processing">
          This analysis has not finished yet. Refresh to check for an update.
        </WarningBanner>
      )}

      {analysis.status === "COMPLETED" && Boolean(reportError) && (
        <ErrorState error={reportError} onRetry={reload} />
      )}

      {report && <ReportView report={report.report} />}
    </div>
  );
}

function ReportView({ report }: { report: ClinicalReport }) {
  const allFindings = [
    ...report.symptoms,
    ...report.diagnoses,
    ...report.medications,
    ...report.vitals,
    ...report.allergies,
    ...report.clinical_observations,
    ...report.clinical_concerns,
    report.patient_information,
  ];
  const uncertainCount = allFindings.filter((f) => f.inferred || f.confidence !== "HIGH").length;

  return (
    <div className="space-y-5">
      <WarningBanner tone="warning" title="AI-generated clinical review — requires professional verification.">
        This report is a document-review aid, not a diagnosis. Every finding below shows its confidence and, where
        stated directly in the document, the exact supporting quote. Findings without a quote are the model's
        interpretation, not a transcription of the source.
      </WarningBanner>

      <ReportSection title="Clinical Summary">
        <p className="text-sm leading-relaxed text-slate-700">{report.report_summary}</p>
      </ReportSection>

      <ReportSection title="Confidence & Uncertainty">
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <span className={`font-medium ${report.requires_review ? "text-amber-700" : "text-emerald-700"}`}>
            {report.requires_review ? "Requires clinician review" : "No uncertainty flagged"}
          </span>
          <span className="text-slate-500">{uncertainCount} of {allFindings.length} findings are inferred or below high confidence</span>
        </div>
      </ReportSection>

      {(report.patient_information.name ||
        report.patient_information.age ||
        report.patient_information.sex ||
        Object.keys(report.patient_information.additional_identifiers).length > 0) && (
        <ReportSection title="Patient Information">
          <FindingItem
            title={[report.patient_information.name, report.patient_information.age, report.patient_information.sex]
              .filter(Boolean)
              .join(" · ") || "Not stated"}
            finding={report.patient_information}
          />
        </ReportSection>
      )}

      <ReportSection title="Key Findings" count={report.clinical_observations.length}>
        <FindingList
          items={report.clinical_observations}
          empty="No clinical observations were extracted."
          render={(o) => ({ title: o.description, meta: o.category })}
        />
      </ReportSection>

      <ReportSection title="Symptoms" count={report.symptoms.length}>
        <FindingList
          items={report.symptoms}
          empty="No symptoms were mentioned in the document."
          render={(s) => ({ title: s.description, meta: [s.onset, s.severity].filter(Boolean).join(" · ") })}
        />
      </ReportSection>

      <ReportSection title="Diagnoses / Clinical Impressions" count={report.diagnoses.length}>
        <FindingList
          items={report.diagnoses}
          empty="No diagnoses were stated in the document."
          render={(d) => ({ title: d.condition, meta: [d.status, d.icd10_code].filter(Boolean).join(" · ") })}
        />
      </ReportSection>

      <ReportSection title="Medications" count={report.medications.length}>
        <FindingList
          items={report.medications}
          empty="No medications were mentioned in the document."
          render={(m) => ({ title: m.name, meta: [m.dosage, m.frequency, m.route].filter(Boolean).join(" · ") })}
        />
      </ReportSection>

      <ReportSection title="Vitals & Investigations" count={report.vitals.length}>
        <FindingList
          items={report.vitals}
          empty="No vital signs or investigation results were found."
          render={(v) => ({ title: `${v.name}: ${v.value}${v.unit ? ` ${v.unit}` : ""}`, meta: v.recorded_at })}
        />
      </ReportSection>

      <ReportSection title="Allergies" count={report.allergies.length}>
        <FindingList
          items={report.allergies}
          empty="No allergies were mentioned in the document."
          render={(a) => ({ title: a.substance, meta: [a.reaction, a.severity].filter(Boolean).join(" · ") })}
        />
      </ReportSection>

      <ReportSection title="Warnings & Clinical Concerns" count={report.clinical_concerns.length}>
        <FindingList
          items={report.clinical_concerns}
          empty="No specific concerns were flagged."
          render={(c) => ({ title: c.description, meta: [c.severity, c.recommended_action].filter(Boolean).join(" · ") })}
        />
        {report.potential_inconsistencies.length > 0 && (
          <div className="mt-4 space-y-2 border-t border-slate-100 pt-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Potential inconsistencies</p>
            {report.potential_inconsistencies.map((inc, i) => (
              <div key={i} className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">
                {inc.description}
              </div>
            ))}
          </div>
        )}
      </ReportSection>

      <ReportSection title="Missing Information" count={report.missing_information.length}>
        {report.missing_information.length === 0 ? (
          <p className="text-sm text-slate-400">The extraction did not flag any missing expected information.</p>
        ) : (
          <ul className="space-y-1.5">
            {report.missing_information.map((item, i) => (
              <li key={i} className="text-sm text-slate-700">
                <span className="font-medium">{item.field}</span>
                {item.reason && <span className="text-slate-500"> — {item.reason}</span>}
              </li>
            ))}
          </ul>
        )}
      </ReportSection>

      <ReportSection title="Limitations">
        <ul className="list-disc space-y-1 pl-4 text-sm text-slate-600">
          <li>This system reviews and structures document content — it does not make or suggest a diagnosis.</li>
          <li>Findings are grounded in the submitted document only, not general medical knowledge.</li>
          <li>Handwritten or low-quality scanned documents may reduce extraction accuracy.</li>
          <li>All output must be verified by a qualified clinician before any use.</li>
        </ul>
      </ReportSection>
    </div>
  );
}

function FindingList<T extends SourcedFinding>({
  items,
  empty,
  render,
}: {
  items: T[];
  empty: string;
  render: (item: T) => { title: string; meta?: string | null };
}) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-400">{empty}</p>;
  }
  return (
    <ul>
      {items.map((item, i) => {
        const { title, meta } = render(item);
        return <FindingItem key={i} title={title} meta={meta} finding={item} />;
      })}
    </ul>
  );
}
