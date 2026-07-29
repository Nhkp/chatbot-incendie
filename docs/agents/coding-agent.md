# Coding agent

## Mission

Change code with the smallest correct diff, while respecting the existing structure.

## Rules

- Read callers and usages before changing a shared function.
- Reuse dependencies already present in the project.
- Add a test for any non-trivial logic.
- Run `scripts/check.sh` before finishing when the change touches code.
- Avoid premature abstractions.
