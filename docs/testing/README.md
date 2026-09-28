# Testing Documentation

## Current state

- **Backend unit/API tests** (`backend/tests/`, Pytest, 32 tests): run against an in-memory SQLite database created fresh per test (`backend/tests/conftest.py`), with FastAPI's `get_db` dependency overridden — no external services required. Covers:
  - `test_health.py` — liveness endpoint
  - `test_analyses_api.py` — `POST/GET /api/v1/analyses` and `GET /api/v1/analyses/{id}/report` validation, status codes, and error envelope
  - `test_clinical_report_schema.py` — the `ClinicalReport` Pydantic contract's evidence/`requires_review` enforcement rules
  - `document_processing/test_text_processor.py`, `test_pdf_processor.py`, `test_factory.py` — `TextProcessor`/`PDFProcessor` against synthetic fixtures (`tests/fixtures/documents/`: valid/multi-page/no-text/mixed/empty/corrupted PDFs), processor selection, and the `ImageProcessor` stub's explicit not-implemented error. No AI/OCR service involved — fully deterministic, local, offline.
- **Manual Docker/PostgreSQL validation** (not automated in CI yet): full `docker compose up --build` stack — Postgres health, Alembic migration on startup (and its idempotency and fail-closed behavior), the same `/api/v1/analyses` endpoints against the real container, and data survival across backend restarts/recreation.
- **CI** (`.github/workflows/ci.yml`): installs backend deps and runs `pytest`; installs frontend deps and runs `npm run build` (which also runs `tsc -b` type-checking). Lightweight by design — no Postgres service container, no deployment steps.

This is possible because the SQLAlchemy models use portable types (`sa.Uuid`, `JSON.with_variant(JSONB, "postgresql")`, non-native `Enum`) — see `docs/decisions/003-database.md`. Anything genuinely PostgreSQL-specific belongs in `tests/integration/`, not here.

## Planned

- `tests/integration/` — tests run against a real PostgreSQL instance (e.g. via `docker-compose`), covering migration correctness and any Postgres-specific behavior (JSONB querying, etc.) not exercised by the SQLite-backed unit tests.
- Frontend component tests (Vitest is already a dev dependency; no components exist yet to test).
- `tests/e2e/` — full frontend+backend flow, once both exist.
- Tests for OCR (`ImageProcessor`, and `PDFProcessor`'s scanned-page fallback) and `ai/` implementations, once they exist.
