from functools import lru_cache

from app.ai.interfaces import AIProvider, ClinicalReportValidator
from app.ai.providers.openai_compatible import OpenAICompatibleProvider
from app.ai.providers.unconfigured import UnconfiguredAIProvider
from app.ai.validators.deterministic import DeterministicClinicalReportValidator
from app.core.config import get_settings
from app.core.exceptions import UnsupportedAIProviderError

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
_UNSET_API_KEY_VALUES = {"", "changeme"}


@lru_cache
def get_default_ai_provider() -> AIProvider:
    """Reads `Settings.ai_provider`/`ai_model_name`/`ai_api_key`/
    `ai_api_base_url` so the concrete provider is a config change, not a
    code change, to swap later — mirrors
    `app.document_processing.ocr_tesseract.get_default_ocr_engine`.

    `"placeholder"` (the shipped default) intentionally has no working
    implementation — see `UnconfiguredAIProvider`. `"openai"` selects the
    real `OpenAICompatibleProvider`, which also works against any
    OpenAI-compatible endpoint via `AI_API_BASE_URL` (Azure OpenAI,
    OpenRouter, a self-hosted server, ...). Raises immediately —
    never silently falls back — if `AI_API_KEY` isn't set.
    """
    settings = get_settings()
    if settings.ai_provider == "placeholder":
        return UnconfiguredAIProvider()
    if settings.ai_provider == "openai":
        if settings.ai_api_key.strip() in _UNSET_API_KEY_VALUES:
            raise UnsupportedAIProviderError("AI_PROVIDER=openai requires AI_API_KEY to be set.")
        return OpenAICompatibleProvider(
            api_key=settings.ai_api_key,
            model=settings.ai_model_name,
            base_url=settings.ai_api_base_url or DEFAULT_OPENAI_BASE_URL,
        )
    raise UnsupportedAIProviderError(f"Unknown AI_PROVIDER setting: '{settings.ai_provider}'.")


@lru_cache
def get_default_validator() -> ClinicalReportValidator:
    return DeterministicClinicalReportValidator()
