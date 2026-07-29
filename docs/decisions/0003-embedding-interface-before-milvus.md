# 0003 - Embedding interface before Milvus

## Decision

The project introduces an embedding interface before adding Milvus. The first real
local embedding model candidate is `intfloat/multilingual-e5-small`, but the dependency
is not installed in this milestone.

## Context

Chunks already preserve citation metadata. Milvus should store vectors and metadata,
not decide how chunks become vectors. A small interface lets the project test that
contract offline before introducing model downloads, vector database services, or CI
runtime variability.

`intfloat/multilingual-e5-small` is the preferred first candidate because it is
multilingual, has 384-dimensional embeddings, and is usable through
`sentence-transformers`. `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
remains a fallback candidate with the same vector size and semantic-search use case.

## Consequences

- CI uses deterministic fake embeddings only.
- Real model downloads stay out of unit tests.
- Milvus integration can consume embedded chunks without changing chunking.
- Parquet remains a future curated-data optimization, not part of this milestone.
