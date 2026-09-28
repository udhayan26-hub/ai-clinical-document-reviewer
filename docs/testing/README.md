# Testing Documentation

## Current state

- **Backend unit/API tests** (`backend/tests/`, Pytest, 62 tests): run against an in-memory SQLite database created fresh per test (`backend/tests/conftest.py`), with FastAPI's `get_db` dependency overridden — no external services required. Covers:
  - `test_health.py` — liveness endpoint
  - `test_analyses_api.py` — `POST/GET /api/v1/analyses` and `GET /api/v1/analyses/{id}/report` validation, status codes, and error envelope
  - `test_clinical_report_schema.py` — the `ClinicalReport` Pydantic contract's evidence/`requires_review` enforcement rules
  - `document_processing/test_text_processor.py` — `TextProcessor` against synthetic text (Unicode, whitespace normalization, invalid UTF-8)
  - `document_processing/test_pdf_processor.py` — `PDFProcessor` against synthetic fixtures (`tests/fixtures/documents/`: valid/multi-page/no-text/mixed/empty/corrupted, plus `scanned.pdf`/`mixed_native_and_scanned.pdf`/`rotated_scanned.pdf`/`multi_page_scanned.pdf` for OCR fallback), asserting native-text pages never invoke OCR, scanned pages do, page order is preserved when combining native+OCR text, a per-page OCR failure degrades to a warning rather than aborting the document, a page-level `/Rotate` value is corrected (image dimensions swapped) before the bytes reach the OCR engine, and — critically — a document with one page recovered via OCR and one page whose OCR failed reports `MEDIUM` (not `HIGH`) confidence with an `OCR_FAILED` warning, so partial extraction never reads as a fully reliable one
  - `document_processing/test_image_processor.py` — `ImageProcessor` against synthetic fixtures (`tests/fixtures/images/`: clear printed, low-quality, corrupted, unsupported-format), asserting it delegates to the injected `OCREngine`, propagates OCR failures as `OCRFailedError`, and preserves engine-reported warnings
  - `document_processing/test_ocr_tesseract.py` — the real `TesseractOCREngine`'s pure logic (confidence bucketing, line reconstruction, warning decisions) against synthetic `pytesseract`-shaped data, plus one real (non-faked) call proving corrupted image bytes raise `OCRFailedError` *before* the Tesseract binary would ever be invoked — deterministic regardless of whether Tesseract is installed on the test machine
  - `document_processing/test_factory.py` — processor selection (construction only, never `.process()` — see below) and the unsupported-source-type error path
  - `document_processing/fakes.py` — `FakeOCREngine`, a configurable `OCREngine` test double (fixed result / sequence of results / raises an exception) used by every OCR-touching processor test **instead of** the real engine
- **Manual Docker/PostgreSQL validation** (not automated in CI yet): full `docker compose up --build` stack — Postgres health, Alembic migration on startup (and its idempotency and fail-closed behavior), the same `/api/v1/analyses` endpoints against the real container, data survival across backend restarts/recreation, and the real `TesseractOCREngine` exercised inside the Linux container where `tesseract-ocr` is actually installed — including the specific empirical test that determined the page-rotation correction direction (`docs/decisions/007-ocr.md`, "Limitations (Scanned PDF)") — this could only be validated against the real engine, not the fake one used in `pytest`.
- **CI** (`.github/workflows/ci.yml`): installs backend deps and runs `pytest`; installs frontend deps and runs `npm run build` (which also runs `tsc -b` type-checking). Lightweight by design — no Postgres service container, no OCR binary, no deployment steps. This works because no automated test calls a real `OCREngine` with input that would actually reach the Tesseract binary (see `test_ocr_tesseract.py`'s docstring) — `pytest` passes identically whether or not Tesseract is installed on the machine running it.

This is possible because the SQLAlchemy models use portable types (`sa.Uuid`, `JSON.with_variant(JSONB, "postgresql")`, non-native `Enum`) — see `docs/decisions/003-database.md`. Anything genuinely PostgreSQL-specific belongs in `tests/integration/`, not here.

## Planned

- `tests/integration/` — tests run against a real PostgreSQL instance (e.g. via `docker-compose`), covering migration correctness and any Postgres-specific behavior (JSONB querying, etc.) not exercised by the SQLite-backed unit tests.
- Frontend component tests (Vitest is already a dev dependency; no components exist yet to test).
- `tests/e2e/` — full frontend+backend flow, once both exist.
- Tests for `ai/` implementations, once they exist.
