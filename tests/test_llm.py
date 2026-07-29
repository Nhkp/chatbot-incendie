from __future__ import annotations

from dataclasses import dataclass, field

from chatbot_incendie.llm import LocalTransformersGenerator


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
