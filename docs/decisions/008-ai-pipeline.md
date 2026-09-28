# 008. AI/ML pipeline: EXTRACT → GENERATE → VALIDATE, with deterministic, provider-independent validation

## Problem

Turn a `NormalizedDocument` into a trustworthy `ClinicalReport` using an LLM, without: hard-coding a vendor, letting the LLM grade its own homework, or allowing an unsupported/fabricated claim to reach a client looking like fact.

## Decision

Three explicit, separated stages — `backend/app/ai/pipeline.py::ClinicalAnalysisPipeline.run()`:

```
NormalizedDocument → EXTRACT → ExtractionResult → GENERATE → draft report (dict)
                                                                    → VALIDATE → ValidationResult
```

- **EXTRACT** and **GENERATE** are the two methods of one `AIProvider` interface (`app/ai/interfaces.py`) — the only thing the pipeline depends on for LLM-backed work.
- **VALIDATE** is a **separate** interface, `ClinicalReportValidator`, with one deterministic implementation (`DeterministicClinicalReportValidator`, pure Python, no LLM call) — not a method on `AIProvider`.
- Only one `AIProvider` exists right now: `UnconfiguredAIProvider`, which cleanly raises rather than fabricating output — see "Provider Status" below.

## Design Decisions That Need Review

This phase made several judgment calls beyond what was fully specified; each is called out here rather than buried in code comments alone.

### 1. `AIProvider` consolidates the two earlier separate interfaces

The architecture-only phase (ADR-004) defined `ClinicalInformationExtractor` and `ClinicalReportGenerator` as two separate ABCs. This phase replaces both with a single `AIProvider(extract, generate)`. Rationale: a real provider implementation shares one client/credentials/model configuration across both calls, so splitting them into separately-implementable interfaces was artificial — no one would implement `extract` and `generate` with two different providers in practice. `StructuredOutputValidator` is similarly renamed/reshaped to `ClinicalReportValidator`, whose signature now takes the extraction and source text too (`validate(draft_report, extraction, source_text) -> ValidationResult`) — the earlier `validate(raw_output) -> ClinicalReport` signature had no way to check evidence grounding against anything, which is the majority of what this phase's validator actually does.

### 2. Validation is a separate interface from generation, on purpose

The prompt's own "AI PROVIDER ABSTRACTION" section lists `validate` as one of three pipeline operations "the abstraction" conceptually supports, while the "VALIDATION" section separately demands the validator be "independent of the LLM provider" and that the system must not "rely on the LLM to validate itself." These two framings are in tension if read as "put all three methods on one interface." This implementation resolves it by keeping `validate` off `AIProvider` entirely: `ClinicalReportValidator` is a distinct ABC with a single deterministic implementation, constructed independently of whichever `AIProvider` produced the draft. **Please confirm this reading is what was intended.**

### 3. Contracts and orchestration live in `backend/app/ai/`, not top-level `ml/`

The prompt asks to use the existing `ml/prompts/`, `ml/schemas/`, `ml/pipeline/`, `ml/evaluators/` structure "if it fits." It doesn't, for a concrete, checked reason: `ml/` is a sibling of `backend/`, not a Python package on `backend`'s import path, and the backend Docker image's build context is `./backend` (`docker-compose.yml`) — `ml/` is not even copied into the image today. Making `import ml...` work from `backend/app` would require either (a) turning `ml/` into a properly `pip install -e`-able package with its own `pyproject.toml`, or (b) widening the Docker build context to the repo root and updating `backend/Dockerfile`'s `COPY` paths — both real infrastructure changes to the already-validated Docker/Postgres/OCR setup from earlier phases, not "contracts" work. Given that risk, all real code (interfaces, schemas, the orchestrator, the placeholder provider, the deterministic validator) lives in `backend/app/ai/`, which is already correctly on the path and in the image. `ml/` remains a documented placeholder — see `ml/README.md` — for where a **real** provider implementation's prompt templates and provider-SDK code would live once one exists, at which point solving the packaging problem properly (option a or b above) becomes worth doing for real. **This is a deviation from the literal instruction and should be reviewed.**

### 4. "Draft report" is a plain `dict`, not a parallel Pydantic model

A `DraftClinicalReport` schema mirroring `ClinicalReport` but with relaxed validation was considered and rejected: it would duplicate most of `ClinicalReport`'s shape for no real benefit, since the entire point of the draft stage is that it *hasn't* been shown to satisfy the schema yet. `AIProvider.generate()` returns `dict[str, Any]`; `ClinicalReportValidator.validate()` attempts `ClinicalReport(**draft_report)` and reports every Pydantic error as a `SCHEMA_INVALID` issue rather than raising. This also directly satisfies "Pydantic/schema validity" as validation checklist item 1, for free.

### 5. `ExtractionResult`/`ClinicalFact` reuse `ClinicalReport`'s `EvidenceSpan`/`ConfidenceLevel`

Rather than defining an equivalent shape twice, `app/ai/schemas.py` imports `EvidenceSpan`/`ConfidenceLevel` directly from `app/schemas/clinical_report.py`. Precedent: `app/ai/interfaces.py` already imported `ClinicalReport` from the same module in the architecture-only phase, so this doesn't cross a new boundary, and duplicating a 2-field evidence model and a 3-value enum would be exactly the "unnecessary fields merely for completeness" the prompt asks to avoid.

### 6. `run_pipeline()` is wired for real, but not called by any endpoint

`AnalysisService.run_pipeline()` no longer raises `NotImplementedError` — it's a complete, real implementation: fetch the analysis, drive it through VALIDATING → EXTRACTING → ANALYZING → COMPLETED/FAILED, actually calling `ClinicalAnalysisPipeline` and persisting a `ClinicalReport` row on success. This *is* "integrating through the existing service boundary." What it deliberately does **not** do is get called automatically by `POST /api/v1/analyses` — doing so would make that request block on OCR and an AI provider call, and no background-job/async infrastructure exists to avoid that. See "What Async Will Need" below.

### 7. PDF/IMAGE analyses cannot currently be re-processed — an honest, pre-existing gap surfaced, not created, by this phase

`Document` rows never persisted raw file bytes for PDF/IMAGE uploads (`storage_uri` is always `None` — object storage writes were explicitly deferred in [005-storage.md](005-storage.md), across two prior phases). `run_pipeline()` can only actually reconstruct a `NormalizedDocument` for **TEXT** analyses today (from the already-stored `Analysis.extracted_text`). For PDF/IMAGE, it raises the new `DocumentBytesUnavailableError` (422) — the analysis ends up cleanly `FAILED` with a clear reason, never silently wrong and never a crash. Fixing this for real means implementing object storage, which remains out of scope here exactly as it was in the two prior phases.

## Extraction Contract & Evidence Grounding

`ClinicalFact` (`app/ai/schemas.py`): `category` (one of 12 categories — patient identifier, document metadata, observation, symptom, diagnosis, medication, allergy, investigation, lab result, vital sign, procedure, history — each traceable to an explicit item in the assignment's own list, nothing invented beyond it), `value` (plain text), `evidence` (`list[EvidenceSpan]`), `confidence`, `inferred`. A non-inferred fact **must** cite evidence — enforced by a Pydantic validator, identical in spirit to `ClinicalReport`'s own findings.

Evidence grounding is checked **twice**, with the same primitive (`app/ai/evidence_grounding.py::find_ungrounded_quotes`, a simple substring check): once on the raw extraction (pipeline stage "validate extraction structure," before spending a GENERATE call on possibly-hallucinated facts — raises `EvidenceMismatchError`), and again on every finding in the generated report (inside `DeterministicClinicalReportValidator`, as the `EVIDENCE_NOT_GROUNDED` issue code). A claim whose evidence quote does not appear verbatim in the source document is never trusted, at either stage.

## Deterministic Validation

`DeterministicClinicalReportValidator` (`app/ai/validators/deterministic.py`) never raises — always returns a `ValidationResult`, even for completely malformed input (any internal exception is caught and converted to a `SCHEMA_INVALID` issue). Checks performed, mapped to the assignment's checklist:

| # | Checklist item | How it's checked |
|---|---|---|
| 1, 2 | Pydantic/schema validity, required fields | `ClinicalReport(**draft_report)`; every `pydantic.ValidationError` becomes a `SCHEMA_INVALID` issue |
| 3, 5 | Evidence references / no evidence → unsupported claim | `ClinicalReport`'s own validator already forbids a non-inferred finding with no evidence (caught as `SCHEMA_INVALID`); this validator additionally requires every cited quote to be verbatim in the source text (`EVIDENCE_NOT_GROUNDED`) |
| 4 | Claims supported by extracted facts | Same grounding check — a claim's evidence must exist in the source document, which is the strongest verifiable proxy for "the extractor really found this" available without fragile fact-to-finding matching |
| 6 | Missing information represented | If `extraction.missing_information` is non-empty but `report.missing_information` is empty, `MISSING_INFORMATION_NOT_REPRESENTED` (WARNING — doesn't invalidate; the report may have represented the gap differently) |
| 7 | Inconsistency can be represented | `ClinicalReport.potential_inconsistencies` already exists as a first-class field (§7 of `system-architecture.md`) and round-trips through validation untouched — confirmed by test, not a separate check |
| 8 | Confidence/uncertainty preserved | If a finding's evidence matches an extracted fact's evidence and claims *higher* confidence than that fact had, `CONFIDENCE_NOT_PRESERVED` (WARNING) — an LLM must not inflate confidence beyond what was actually extracted |
| 9 | Report status | `ValidationResult.status` (`VALID`/`INVALID`) — the model's own reason for existing |

`ERROR`-severity issues (schema-invalid, ungrounded evidence) make the result `INVALID`, which the pipeline turns into `ReportValidationFailedError`. `WARNING`-severity issues (missing-information reconciliation, confidence inflation) are recorded but do not block a `VALID` result — they're visible in `ValidationResult.issues` for whoever persists/inspects the result.

## Uncertainty & Safety

This system is a document-review/triage aid, not an autonomous diagnostician — nothing here changes that framing. `ClinicalReport`'s existing, unmodified rule (`requires_review` cannot be `False` while anything is non-`HIGH`-confidence, inferred, or accompanied by missing information/inconsistencies — see `system-architecture.md` §7) is the mechanism that keeps a generated report from presenting itself as final, unreviewed truth; this phase's validator adds evidence-grounding and confidence-preservation on top, it doesn't relax that existing rule.

## FakeAIProvider Testing Strategy

`backend/tests/ai/fakes.py::FakeAIProvider` implements `AIProvider` with configurable canned results/exceptions per method, plus call recording — used by every pipeline and service test instead of a real LLM. `SpyingValidator` wraps the real deterministic validator to prove it was actually invoked (not skippable) without needing a second fake validator implementation. No test in this phase makes a network call or requires an API key — the *only* provider that exists, `UnconfiguredAIProvider`, is deliberately non-functional, so there is nothing to accidentally call for real.

## What Async Will Need (documented, not built)

`run_pipeline()` currently runs synchronously and is not invoked by any endpoint. Making an analysis actually process after `POST /api/v1/analyses` will need, at minimum: a way to trigger `run_pipeline()` out-of-request (a background task runner or job queue — e.g. FastAPI `BackgroundTasks` for a first cut, or a real queue for production), a decision on whether `GET /api/v1/analyses/{id}` polling is sufficient for the frontend or a push mechanism (webhook/SSE) is needed, and idempotency handling if a worker retries a partially-completed run. None of this is implemented or assumed here.

## Trade-offs

- No automated test exercises a real LLM end-to-end — by design (see "FakeAIProvider Testing Strategy"). There is currently no real `AIProvider` to test even if one wanted to.
- The confidence-preservation and missing-information checks rely on evidence-quote string matching between facts and findings, which is exact-substring, not fuzzy — a real provider that paraphrases evidence slightly differently between extraction and generation could produce a spurious `CONFIDENCE_NOT_PRESERVED` or miss a match entirely. Acceptable for now; revisit once a real provider's actual output shape is known.
- `ml/`'s four directories remain unused by real code this phase (see Design Decision 3) — this is intentional, not an oversight, but is a direct deviation from what was asked and should be confirmed.

## Real Provider (Step 2)

A real `AIProvider` now exists: `OpenAICompatibleProvider` (`backend/app/ai/providers/openai_compatible.py`) — a plain `httpx` call to any OpenAI-compatible `/chat/completions` endpoint (chosen over the `openai` SDK since one POST + one JSON body didn't justify a new dependency; `httpx` was already required). Configuration is entirely env-var-driven — `AI_PROVIDER=openai`, `AI_MODEL_NAME`, `AI_API_KEY`, optional `AI_API_BASE_URL` (defaults to `https://api.openai.com/v1`) — no credentials in code, and `ai/factory.py` raises `UnsupportedAIProviderError` immediately if `AI_API_KEY` is unset, rather than attempting a call. Extraction and generation each use a concise system prompt (in the same file) instructing the model to return JSON only, cite verbatim evidence quotes, and never fabricate a finding with no supporting fact — enforcement of those rules still happens where it always did, in `ExtractionResult`'s own Pydantic validator and `DeterministicClinicalReportValidator`, not in the provider or the prompt text.

**`POST /api/v1/analyses` now calls `AnalysisService.run_pipeline()` synchronously** (previously built but not wired to any endpoint) — the request blocks on document processing + the AI provider call, and the response reflects the final `COMPLETED`/`FAILED` status rather than always `PENDING`. `AnalysisService`'s provider/validator resolution moved from `__init__` to inside `run_pipeline()` so a misconfigured `AI_PROVIDER` only fails analysis processing, not unrelated `GET` endpoints. Tests use `FakeAIProvider` via the existing `ai_provider=` constructor override (now also exercised through `app.dependency_overrides` at the API layer, not just the service layer) — no test requires a network call or API key; `OpenAICompatibleProvider`'s own tests mock the HTTP boundary with `httpx.MockTransport`.
