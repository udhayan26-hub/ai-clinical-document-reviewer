"""Deterministic tests for OpenAICompatibleProvider. The HTTP boundary is
mocked via httpx.MockTransport — no real network call, no API key
required, ever. See docs/testing/README.md.
"""

import json

import httpx
import pytest

from app.ai.providers.openai_compatible import OpenAICompatibleProvider
from app.core.exceptions import AIExtractionFailedError, AIGenerationFailedError, UnsupportedAIProviderError
from tests.ai.builders import build_grounded_extraction, build_normalized_document


def make_provider(handler) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        api_key="test-key",
        model="gpt-test",
        base_url="https://example.invalid/v1",
        transport=httpx.MockTransport(handler),
    )


def completion_response(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_extract_builds_expected_request_and_parses_response():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content)
        return completion_response(
            json.dumps(
                {
                    "facts": [
                        {
                            "category": "SYMPTOM",
                            "value": "headache",
                            "confidence": "HIGH",
                            "inferred": False,
                            "evidence": [{"quote": "headache"}],
                        }
                    ],
                    "missing_information": [],
                    "notes": [],
                }
            )
        )

    provider = make_provider(handler)
    result = provider.extract(build_normalized_document("Patient has a headache."))

    assert captured["url"].endswith("/chat/completions")
    assert captured["auth"] == "Bearer test-key"
    assert captured["body"]["model"] == "gpt-test"
    assert captured["body"]["messages"][0]["role"] == "system"
    assert captured["body"]["messages"][1]["content"] == "Patient has a headache."
    assert captured["body"]["response_format"] == {"type": "json_object"}
    assert len(result.facts) == 1
    assert result.facts[0].value == "headache"


def test_extract_malformed_json_content_raises_domain_error():
    provider = make_provider(lambda request: completion_response("this is not json"))

    with pytest.raises(AIExtractionFailedError):
        provider.extract(build_normalized_document())


def test_extract_missing_required_field_raises_domain_error():
    """'value' is required on ClinicalFact — a well-formed JSON object
    missing it must still be caught as a domain error, not a raw
    pydantic.ValidationError leaking out."""
    provider = make_provider(
        lambda request: completion_response(json.dumps({"facts": [{"category": "SYMPTOM"}], "missing_information": [], "notes": []}))
    )

    with pytest.raises(AIExtractionFailedError):
        provider.extract(build_normalized_document())


def test_extract_http_error_status_raises_domain_error():
    provider = make_provider(lambda request: httpx.Response(500, json={"error": "internal server error"}))

    with pytest.raises(AIExtractionFailedError):
        provider.extract(build_normalized_document())


def test_extract_timeout_raises_domain_error():
    def handler(request: httpx.Request):
        raise httpx.TimeoutException("timed out", request=request)

    provider = make_provider(handler)

    with pytest.raises(AIExtractionFailedError):
        provider.extract(build_normalized_document())


def test_extract_unexpected_response_shape_raises_domain_error():
    provider = make_provider(lambda request: httpx.Response(200, json={"unexpected": "shape"}))

    with pytest.raises(AIExtractionFailedError):
        provider.extract(build_normalized_document())


def test_generate_success_returns_plain_dict():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["messages"][1]["content"]  # extraction JSON was passed as user content
        return completion_response(json.dumps({"report_summary": "ok", "requires_review": True}))

    provider = make_provider(handler)
    draft = provider.generate(build_grounded_extraction())

    assert draft == {"report_summary": "ok", "requires_review": True}


def test_generate_malformed_json_raises_domain_error():
    provider = make_provider(lambda request: completion_response("{not valid json"))

    with pytest.raises(AIGenerationFailedError):
        provider.generate(build_grounded_extraction())


def test_generate_non_object_json_raises_domain_error():
    provider = make_provider(lambda request: completion_response(json.dumps(["not", "an", "object"])))

    with pytest.raises(AIGenerationFailedError):
        provider.generate(build_grounded_extraction())


def test_factory_raises_when_openai_selected_without_api_key(monkeypatch):
    from app.ai import factory as ai_factory
    from app.core.config import Settings

    monkeypatch.setattr(ai_factory, "get_settings", lambda: Settings(ai_provider="openai", ai_api_key="changeme"))
    ai_factory.get_default_ai_provider.cache_clear()
    try:
        with pytest.raises(UnsupportedAIProviderError):
            ai_factory.get_default_ai_provider()
    finally:
        ai_factory.get_default_ai_provider.cache_clear()


def test_factory_returns_real_provider_when_openai_configured(monkeypatch):
    from app.ai import factory as ai_factory
    from app.core.config import Settings

    monkeypatch.setattr(
        ai_factory,
        "get_settings",
        lambda: Settings(ai_provider="openai", ai_api_key="sk-test-not-real", ai_model_name="gpt-test"),
    )
    ai_factory.get_default_ai_provider.cache_clear()
    try:
        provider = ai_factory.get_default_ai_provider()
        assert isinstance(provider, OpenAICompatibleProvider)
    finally:
        ai_factory.get_default_ai_provider.cache_clear()
