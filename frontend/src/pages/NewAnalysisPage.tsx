import { useState } from "react";
import { useNavigate } from "react-router-dom";
import UploadDropzone from "../components/UploadDropzone";
import TextInput from "../components/TextInput";
import PipelineProgress from "../components/PipelineProgress";
import WarningBanner from "../components/WarningBanner";
import { createAnalysis } from "../services/analyses";
import { ApiError } from "../services/apiClient";

type Mode = "text" | "file";

export default function NewAnalysisPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("text");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<ApiError | null>(null);

  const canSubmit = mode === "text" ? text.trim().length > 0 : file !== null;

  function switchMode(next: Mode) {
    setMode(next);
    setSubmitError(null);
  }

  async function handleSubmit() {
    if (!canSubmit || submitting) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const analysis = await createAnalysis(mode === "text" ? { text } : { file: file! });
      // The pipeline already ran synchronously — go straight to the
      // detail page, which shows the final status/report/error.
      navigate(`/analyses/${analysis.id}`);
    } catch (error) {
      setSubmitting(false);
      if (error instanceof ApiError) {
        setSubmitError(error);
      } else {
        setSubmitError(new ApiError(0, "UNKNOWN_ERROR", "Something went wrong submitting the document."));
      }
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">New Analysis</h1>
        <p className="mt-1 text-sm text-slate-500">Submit a clinical document as text or a file for AI-assisted review.</p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="mb-4 inline-flex rounded-lg bg-slate-100 p-1">
          <button
            type="button"
            disabled={submitting}
            onClick={() => switchMode("text")}
            className={`rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors ${
              mode === "text" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Paste text
          </button>
          <button
            type="button"
            disabled={submitting}
            onClick={() => switchMode("file")}
            className={`rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors ${
              mode === "file" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Upload file
          </button>
        </div>

        {mode === "text" ? (
          <TextInput value={text} onChange={setText} disabled={submitting} />
        ) : (
          <UploadDropzone file={file} onChange={setFile} disabled={submitting} />
        )}

        {submitError && (
          <div className="mt-4">
            <WarningBanner tone="danger" title={submitError.message}>
              {submitError.code !== "UNKNOWN_ERROR" && <span>Error code: {submitError.code}</span>}
            </WarningBanner>
          </div>
        )}

        <div className="mt-5 flex items-center justify-between">
          <p className="text-xs text-slate-400">Exactly one of text or a file is submitted per analysis.</p>
          <button
            type="button"
            disabled={!canSubmit || submitting}
            onClick={handleSubmit}
            className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-sky-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {submitting && <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />}
            {submitting ? "Analyzing…" : "Submit for analysis"}
          </button>
        </div>
      </div>

      {submitting && (
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <p className="mb-4 text-sm font-medium text-slate-700">Processing your document — this can take a moment.</p>
          <PipelineProgress status="IN_FLIGHT" />
        </div>
      )}
    </div>
  );
}
