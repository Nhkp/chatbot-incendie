from __future__ import annotations

import re
import sys
from pathlib import Path

COMMIT_RE = re.compile(
    r"^(feat|fix|docs|test|refactor|chore|ci|build|perf|style|revert)"
    r"(\([a-z0-9._-]+\))?!?: .{1,72}$"
)
IGNORED_PREFIXES = (
    "Merge ",
    "Revert ",
    "fixup! ",
    "squash! ",
)


def is_valid_commit_subject(subject: str) -> bool:
    return subject.startswith(IGNORED_PREFIXES) or COMMIT_RE.match(subject) is not None


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_commit_msg.py <commit-msg-file>", file=sys.stderr)
        return 2

    lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    first_line = lines[0].strip() if lines else ""
    if is_valid_commit_subject(first_line):
        return 0

    print(
        "Commit message must follow Conventional Commits, for example: "
        "feat(rag): add retrieval service",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
