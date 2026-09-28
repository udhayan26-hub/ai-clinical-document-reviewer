# Prompts

Reserved for the prompt templates a **real** `AIProvider` implementation will use for the EXTRACT and GENERATE stages (see `backend/app/ai/interfaces.py`). Deliberately empty of any actual prompt text right now — writing a production prompt before there is a provider to run it against would be premature, and this phase's job was the surrounding contracts (`backend/app/ai/schemas.py`), not prompt engineering.

Expected shape once a provider exists (not yet built):

- `extract.md` (or `.txt`/`.jinja`) — instructs the model to produce a `backend.app.ai.schemas.ExtractionResult`-shaped JSON payload: one entry per clinical fact, each with a `category` (see `ClinicalFactCategory`), a `value`, and evidence quoted verbatim from the source document.
- `generate.md` — instructs the model to turn an `ExtractionResult` into a `backend.app.ai.schemas`-adjacent draft matching `app.schemas.clinical_report.ClinicalReport`'s shape, making clear that every non-inferred finding must cite evidence and that uncertain/inferred content must be marked as such — the same rules `DeterministicClinicalReportValidator` will check afterward, not optional guidance.

Neither prompt is expected to be trusted on its own — `ClinicalReportValidator` (deterministic, not part of this directory) is the actual gate, regardless of how well either prompt is written.
