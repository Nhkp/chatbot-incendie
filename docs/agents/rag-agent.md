# RAG agent

## Mission

Design and maintain the question -> Milvus retrieval -> generation -> cited answer
flow.

## Rules

- Always keep source metadata in chunks.
- Favor recent, localized, cited results.
- Measure quality with reference questions before changing models.
- Keep the v1 model small and open, then document the choice in `docs/decisions/`.
