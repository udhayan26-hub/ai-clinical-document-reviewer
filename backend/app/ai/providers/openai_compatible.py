"""Real `AIProvider` implementation calling an OpenAI-compatible chat
completions API (OpenAI itself by default; set AI_API_BASE_URL to point
at Azure OpenAI, OpenRouter, a self-hosted vLLM, or any other endpoint
exposing the same /chat/completions shape).

Uses a plain `httpx` HTTP call rather than the `openai` SDK — the surface
needed (one POST, one JSON body, one Bearer header) doesn't justify an
extra dependency (`httpx` is already required by the project).
"""

import json
import logging
from typing import Any

import httpx

from app.ai.interfaces import AIProvider
from app.ai.schemas import ExtractionResult
from app.core.exceptions import AIExtractionFailedError, AIGenerationFailedError, AppError
from app.document_processing.interfaces import NormalizedDocument

logger = logging.getLogger("app.ai.providers.openai_compatible")

DEFAULT_TIMEOUT_SECONDS = 60.0

EXTRACTION_SYSTEM_PROMPT = """You are a clinical document extraction assistant. You will be given the normalized text of one clinical document. Extract ONLY information explicitly supported by the document text — never invent, assume, or add outside medical knowledge.

Respond with ONLY a single JSON object (no markdown, no commentary) in exactly this shape:
{
  "facts": [
    {
      "category": one of ["PATIENT_IDENTIFIER","DOCUMENT_METADATA","OBSERVATION","SYMPTOM","DIAGNOSIS","MEDICATION","ALLERGY","INVESTIGATION","LAB_RESULT","VITAL_SIGN","PROCEDURE","HISTORY"],
      "value": "short text describing the fact",
      "evidence": [{"quote": "EXACT verbatim substring copied from the document text", "context": null}],
      "confidence": "HIGH" | "MEDIUM" | "LOW",
      "inferred": false
    }
  ],
  "missing_information": ["short description of an expected field not found in the document"],
  "notes": ["any extraction caveat"]
}

Rules:
- Every "quote" MUST be copied character-for-character from the document text — never paraphrase, translate, or summarize inside a quote.
- If a fact is stated directly, set inferred=false and cite at least one evidence quote copied verbatim from the document.
- If a fact is your interpretation rather than something stated directly, set inferred=true (evidence may then be empty).
- Do not fabricate patient identifiers, dates, diagnoses, or values that are not present in the document.
- If the document lacks an expected category of information (e.g. no medications mentioned), add a short entry to "missing_information" instead of inventing a fact.
"""

GENERATION_SYSTEM_PROMPT = """You are a clinical report drafting assistant. You will be given a JSON object of clinical facts already extracted from a document (each fact carries evidence quoted verbatim from that document). Produce a structured DRAFT clinical report for a human clinician to review. This is a document-review/triage aid, not an autonomous diagnostic tool — never present anything as more certain than the underlying facts support.

Respond with ONLY a single JSON object (no markdown, no commentary) in exactly this shape (omit fields/sections that don't apply as empty lists, but keep report_summary and requires_review):
{
  "report_summary": "short plain-language summary of the document's clinical content",
  "patient_information": {"name": null, "age": null, "sex": null, "date_of_birth": null, "additional_identifiers": {}, "confidence": "LOW", "evidence": [], "inferred": true},
  "symptoms": [{"description": "...", "onset": null, "severity": null, "confidence": "HIGH", "evidence": [{"quote": "..."}], "inferred": false}],
  "diagnoses": [{"condition": "...", "icd10_code": null, "status": null, "confidence": "HIGH", "evidence": [{"quote": "..."}], "inferred": false}],
  "medications": [{"name": "...", "dosage": null, "frequency": null, "route": null, "confidence": "HIGH", "evidence": [{"quote": "..."}], "inferred": false}],
  "vitals": [{"name": "...", "value": "...", "unit": null, "recorded_at": null, "confidence": "HIGH", "evidence": [{"quote": "..."}], "inferred": false}],
  "allergies": [{"substance": "...", "reaction": null, "severity": null, "confidence": "HIGH", "evidence": [{"quote": "..."}], "inferred": false}],
  "clinical_observations": [{"description": "...", "category": null, "confidence": "HIGH", "evidence": [{"quote": "..."}], "inferred": false}],
  "clinical_concerns": [{"description": "...", "severity": null, "recommended_action": null, "confidence": "MEDIUM", "evidence": [{"quote": "..."}], "inferred": true}],
  "missing_information": [{"field": "...", "reason": null}],
  "potential_inconsistencies": [{"description": "...", "related_fields": [], "evidence": []}],
  "requires_review": true
}

Critical rules:
- Every "quote" in every "evidence" entry MUST be copied EXACTLY from the evidence quotes already present in the input facts — never write a new quote, paraphrase, or invent one.
- Never state a diagnosis, medication, vital, or finding that has no corresponding extracted fact.
- Never claim higher confidence for a finding than the source fact(s) it's based on.
- Copy every item from the input's "missing_information" into the report's "missing_information".
- If anything is uncertain, inferred, or incomplete anywhere in the report, set "requires_review": true.
"""


class OpenAICompatibleProvider(AIProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._model = model
        # `transport` is injectable (httpx.MockTransport in tests) so the
        # real auth/header/base_url setup below always applies identically
        # in tests and production — only the actual network send differs.
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            transport=transport,
        )

    def extract(self, document: NormalizedDocument) -> ExtractionResult:
        payload = self._chat_json(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_content=document.text,
            failure_error_cls=AIExtractionFailedError,
        )
        try:
            return ExtractionResult(**payload)
        except Exception as exc:
            raise AIExtractionFailedError(
                "The AI provider returned extraction output that does not match the expected shape."
            ) from exc

    def generate(self, extraction: ExtractionResult) -> dict[str, Any]:
        return self._chat_json(
            system_prompt=GENERATION_SYSTEM_PROMPT,
            user_content=extraction.model_dump_json(),
            failure_error_cls=AIGenerationFailedError,
        )

    def _chat_json(
        self, *, system_prompt: str, user_content: str, failure_error_cls: type[AppError]
    ) -> dict[str, Any]:
        try:
            response = self._client.post(
                "/chat/completions",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0,
                },
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise failure_error_cls("The AI provider request timed out.") from exc
        except httpx.HTTPStatusError as exc:
            # Never forward the response body/headers to the caller — may
            # contain provider-internal details, never the API key (that's
            # only ever sent, never echoed back), but conservative regardless.
            raise failure_error_cls(f"The AI provider returned HTTP {exc.response.status_code}.") from exc
        except httpx.HTTPError as exc:
            raise failure_error_cls("The AI provider request failed.") from exc

        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise failure_error_cls("The AI provider response did not have the expected shape.") from exc

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise failure_error_cls("The AI provider did not return valid JSON.") from exc

        if not isinstance(parsed, dict):
            raise failure_error_cls("The AI provider's JSON response was not an object.")

        return parsed
