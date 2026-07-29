from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

DEFAULT_LLM_MODEL = "Qwen/Qwen3-0.6B"


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
