import importlib.util
from pathlib import Path
from typing import Protocol


class CommitValidator(Protocol):
    def is_valid_commit_subject(self, subject: str) -> bool: ...


def _load_validator() -> CommitValidator:
    script_path = Path(__file__).parents[1] / "scripts" / "validate_commit_msg.py"
    spec = importlib.util.spec_from_file_location("validate_commit_msg", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_conventional_commit_subjects_are_valid() -> None:
    validator = _load_validator()

    assert validator.is_valid_commit_subject("docs: add project governance")
    assert validator.is_valid_commit_subject("feat(rag): add retrieval service")
    assert validator.is_valid_commit_subject("fix!: drop unsupported source")


def test_non_conventional_commit_subjects_are_invalid() -> None:
    validator = _load_validator()

    assert not validator.is_valid_commit_subject("")
    assert not validator.is_valid_commit_subject("update stuff")
    assert not validator.is_valid_commit_subject("feat missing separator")
