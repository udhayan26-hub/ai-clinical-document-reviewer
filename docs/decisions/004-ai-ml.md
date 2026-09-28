# 004. AI/ML layer: interface-first, provider-agnostic, with a mandatory validation gate

## Problem

The system must run clinical analysis via *some* AI/ML approach, but the specific model/provider is explicitly not to be hard-coded, must be swappable later, and must never let unsupported model output be presented as fact.

## Decision

Define the AI/ML pipeline purely as interfaces in this phase — `DocumentProcessor` (`backend/app/document_processing/interfaces.py`), and `ClinicalInformationExtractor`, `ClinicalReportGenerator`, `StructuredOutputValidator` (`backend/app/ai/interfaces.py`) — with zero provider SDK code. Concrete implementations will live behind these interfaces, with pipeline-specific logic (prompts, provider calls, evaluation) isolated in the independent top-level `ml/` package, selected via `AI_PROVIDER`/`AI_MODEL_NAME` settings.

> **Update (document-processing foundation phase):** `DocumentProcessor` now has real implementations — `TextProcessor`, `PDFProcessor`, and `ImageProcessor` (the latter two via a local, offline `OCREngine`; see [007-ocr.md](007-ocr.md)). None of this involves an LLM or any external service. This doesn't change the decision above: `ai/interfaces.py` (the actual AI/ML/LLM boundary this ADR is about) is still interfaces only, with no provider selected or called anywhere.
>
> **Update (AI/ML pipeline foundation phase):** `ai/interfaces.py` has been reshaped — `ClinicalInformationExtractor`+`ClinicalReportGenerator` are consolidated into one `AIProvider(extract, generate)`, and `StructuredOutputValidator` is renamed/reshaped to `ClinicalReportValidator` with one deterministic (non-LLM) implementation. `AnalysisService.run_pipeline()` now really runs this, but the only `AIProvider` that exists is `UnconfiguredAIProvider` — it raises rather than fabricating output, so this ADR's core claim ("no provider selected or called") still holds in spirit: no *working* provider exists, by design. Full rationale: [008-ai-pipeline.md](008-ai-pipeline.md).

## Rationale

- **Interfaces before implementation**: `app/services/analysis_service.py` (the only caller) depends solely on these abstract base classes. A concrete provider — whatever it ends up being — is added as a new class implementing the interface and wired in by a factory; `api/` and `services/` code does not change. This is the direct mechanism for "the AI provider should be replaceable."
- **Splitting extraction from generation from validation** (`ClinicalInformationExtractor` → `ClinicalReportGenerator` → `StructuredOutputValidator`) rather than one monolithic "call the model" interface: it lets a future implementation use different strategies per stage (e.g. a fast entity-extraction pass followed by a slower report-synthesis pass) without forcing that choice at the interface level, and — critically — it makes `StructuredOutputValidator` a mandatory, separate stage that every generator's output passes through, rather than trusting whatever a provider claims its "JSON mode" guarantees.
- **`ml/` is kept independent of FastAPI/SQLAlchemy** (see `ml/README.md`) so the AI/ML pipeline can be developed, tested, and evaluated (`ml/evaluators/`) without spinning up the web app, and so it could in principle be reused outside this API.
- **The report contract enforces its own honesty** (`backend/app/schemas/clinical_report.py`, detailed in the architecture doc §7): every finding must be `HIGH` confidence and evidence-backed, or explicitly marked `inferred`/lower-confidence, and `requires_review` cannot be falsely cleared. This is deliberately placed in the shared schema (used by both `StructuredOutputValidator` and the API response), not left as a UI-only convention, so no implementation of any interface can bypass it.

## Alternatives Considered

- **A single `ClinicalAnalyzer.analyze(text) -> ClinicalReport` interface** — simpler, but collapses extraction/generation/validation into one opaque call, making it harder to swap only one stage (e.g. keep a extraction approach but change the report-writing model) and removing the enforced validation gate as a separable concern.
- **LangChain/LlamaIndex-style framework dependency** — rejected for this phase to avoid coupling the interface design to one framework's abstractions before there's a concrete provider decision to make; the plain-ABC approach costs nothing to change later if a framework proves useful inside a specific `ml/pipeline/` implementation.
- **Hard-coding a specific provider now** "to make progress faster" — explicitly rejected per the assignment's requirement; the interface-first approach is the direct response to that requirement, not a hedge.

## Trade-offs

- Nothing in the AI/ML pipeline actually runs yet — `AnalysisService.run_pipeline` raises `NotImplementedError` by design. This is intentional scope for this phase (architecture/contracts only), not an oversight.
- Interface-first design means the eventual implementation must be reconciled against these contracts rather than the contracts being derived from a working implementation; the risk is mitigated by having concrete, tested schemas (`ClinicalReport`, `NormalizedDocument`, `ClinicalExtractionResult`) rather than speculative method signatures alone.
