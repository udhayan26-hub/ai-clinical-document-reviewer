"""The default `AIProvider` while `AI_PROVIDER=placeholder` (the shipped
default — see `.env.example`). No real LLM integration exists yet in this
phase; this class exists so `app.ai.factory.get_default_ai_provider()`
always returns *something* implementing `AIProvider`, and so calling the
pipeline without a configured provider fails honestly and immediately
with a clear, typed error — never silently, never with fabricated output.

A future real provider (e.g. calling an actual LLM API) is a new class
implementing `AIProvider` alongside this one, selected by
`app.ai.factory` based on `Settings.ai_provider` — no change needed to
`app.ai.pipeline` or anything above it.
"""

from typing import Any

from app.ai.interfaces import AIProvider
from app.ai.schemas import ExtractionResult
from app.core.exceptions import AIExtractionFailedError, AIGenerationFailedError
from app.document_processing.interfaces import NormalizedDocument


class UnconfiguredAIProvider(AIProvider):
    def extract(self, document: NormalizedDocument) -> ExtractionResult:
        raise AIExtractionFailedError(
            "No AI provider is configured (AI_PROVIDER=placeholder); clinical fact extraction is not available."
        )

    def generate(self, extraction: ExtractionResult) -> dict[str, Any]:
        raise AIGenerationFailedError(
            "No AI provider is configured (AI_PROVIDER=placeholder); report generation is not available."
        )
