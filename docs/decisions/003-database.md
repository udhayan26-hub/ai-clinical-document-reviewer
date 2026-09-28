# 003. Database: PostgreSQL, with UUID keys, JSONB report storage, and portable enum/JSON types

## Problem

Persist documents, analyses (with lifecycle status), structured clinical reports, and an audit trail of processing events, in a schema that's queryable (filter by status, list history) but flexible enough for a report shape that will keep evolving as the AI pipeline is built out.

## Decision

PostgreSQL, modeled via four tables (`documents`, `analyses`, `clinical_reports`, `processing_events`) as detailed in `docs/architecture/system-architecture.md` §5. Key choices:

- UUID primary keys everywhere (`sa.Uuid`, client-generated via `default=uuid.uuid4`), not auto-incrementing integers.
- `clinical_reports.structured_data` and `processing_events.event_metadata` are JSONB, via `sa.JSON().with_variant(postgresql.JSONB(), "postgresql")`.
- Status/type enums (`AnalysisStatus`, `DocumentSourceType`, `ProcessingEventType`) are stored as `VARCHAR` with `native_enum=False`, not native Postgres `ENUM` types.

## Rationale

- **PostgreSQL** was specified as the required database; it also natively supports JSONB, which the report-storage design leans on.
- **UUID PKs**: ids are safe to generate application-side before a row is committed (useful for e.g. returning an id in the same response that creates it), and they sidestep a real portability bug encountered while building this schema — SQLAlchemy's `BigInteger` autoincrement PK does not get SQLite's special ROWID-alias treatment (only a column typed exactly `INTEGER` does), which broke the initial `processing_events` design under the SQLite-backed test suite. Standardizing on UUIDs everywhere avoids this class of dialect quirk entirely rather than special-casing one table.
- **JSONB for `structured_data`**: the `ClinicalReport` contract (§7 of the architecture doc) has multiple nested list-of-object sections (`symptoms`, `diagnoses`, `medications`, ...) that will keep growing/changing as the AI pipeline is implemented. Normalizing each into its own table now would mean a migration for every schema tweak to the AI contract, for querying patterns (per-patient trend queries, cross-report search) that don't exist yet. JSONB stores the whole validated Pydantic payload as the single source of truth, while `report_summary` and `requires_review` are promoted to real columns specifically because those two *are* known to need direct filtering/display.
- **Portable types (`with_variant`, `native_enum=False`)**: the exact same SQLAlchemy models produce a working schema on both PostgreSQL (production, via the JSONB/enum-check-constraint path) and SQLite (`backend/tests/conftest.py`, an in-memory DB per test). This means the unit/API test suite runs in milliseconds with zero external dependencies, while `tests/integration/` (not yet implemented) is where behavior that's genuinely Postgres-specific will be verified against the real engine.

## Alternatives Considered

- **Auto-incrementing integer PKs** — simpler DDL, but reintroduces the dialect portability problem above and offers no benefit here (no volume/performance claim is being made either way at this stage).
- **Fully normalized report schema** (separate `symptoms`, `diagnoses`, `medications` tables, etc.) — rejected for now as premature: it would require guessing the final AI output shape before the AI pipeline exists, and none of the assignment's required read patterns (list analyses, fetch one report) need it. Revisit once real query patterns against report contents emerge.
- **Native Postgres `ENUM` types** — rejected because altering a native enum's allowed values is a more invasive migration than altering a `VARCHAR` + check constraint, and native enums don't exist on SQLite, which would have broken the portable-test-suite goal above.

## Trade-offs

- JSONB fields aren't validated by the database — correctness of `structured_data` depends entirely on the Pydantic `ClinicalReport` validator running before persistence (see `app/services/analysis_service.py` and the schema's `model_validator`s). This is an accepted trade-off: the validation lives once, at the application boundary, rather than being duplicated as DB constraints.
- Querying *inside* the JSONB blob (e.g. "find all reports mentioning a given medication") is possible with Postgres JSONB operators but not indexed by default; add a `GIN` index or promote fields to columns if/when that access pattern is actually needed.
- No claims are made here about throughput or storage cost — none have been measured, and none should be assumed from this design.
