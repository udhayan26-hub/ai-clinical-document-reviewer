# Technical Decisions

Architecture Decision Records (ADRs), one per major technical choice. Format: Problem, Decision, Rationale, Alternatives Considered, Trade-offs.

- [001-frontend.md](001-frontend.md) — React + TypeScript + Vite + Tailwind CSS
- [002-backend.md](002-backend.md) — FastAPI + Pydantic + SQLAlchemy + Alembic
- [003-database.md](003-database.md) — PostgreSQL schema design (UUID keys, JSONB, portable enums)
- [004-ai-ml.md](004-ai-ml.md) — Provider-agnostic AI/ML interface design
- [005-storage.md](005-storage.md) — Object storage strategy for uploaded documents
- [006-deployment.md](006-deployment.md) — Docker-first local development, AWS deployment deferred
- [007-ocr.md](007-ocr.md) — OCR engine selection (Tesseract), alternatives, handwriting/confidence handling
