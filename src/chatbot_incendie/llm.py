from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_LLM_MODEL = "Qwen/Qwen3-0.6B"
DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"
DEFAULT_MISTRAL_MODEL = "mistral-small-latest"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_OPENAI_MODEL = "gpt-5.4-nano"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5"
MISTRAL_API_BASE_URL = "https://api.mistral.ai/v1"
DEEPSEEK_API_BASE_URL = "https://api.deepseek.com"
OPENAI_API_BASE_URL = "https://api.openai.com/v1"
ANTHROPIC_API_BASE_URL = "https://api.anthropic.com/v1"
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
ANTHROPIC_VERSION = "2023-06-01"


class LlmProvider(StrEnum):
    LOCAL = "local"
    GEMINI = "gemini"
    MISTRAL = "mistral"
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class TextGenerator(Protocol):
    @property
    def model_name(self) -> str: ...

    def generate(self, prompt: str) -> str: ...


class _TextGenerationBackend(Protocol):
    def __call__(
        self,
        text_inputs: str,
        *,
        max_new_tokens: int,
        do_sample: bool,
        return_full_text: bool,
        clean_up_tokenization_spaces: bool,
    ) -> object: ...


class JsonPostFunction(Protocol):
    def __call__(
        self,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> dict[str, Any]: ...


def _post_json(
    url: str,
    payload: dict[str, object],
    headers: dict[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    request = Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as error:
        raise ValueError(f"LLM provider request failed: {error}") from error
    return _json_response(body)


@dataclass(frozen=True)
class LocalTransformersGenerator:
    model_name: str = DEFAULT_LLM_MODEL
    max_new_tokens: int = 220
    backend: _TextGenerationBackend | None = None

    def __post_init__(self) -> None:
        if self.backend is None:
            object.__setattr__(self, "backend", _load_text_generation_pipeline(self.model_name))

    def generate(self, prompt: str) -> str:
        backend = self.backend
        if backend is None:
            raise ValueError("text generation backend is not initialized")
        outputs = backend(
            prompt,
            max_new_tokens=self.max_new_tokens,
            do_sample=False,
            return_full_text=False,
            clean_up_tokenization_spaces=False,
        )
        return _generated_text(outputs).strip()


@dataclass(frozen=True)
class GeminiApiGenerator:
    api_key: str
    model_name: str = DEFAULT_GEMINI_MODEL
    max_new_tokens: int = 120
    temperature: float = 0.0
    base_url: str = GEMINI_API_BASE_URL
    timeout_seconds: float = 60.0
    post_json: JsonPostFunction = field(default=_post_json)

    def __post_init__(self) -> None:
        _require_api_key(self.api_key, "GEMINI_API_KEY")

    def generate(self, prompt: str) -> str:
        url = _gemini_generate_url(self.base_url, self.model_name, self.api_key)
        payload: dict[str, object] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": self.max_new_tokens,
                "temperature": self.temperature,
            },
        }
        response = self.post_json(url, payload, _json_headers(), self.timeout_seconds)
        return _gemini_text(response).strip()


@dataclass(frozen=True)
class OpenAICompatibleGenerator:
    api_key: str
    model_name: str
    base_url: str
    provider_name: str
    max_new_tokens: int = 120
    temperature: float = 0.0
    timeout_seconds: float = 60.0
    post_json: JsonPostFunction = field(default=_post_json)

    def __post_init__(self) -> None:
        _require_api_key(self.api_key, f"{self.provider_name.upper()}_API_KEY")

    def generate(self, prompt: str) -> str:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload: dict[str, object] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_new_tokens,
            "temperature": self.temperature,
        }
        response = self.post_json(
            url,
            payload,
            _bearer_headers(self.api_key),
            self.timeout_seconds,
        )
        return _openai_compatible_text(response).strip()


@dataclass(frozen=True)
class AnthropicApiGenerator:
    api_key: str
    model_name: str = DEFAULT_ANTHROPIC_MODEL
    max_new_tokens: int = 120
    temperature: float = 0.0
    base_url: str = ANTHROPIC_API_BASE_URL
    timeout_seconds: float = 60.0
    post_json: JsonPostFunction = field(default=_post_json)

    def __post_init__(self) -> None:
        _require_api_key(self.api_key, "ANTHROPIC_API_KEY")

    def generate(self, prompt: str) -> str:
        url = f"{self.base_url.rstrip('/')}/messages"
        payload: dict[str, object] = {
            "model": self.model_name,
            "max_tokens": self.max_new_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        response = self.post_json(
            url,
            payload,
            {
                **_json_headers(),
                "x-api-key": self.api_key,
                "anthropic-version": ANTHROPIC_VERSION,
            },
            self.timeout_seconds,
        )
        return _anthropic_text(response).strip()


def _load_text_generation_pipeline(model_name: str) -> _TextGenerationBackend:
    from transformers import pipeline

    return cast(_TextGenerationBackend, pipeline("text-generation", model=model_name))


def _generated_text(outputs: object) -> str:
    if not isinstance(outputs, list) or not outputs:
        return ""
    first = outputs[0]
    if not isinstance(first, dict):
        return ""
    value = first.get("generated_text")
    return value if isinstance(value, str) else ""


def build_llm_generator(
    *,
    provider: LlmProvider,
    model_name: str,
    max_new_tokens: int,
    temperature: float,
    api_keys: dict[str, str],
) -> TextGenerator:
    if max_new_tokens <= 0:
        raise ValueError("llm_max_new_tokens must be greater than 0")
    if provider == LlmProvider.LOCAL:
        return LocalTransformersGenerator(model_name=model_name, max_new_tokens=max_new_tokens)
    if provider == LlmProvider.GEMINI:
        return GeminiApiGenerator(
            api_key=api_keys.get("GEMINI_API_KEY", ""),
            model_name=model_name or DEFAULT_GEMINI_MODEL,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
        )
    if provider == LlmProvider.MISTRAL:
        return OpenAICompatibleGenerator(
            api_key=api_keys.get("MISTRAL_API_KEY", ""),
            model_name=model_name or DEFAULT_MISTRAL_MODEL,
            base_url=MISTRAL_API_BASE_URL,
            provider_name="mistral",
            max_new_tokens=max_new_tokens,
            temperature=temperature,
        )
    if provider == LlmProvider.DEEPSEEK:
        return OpenAICompatibleGenerator(
            api_key=api_keys.get("DEEPSEEK_API_KEY", ""),
            model_name=model_name or DEFAULT_DEEPSEEK_MODEL,
            base_url=DEEPSEEK_API_BASE_URL,
            provider_name="deepseek",
            max_new_tokens=max_new_tokens,
            temperature=temperature,
        )
    if provider == LlmProvider.OPENAI:
        return OpenAICompatibleGenerator(
            api_key=api_keys.get("OPENAI_API_KEY", ""),
            model_name=model_name or DEFAULT_OPENAI_MODEL,
            base_url=OPENAI_API_BASE_URL,
            provider_name="openai",
            max_new_tokens=max_new_tokens,
            temperature=temperature,
        )
    return AnthropicApiGenerator(
        api_key=api_keys.get("ANTHROPIC_API_KEY", ""),
        model_name=model_name or DEFAULT_ANTHROPIC_MODEL,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
    )


def default_model_for_provider(provider: LlmProvider) -> str:
    if provider == LlmProvider.GEMINI:
        return DEFAULT_GEMINI_MODEL
    if provider == LlmProvider.MISTRAL:
        return DEFAULT_MISTRAL_MODEL
    if provider == LlmProvider.DEEPSEEK:
        return DEFAULT_DEEPSEEK_MODEL
    if provider == LlmProvider.OPENAI:
        return DEFAULT_OPENAI_MODEL
    if provider == LlmProvider.ANTHROPIC:
        return DEFAULT_ANTHROPIC_MODEL
    return DEFAULT_LLM_MODEL


def _json_response(body: str) -> dict[str, Any]:
    try:
        data = json.loads(body)
    except json.JSONDecodeError as error:
        raise ValueError("LLM provider response must be valid JSON") from error
    if not isinstance(data, dict):
        raise ValueError("LLM provider response must be a JSON object")
    return data


def _json_headers() -> dict[str, str]:
    return {"Content-Type": "application/json"}


def _bearer_headers(api_key: str) -> dict[str, str]:
    return {**_json_headers(), "Authorization": f"Bearer {api_key}"}


def _gemini_generate_url(base_url: str, model_name: str, api_key: str) -> str:
    query = urlencode({"key": api_key})
    return f"{base_url.rstrip('/')}/models/{model_name}:generateContent?{query}"


def _require_api_key(api_key: str, env_var: str) -> None:
    if not api_key.strip():
        raise ValueError(f"{env_var} must be set when using this LLM provider")


def _gemini_text(response: dict[str, Any]) -> str:
    candidates = response.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ""
    content = _mapping(candidates[0]).get("content")
    parts = _mapping(content).get("parts")
    if not isinstance(parts, list):
        return ""
    return "".join(_text_part(part) for part in parts)


def _openai_compatible_text(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = _mapping(choices[0]).get("message")
    content = _mapping(message).get("content")
    return content if isinstance(content, str) else ""


def _anthropic_text(response: dict[str, Any]) -> str:
    content = response.get("content")
    if not isinstance(content, list):
        return ""
    return "".join(_text_part(part) for part in content)


def _text_part(value: object) -> str:
    data = _mapping(value)
    text = data.get("text")
    return text if isinstance(text, str) else ""


def _mapping(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}
