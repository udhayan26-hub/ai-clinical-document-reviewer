# AI Clinical Document Reviewer

An end-to-end AI/ML application that ingests clinical documentation (plain text, images, or PDFs — typed, scanned, or handwritten), extracts relevant clinical information, runs AI/ML-based clinical analysis, and produces a structured clinical report.

> **Status:** Project foundation only. Application logic, AI pipeline, document processing, authentication, and deployment are not yet implemented. See [Roadmap](#roadmap) below.

> **Note:** All clinical data used in this project (`synthetic-data/`) is synthetic. No real patient data is used at any stage.

## Overview

- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **Backend:** Python + FastAPI + Pydantic + SQLAlchemy + Alembic + PostgreSQL
- **AI/ML:** Modular, provider-agnostic layer (LLM/model provider is swappable, not hard-coded)
- **Infrastructure:** Docker + Docker Compose locally; AWS for public deployment (planned)

## Repository Structure

```
ai-clinical-document-reviewer/
├── frontend/              React + TypeScript + Vite + Tailwind CSS client
├── backend/               FastAPI backend (API, services, persistence)
├── ml/                    AI/ML pipeline, prompts, schemas, evaluators
├── infrastructure/        Docker / AWS infrastructure definitions
├── docs/                  Architecture, decisions, testing documentation
├── synthetic-data/        Synthetic sample clinical documents (text/images/pdf)
├── tests/                 Cross-cutting integration and end-to-end tests
└── .github/workflows/     CI/CD pipelines
```

See [`docs/architecture/`](docs/architecture) for diagrams and [`docs/decisions/`](docs/decisions) for technical decision records.

## Branching Strategy

```
feature/*  →  dev  →  staging  →  main
```

- `main` — production-ready code, deployable
- `staging` — pre-production integration/validation
- `dev` — active integration branch for feature work
- `feature/*` — individual feature branches, merged into `dev`

## Getting Started

Setup instructions will be added once the backend and frontend applications are implemented. Planned local development flow:

```bash
cp .env.example .env
docker compose up --build
```

## Documentation

| Topic | Location |
|---|---|
| Architecture diagram | `docs/architecture/` |
| AI/ML design | `docs/architecture/ai-ml-design.md` (planned) |
| Technical decisions | `docs/decisions/` |
| Testing strategy | `docs/testing/` |
| Deployment URLs | *to be added after AWS deployment* |
| Screenshots / examples | `docs/screenshots/` |
| Limitations | *to be added* |

## Roadmap

- [x] Project & repository foundation
- [ ] Backend API skeleton (FastAPI, DB models, migrations)
- [ ] Document ingestion & validation (text / image / PDF)
- [ ] Document processing (OCR / handwriting extraction)
- [ ] AI/ML clinical analysis pipeline
- [ ] Structured report generation & persistence
- [ ] Frontend application
- [ ] Testing (unit, integration, e2e)
- [ ] AWS deployment
- [ ] Full documentation pass

## License

MIT — see [LICENSE](LICENSE).
