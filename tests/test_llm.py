from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from chatbot_incendie.llm import (
    AnthropicApiGenerator,
    GeminiApiGenerator,
    LlmProvider,
    LocalTransformersGenerator,
    OpenAICompatibleGenerator,
    build_llm_generator,
    default_model_for_provider,
)


@dataclass
class FakeTextGenerationBackend:
    generated_text: str
    calls: list[dict[str, object]] = field(default_factory=list)

    def __call__(
        self,
        text_inputs: str,
        *,
        max_new_tokens: int,
        do_sample: bool,
        return_full_text: bool,
        clean_up_tokenization_spaces: bool,
    ) -> object:
        self.calls.append(
            {
                "text_inputs": text_inputs,
                "max_new_tokens": max_new_tokens,
                "do_sample": do_sample,
                "return_full_text": return_full_text,
                "clean_up_tokenization_spaces": clean_up_tokenization_spaces,
            }
        )
        return [{"generated_text": self.generated_text}]


@dataclass
class FakeJsonPoster:
    response: dict[str, Any]
    calls: list[dict[str, object]] = field(default_factory=list)

    def __call__(
        self,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "url": url,
                "payload": payload,
                "headers": headers,
                "timeout_seconds": timeout_seconds,
            }
        )
        return self.response


def test_local_transformers_generator_uses_backend_without_sampling() -> None:
    backend = FakeTextGenerationBackend(" Réponse sourcée [1]. ")
    generator = LocalTransformersGenerator(
        model_name="fake-model",
        max_new_tokens=42,
        backend=backend,
    )

    answer = generator.generate("Prompt")

    assert answer == "Réponse sourcée [1]."
    assert generator.model_name == "fake-model"
    assert backend.calls == [
        {
            "text_inputs": "Prompt",
            "max_new_tokens": 42,
            "do_sample": False,
            "return_full_text": False,
            "clean_up_tokenization_spaces": False,
        }
    ]


def test_local_transformers_generator_returns_empty_text_for_unexpected_output() -> None:
    class EmptyBackend:
        def __call__(
            self,
            text_inputs: str,
            *,
            max_new_tokens: int,
            do_sample: bool,
            return_full_text: bool,
            clean_up_tokenization_spaces: bool,
        ) -> object:
            return []

    generator = LocalTransformersGenerator(backend=EmptyBackend())

    assert generator.generate("Prompt") == ""


def test_gemini_generator_sends_generate_content_payload() -> None:
    poster = FakeJsonPoster(
        {"candidates": [{"content": {"parts": [{"text": "Réponse Gemini [1]."}]}}]}
    )
    generator = GeminiApiGenerator(
        api_key="gemini-key",
        model_name="gemini-test",
        max_new_tokens=33,
        temperature=0.1,
        post_json=poster,
    )

    answer = generator.generate("Prompt RAG")

    assert answer == "Réponse Gemini [1]."
    call = poster.calls[0]
    assert call["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-test:generateContent?key=gemini-key"
    )
    assert call["payload"] == {
        "contents": [{"role": "user", "parts": [{"text": "Prompt RAG"}]}],
        "generationConfig": {"maxOutputTokens": 33, "temperature": 0.1},
    }


def test_openai_compatible_generator_sends_chat_completion_payload() -> None:
    poster = FakeJsonPoster({"choices": [{"message": {"content": "Réponse Mistral [1]."}}]})
    generator = OpenAICompatibleGenerator(
        api_key="mistral-key",
        model_name="mistral-small",
        base_url="https://api.mistral.ai/v1",
        provider_name="mistral",
        max_new_tokens=44,
        temperature=0.0,
        post_json=poster,
    )

    answer = generator.generate("Prompt RAG")

    assert answer == "Réponse Mistral [1]."
    call = poster.calls[0]
    assert call["url"] == "https://api.mistral.ai/v1/chat/completions"
    assert call["headers"] == {
        "Content-Type": "application/json",
        "Authorization": "Bearer mistral-key",
    }
    assert call["payload"] == {
        "model": "mistral-small",
        "messages": [{"role": "user", "content": "Prompt RAG"}],
        "max_tokens": 44,
        "temperature": 0.0,
    }


def test_anthropic_generator_sends_messages_payload() -> None:
    poster = FakeJsonPoster({"content": [{"type": "text", "text": "Réponse Claude [1]."}]})
    generator = AnthropicApiGenerator(
        api_key="anthropic-key",
        model_name="claude-test",
        max_new_tokens=55,
        temperature=0.2,
        post_json=poster,
    )

    answer = generator.generate("Prompt RAG")

    assert answer == "Réponse Claude [1]."
    call = poster.calls[0]
    assert call["url"] == "https://api.anthropic.com/v1/messages"
    assert call["headers"] == {
        "Content-Type": "application/json",
        "x-api-key": "anthropic-key",
        "anthropic-version": "2023-06-01",
    }
    assert call["payload"] == {
        "model": "claude-test",
        "max_tokens": 55,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": "Prompt RAG"}],
    }


def test_missing_cloud_api_key_is_rejected() -> None:
    with pytest.raises(ValueError, match="GEMINI_API_KEY must be set"):
        GeminiApiGenerator(api_key=" ")


def test_build_llm_generator_selects_default_provider_models() -> None:
    gemini = build_llm_generator(
        provider=LlmProvider.GEMINI,
        model_name="",
        max_new_tokens=120,
        temperature=0.0,
        api_keys={"GEMINI_API_KEY": "key"},
    )

    assert isinstance(gemini, GeminiApiGenerator)
    assert gemini.model_name == default_model_for_provider(LlmProvider.GEMINI)
