# AI Clinical Document Reviewer

An end-to-end AI/ML application that ingests clinical documentation (plain text, images, or PDFs — typed, scanned, or handwritten), extracts relevant clinical information, runs AI/ML-based clinical analysis, and produces a structured clinical report.

> **Status:** System architecture and engineering contracts are defined and implemented at the skeleton level (models, migrations, API routing, schemas, error handling, interfaces). Actual document processing (OCR/extraction) and the AI/ML pipeline are **not yet implemented** — see [Current Project Status](#current-project-status) and [Roadmap](#roadmap).

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

Why each major technology/design choice was made is recorded in [`docs/decisions/`](docs/decisions) (ADRs 001–006: frontend, backend, database, AI/ML, storage, deployment).

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
│   │   ├── document_processing/ DocumentTextExtractor / OCRProcessor interfaces
│   │   └── ai/                  ClinicalInformationExtractor / ClinicalReportGenerator / StructuredOutputValidator interfaces
│   ├── migrations/          Alembic migrations (initial schema: 0001)
│   └── tests/               Pytest unit/API tests
├── ml/                    AI/ML pipeline implementations (prompts, schemas, pipeline, evaluators) — not yet implemented, see app/ai for interfaces
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
pytest                        # runs against an in-memory SQLite DB, no Postgres required
```

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

**Implemented (this phase — architecture & engineering contracts):**
- Backend layering (`api → services → repositories/document_processing/ai → models`), documented module ownership boundaries
- Versioned REST API (`/api/v1/analyses`: create, list, get, get report) with full request/response/error contracts, backed by real persistence
- PostgreSQL schema (4 tables) as SQLAlchemy models + an Alembic migration, portable to SQLite for fast tests
- Processing lifecycle state machine (`PENDING → VALIDATING → EXTRACTING → ANALYZING → COMPLETED/FAILED`) defined with an explicit transition table
- AI/ML and document-processing interfaces (no implementations) — provider-agnostic by construction
- The structured `ClinicalReport` Pydantic contract, with enforced evidence/confidence/`requires_review` rules, mirrored in TypeScript
- Consistent error-response envelope across the API
- Docker Compose (frontend/backend/db), Dockerfiles, lightweight CI (backend tests + frontend build)
- 15 passing backend tests (API validation paths + report schema rules)

**Not yet implemented (planned):**
- Actual text extraction / OCR (`document_processing` implementations)
- Actual AI/ML clinical analysis (`ai`/`ml` implementations, provider selection)
- Object storage writes (uploaded file bytes are validated but not yet persisted to disk/S3)
- Pipeline execution (`AnalysisService.run_pipeline` is an intentional `NotImplementedError`)
- Frontend UI (only TypeScript API/report types exist)
- Authentication
- AWS deployment
- Integration (`tests/integration/`) and end-to-end (`tests/e2e/`) tests

## Roadmap

- [x] Project & repository foundation
- [x] System architecture & engineering contracts (backend skeleton, API contract, DB schema, AI/ML interfaces, error architecture)
- [ ] Document ingestion & validation implementation (text / image / PDF extraction, OCR)
- [ ] AI/ML clinical analysis pipeline implementation
- [ ] Structured report generation wired end-to-end (pipeline execution)
- [ ] Frontend application
- [ ] Integration & end-to-end tests
- [ ] AWS deployment
- [ ] Full documentation pass (screenshots, limitations, deployment URLs)

## License

MIT — see [LICENSE](LICENSE).
