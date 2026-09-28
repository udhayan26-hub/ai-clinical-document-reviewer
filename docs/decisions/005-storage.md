# 005. Storage: local disk for development, object storage abstraction for uploaded files

## Problem

Uploaded images and PDFs (raw bytes) need somewhere to live that is separate from both the relational database and the extracted/derived data, in a way that works identically in local development and once deployed to AWS.

## Decision

- The database never stores raw file bytes. `documents.storage_uri` holds a reference to where the bytes live; `documents.checksum_sha256` and `documents.size_bytes` are computed and stored at upload time regardless of where the bytes end up.
- Local development target: a local filesystem directory (`UPLOAD_STORAGE_DIR` in `.env.example`, default `./backend/storage`).
- Production target (AWS, not yet implemented): object storage (S3), referenced by the same `storage_uri` column.
- Plain-text submissions bypass file storage entirely — text is small, already structured, and is stored directly as `analyses.extracted_text`; there is no "raw file" for a `TEXT` document beyond the text itself.

## Rationale

- Keeping raw bytes out of PostgreSQL keeps the database focused on structured/query-able data and avoids bloating it with binary blobs that don't need transactional/relational treatment.
- Using a URI-style reference column (rather than, say, assuming a local path format) means the actual backing store can change (local disk → S3) without a schema change — only what `storage_uri` points at changes.
- Computing `checksum_sha256` at upload time (before storage-backend selection matters) gives a stable, storage-independent way to identify/deduplicate a document later, and is cheap to do regardless of file size.

## Alternatives Considered

- **Storing files as PostgreSQL `bytea`/large objects** — rejected: mixes binary storage concerns into the relational database, complicates backups/replication sizing, and gives no benefit over a dedicated object store for this access pattern (write-once, read-occasionally, never queried by content).
- **Committing to S3 immediately, even in local dev** — rejected for this phase: it would require AWS credentials/connectivity just to run `docker compose up` locally, adding friction before there's even a real object-storage-writing code path implemented. The local-disk path and the future S3 path are meant to be interchangeable behind the same `storage_uri` contract, not developed as two divergent systems.

## Trade-offs

- **Not yet implemented**: no code currently writes bytes to `UPLOAD_STORAGE_DIR` or to S3 — `AnalysisService.create_analysis` currently persists `storage_uri=None` for every document (see its docstring/comment). This is in scope for the document-processing implementation phase, not this architecture phase.
- A local-disk storage path means local dev data isn't portable across machines/containers without a shared volume — acceptable for a single-developer/local Docker Compose setup; revisit if multi-instance local development becomes a requirement.
- No specific S3 bucket layout, lifecycle policy, or access-control model is decided here — that belongs with `006-deployment.md` once AWS deployment is actually undertaken.
