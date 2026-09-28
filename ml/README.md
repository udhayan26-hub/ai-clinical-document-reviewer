# ML Layer

This directory holds the AI/ML layer for the AI Clinical Document Reviewer, kept **modular and independent** from the FastAPI backend (`backend/app/ai` only calls into this layer through a stable interface — it does not contain model/provider-specific logic itself).

Design goal: the underlying model/provider (LLM or otherwise) must be swappable without changes to the API layer or document processing pipeline.

## Structure

- `prompts/` — prompt templates used for clinical information extraction and report generation
- `schemas/` — structured input/output schemas for the AI pipeline (extraction results, report structure, etc.)
- `pipeline/` — orchestration logic: document → extraction → analysis → structured report
- `evaluators/` — evaluation/validation logic for AI outputs (accuracy, completeness, safety checks)

No pipeline or provider implementation exists yet — this is a structural placeholder only.
