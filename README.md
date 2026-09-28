# AI Clinical Document Reviewer

An end-to-end AI/ML application that ingests clinical documentation (plain text, images, or PDFs — typed, scanned, or handwritten), extracts relevant clinical information, runs AI/ML-based clinical analysis, and produces a structured clinical report.

> **Status:** Backend architecture, persistence, document processing (plain text, PDF text extraction, OCR via local Tesseract), and the AI/ML pipeline (EXTRACT → GENERATE → VALIDATE) are implemented and tested — including a real `AIProvider` (`OpenAICompatibleProvider`) callable via `POST /api/v1/analyses`, configured entirely by environment variables (`AI_PROVIDER=openai`, `AI_MODEL_NAME`, `AI_API_KEY`, optional `AI_API_BASE_URL`). Without a configured key, requests fail cleanly rather than fabricating a report. No background job queue exists yet, so the endpoint blocks synchronously on processing. See [Current Project Status](#current-project-status) and [Roadmap](#roadmap).

> **Note:** All clinical data used in this project (`synthetic-data/`) is synthetic. No real patient data is used at any stage.

## Overview

- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **Backend:** Python + FastAPI + Pydantic + SQLAlchemy + Alembic + PostgreSQL
- **AI/ML:** Modular, provider-agnostic layer (LLM/model provider is swappable, not hard-coded)
- **Infrastructure:** Docker + Docker Compose locally; AWS for public deployment (planned)

## Planned Architecture

```
User → React frontend → FastAPI backend → document processing (OCR/text extraction)
     → AI/ML pipeline → structured clinical report → PostgreSQL persistence
```

Full detail, including backend module responsibilities, the versioned REST API contract, the processing-status state machine, database schema, AI/ML interfaces, the structured report contract, and the error-response format, is in **[`docs/architecture/system-architecture.md`](docs/architecture/system-architecture.md)**, with a component diagram at [`docs/architecture/architecture-diagram.mmd`](docs/architecture/architecture-diagram.mmd).

Why each major technology/design choice was made is recorded in [`docs/decisions/`](docs/decisions) (ADRs 001–008: frontend, backend, database, AI/ML, storage, deployment, OCR, AI pipeline).

## Repository Structure

```
ai-clinical-document-reviewer/
├── frontend/              React + TypeScript + Vite + Tailwind CSS client
├── backend/
│   ├── app/
│   │   ├── api/v1/            REST routes (analyses, health)
│   │   ├── core/               config, error taxonomy, DB session, enums
│   │   ├── models/              SQLAlchemy models (documents, analyses, clinical_reports, processing_events)
│   │   ├── schemas/             Pydantic contracts (requests/responses, ClinicalReport)
│   │   ├── services/            use-case orchestration (AnalysisService)
│   │   ├── repositories/        SQLAlchemy persistence per model
│   │   ├── document_processing/ DocumentProcessor: TextProcessor, PDFProcessor, ImageProcessor + OCREngine (Tesseract)
│   │   └── ai/                  AIProvider + ClinicalReportValidator interfaces, ClinicalAnalysisPipeline, deterministic validator, placeholder provider
│   ├── migrations/          Alembic migrations (initial schema: 0001)
│   └── tests/               Pytest unit/API tests
├── ml/                    Reserved for a real LLM provider's prompts/implementation once one exists — see ml/README.md; contracts live in backend/app/ai/ for now
├── infrastructure/        Docker / AWS infrastructure definitions (AWS not yet implemented)
├── docs/
│   ├── architecture/          system-architecture.md, architecture-diagram.mmd
│   ├── decisions/              ADRs 001-006
│   └── testing/                 test strategy
├── synthetic-data/        Synthetic sample clinical documents (text/images/pdf)
├── tests/                 Cross-cutting integration (planned) and end-to-end (planned) tests
└── .github/workflows/     CI (backend tests, frontend build)
```

## Branching Strategy

```
feature/*  →  dev  →  staging  →  main
```

- `main` — production-ready code, deployable
- `staging` — pre-production integration/validation
- `dev` — active integration branch for feature work
- `feature/*` — individual feature branches, merged into `dev`

Each branch corresponds to an eventual deployment environment (see [`docs/decisions/006-deployment.md`](docs/decisions/006-deployment.md)); no AWS environment exists yet.

## Development Workflow

1. Branch from `dev` as `feature/<short-description>`.
2. Open a PR back into `dev`; CI (`.github/workflows/ci.yml`) runs backend tests and a frontend build on every push/PR to `main`/`staging`/`dev`.
3. `dev` is periodically merged into `staging` for pre-production validation, then `staging` into `main`.
4. Do not commit directly to `staging` or `main`.

## Local Development Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (for running PostgreSQL, and eventually the full stack)

### Backend

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate   # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp ../.env.example ../.env   # then adjust DATABASE_URL etc. as needed
alembic upgrade head          # requires a running PostgreSQL (see docker-compose.yml)
uvicorn app.main:app --reload
pytest                        # runs against an in-memory SQLite DB, no Postgres or OCR binary required
```

> **OCR note:** `pytest` never requires a real OCR engine (see `docs/testing/README.md`). To exercise real OCR, use `docker compose up --build` — the backend image installs `tesseract-ocr` automatically (see `docs/decisions/007-ocr.md`). Running the backend natively on Windows with real OCR requires installing Tesseract separately (e.g. the UB-Mannheim installer or `choco install tesseract`) and ensuring it's on `PATH`.

### Frontend

```bash
cd frontend
npm install
npm run dev
npm run build   # type-checks (tsc -b) then builds
```

### Full stack (once implemented end-to-end)

```bash
cp .env.example .env
docker compose up --build
```

## Documentation

| Topic | Location |
|---|---|
| System architecture, API contract, DB schema, error format | [`docs/architecture/system-architecture.md`](docs/architecture/system-architecture.md) |
| Architecture diagram | [`docs/architecture/architecture-diagram.mmd`](docs/architecture/architecture-diagram.mmd) |
| Technical decisions (ADRs) | [`docs/decisions/`](docs/decisions) |
| Testing strategy | [`docs/testing/`](docs/testing) |
| Deployment URLs | *to be added after AWS deployment* |
| Screenshots / examples | [`docs/screenshots/`](docs/screenshots) *(none yet — no UI exists)* |
| Limitations | *to be added once the AI/ML pipeline exists — premature to document limitations of unbuilt behavior* |

## Current Project Status

**Implemented:**
- Backend layering (`api → services → repositories/document_processing/ai → models`), documented module ownership boundaries
- Versioned REST API (`/api/v1/analyses`: create, list, get, get report) with full request/response/error contracts, backed by real persistence, validated end-to-end against a real PostgreSQL container (not just SQLite)
- PostgreSQL schema (4 tables) as SQLAlchemy models + an Alembic migration (runs on container startup, idempotent, blocks server start on failure), portable to SQLite for fast tests
- Processing lifecycle state machine (`PENDING → VALIDATING → EXTRACTING → ANALYZING → COMPLETED/FAILED`) defined with an explicit transition table
- **Document processing, including OCR**: `DocumentProcessor` interface with `TextProcessor` (plain text, Unicode-safe, whitespace normalization), `PDFProcessor` (native-text-layer extraction via `pypdf`, per-page OCR fallback for pages with no native text, preserving page order), and `ImageProcessor` (validates the image, delegates to OCR). OCR is local and offline — Tesseract via `pytesseract`, no external service, no data leaves the machine (see `docs/decisions/007-ocr.md`) — behind a swappable `OCREngine` interface. Confidence is a real, engine-reported signal bucketed into the existing qualitative model, not invented; handwriting limitations are explicitly disclosed, never silently assumed away. Scanned-PDF OCR covers the dominant real-world case (embedded page images, with page-rotation correction) but is **not** a general PDF-rendering engine — see "Scanned-PDF support" in `system-architecture.md` §8 and the Limitations section of `docs/decisions/007-ocr.md` for exactly what is and isn't covered.
- **AI/ML pipeline, with a real provider**: an explicit EXTRACT → GENERATE → VALIDATE pipeline (`app/ai/pipeline.py::ClinicalAnalysisPipeline`). `AIProvider` has two implementations: `UnconfiguredAIProvider` (the default — raises clearly rather than fabricating output) and `OpenAICompatibleProvider`, a real implementation calling any OpenAI-compatible `/chat/completions` endpoint via plain `httpx` (no SDK, no hard-coded vendor). Configure with `AI_PROVIDER=openai`, `AI_MODEL_NAME`, `AI_API_KEY`, optional `AI_API_BASE_URL` (see `.env.example`) — no credentials in code, and a missing key fails fast and cleanly rather than attempting a call. Validation remains a completely separate, deterministic (non-LLM) gate: every claim's evidence must be a verbatim quote from the source document, confidence can't be inflated beyond what was extracted, and a report can never be marked as not-needing-review while anything is uncertain — see `docs/decisions/008-ai-pipeline.md`.
- **`POST /api/v1/analyses` now runs the full pipeline synchronously** — `AnalysisService.run_pipeline()` is called right after the document is persisted, and the response reflects the real final status (`COMPLETED` with a persisted report, or `FAILED` with a clear error code — e.g. `AI_EXTRACTION_FAILED` if no provider is configured, `DOCUMENT_BYTES_UNAVAILABLE` for PDF/IMAGE, whose raw bytes aren't persisted yet — see `docs/decisions/005-storage.md`) instead of always `PENDING`. There is still no background job queue, so the request blocks on document processing + the AI call — see `docs/decisions/008-ai-pipeline.md` "What Async Will Need".
- The structured `ClinicalReport` Pydantic contract, with enforced evidence/confidence/`requires_review` rules, mirrored in TypeScript
- Consistent error-response envelope across the API
- Docker Compose (frontend/backend/db), Dockerfiles (backend now installs `tesseract-ocr`), lightweight CI (backend tests + frontend build)
- 102 passing backend tests (API validation paths, report schema rules, document-processing/OCR, AI pipeline/validator, real-provider request/response/error handling, and full API-level pipeline integration — all deterministic; the real provider's tests mock the HTTP boundary, so no test requires an API key, network, or external LLM)

**Not yet implemented (planned):**
- Async execution of `run_pipeline()` (background worker/job queue) — currently synchronous inside the `POST` request
- Object storage writes (uploaded file bytes are validated but not yet persisted to disk/S3) — the reason PDF/IMAGE analyses can't currently be (re-)processed
- Frontend UI (only TypeScript API/report types exist)
- Authentication
- AWS deployment
- Integration (`tests/integration/`) and end-to-end (`tests/e2e/`) tests

## Roadmap

- [x] Project & repository foundation
- [x] System architecture & engineering contracts (backend skeleton, API contract, DB schema, AI/ML interfaces, error architecture)
- [x] Docker/PostgreSQL development environment validated end-to-end
- [x] Document-processing foundation: plain text + PDF text extraction, normalized representation, unit tests
- [x] OCR: images and scanned/mixed PDFs, via local Tesseract behind a swappable `OCREngine` interface
- [x] AI/ML pipeline architecture: EXTRACT→GENERATE→VALIDATE, provider abstraction, deterministic evidence-grounded validation
- [x] Real `AIProvider` (`OpenAICompatibleProvider`) wired into `AnalysisService.run_pipeline()`, called synchronously from `POST /api/v1/analyses`
- [ ] Async execution of `run_pipeline()` (background worker/job queue) triggered from the API
- [ ] Object storage (unblocks re-processing PDF/IMAGE analyses)
- [ ] Frontend application
- [ ] Integration & end-to-end tests
- [ ] AWS deployment
- [ ] Full documentation pass (screenshots, limitations, deployment URLs)

## License

MIT — see [LICENSE](LICENSE).
