# ML Layer

**Status update (AI/ML pipeline foundation phase):** the real AI/ML pipeline contracts and orchestration — `AIProvider`, `ClinicalReportValidator`, `ClinicalAnalysisPipeline`, the deterministic validator, and the placeholder provider — were built in `backend/app/ai/`, **not** here, for a concrete reason: this directory is a sibling of `backend/`, not a Python package on the backend's import path, and it's outside the backend Docker image's build context (`docker-compose.yml` scopes the build to `./backend`). Making `import ml...` work from the running backend would require either packaging `ml/` as a proper `pip install -e`-able dependency or widening the Docker build context to the repo root — both real infrastructure changes, not "AI/ML contracts" work. See [`docs/decisions/008-ai-pipeline.md`](../docs/decisions/008-ai-pipeline.md) "Design Decisions That Need Review" #3 for the full reasoning.

This directory remains reserved for what it was always meant to hold once a **real** LLM provider is added: prompt templates and provider-SDK-specific implementation code that `backend/app/ai`'s `AIProvider` interface would then be implemented against — kept out of the backend package specifically so it can be developed/evaluated independently of the web app, per the design goal below. Until that happens, treat `backend/app/ai/interfaces.py` and `backend/app/ai/schemas.py` as the authoritative contracts, not anything here.

Design goal: the underlying model/provider (LLM or otherwise) must be swappable without changes to the API layer or document processing pipeline. This still holds — `backend/app/ai/factory.py::get_default_ai_provider()` is the one place that would need a new branch to select a real provider implementation (wherever it ends up living), and nothing above the factory would change.

## Structure

- `prompts/` — where prompt templates for a real provider's extraction/generation calls will live once one exists (see `prompts/README.md`)
- `schemas/` — reserved; the actual schemas in use today (`ExtractionResult`, `ClinicalFact`, `ValidationResult`, etc.) live in `backend/app/ai/schemas.py` for the import/Docker reasons above
- `pipeline/` — reserved; the actual orchestrator (`ClinicalAnalysisPipeline`) lives in `backend/app/ai/pipeline.py`
- `evaluators/` — reserved; the actual deterministic validator lives in `backend/app/ai/validators/deterministic.py`

No pipeline or provider implementation exists in this directory — this remains a structural placeholder, now with a documented reason rather than just "not built yet."
