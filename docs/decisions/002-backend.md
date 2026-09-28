# 002. Backend stack: FastAPI + Pydantic + SQLAlchemy + Alembic

## Problem

The backend must handle uploads (text/image/PDF), validate them, run them through document processing and an AI/ML pipeline, persist structured results, expose a versioned REST API, and return consistent errors — while keeping business logic decoupled from any specific AI provider.

## Decision

Python with FastAPI for the API layer, Pydantic for request/response/report schemas, SQLAlchemy (2.0-style declarative models) for persistence, Alembic for migrations. Layered as `api/ → services/ → (repositories/ + document_processing/ + ai/) → models/`, per `docs/architecture/system-architecture.md` §2.

## Rationale

- **FastAPI** generates OpenAPI docs directly from the same Pydantic models used for validation, gives async support if a future provider call needs it, and its dependency-injection system (`Depends`) is what makes `AnalysisService` injectable and swappable in tests (see `backend/tests/conftest.py` overriding `get_db`).
- **Pydantic** is the single place the `ClinicalReport` contract is defined and enforced (`backend/app/schemas/clinical_report.py`) — the same model validates AI output, shapes the API response, and (via `model_dump()`) is what gets stored in `clinical_reports.structured_data`. One definition, not three.
- **SQLAlchemy 2.0 declarative models + Alembic** were chosen over a lighter query builder because the domain has real relational structure (documents/analyses/reports/events with FKs and cascade rules) worth expressing as an ORM, and because Alembic gives an auditable, reviewable migration history rather than ad-hoc `CREATE TABLE` scripts.
- **Layering** (see §2 of the architecture doc) exists so that `app/ai` and `app/document_processing` can be implemented, tested, and swapped without touching `app/api` — the explicit goal from the assignment that the AI provider be replaceable.

## Alternatives Considered

- **Flask / Django** — Flask lacks built-in request/response validation and OpenAPI generation (would mean hand-writing what Pydantic+FastAPI give for free); Django's batteries (admin, ORM conventions, templating) are aimed at a different kind of app and its ORM is harder to decouple from the web layer the way this project's layering requires.
- **Raw `psycopg2`/SQL** instead of an ORM — would remove SQLAlchemy's abstraction but at the cost of hand-writing and hand-migrating schema DDL, with no gain given the schema's actual complexity (four related tables, JSONB, enum-backed status).
- **A task queue (Celery/RQ) for pipeline execution** — deliberately deferred. `AnalysisService.run_pipeline` is the documented seam for it, but introducing a broker before there's an actual pipeline to run would be speculative infrastructure.

## Trade-offs

- FastAPI + Pydantic + SQLAlchemy is more moving parts than a minimal script, but the assignment explicitly asks for a production-shaped, layered application, not a notebook.
- SQLAlchemy's ORM has a learning curve (session lifecycle, lazy loading) that a raw query builder wouldn't; mitigated by centralizing session handling in `app/core/database.py` and keeping repositories thin.
- **Known follow-up**: `frontend/src/types/*.ts` are hand-mirrored from the Pydantic schemas rather than generated (e.g. via `openapi-typescript`). Acceptable at this project's current size; worth automating once the API stabilizes, so the two can't silently drift.
