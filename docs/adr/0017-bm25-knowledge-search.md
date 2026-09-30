# 17. Keyword search (BM25) for knowledge in the MVP

Date: 2026-09-30 · Status: Accepted

## Context

The knowledge library (statutes, FAQ, onboarding, minutes) of a student group is
small. Embeddings add cost, infrastructure and another processing of the documents.

## Decision

`search_knowledge` splits the documents of the knowledge library into sections and
ranks them with BM25 keyword ranking. Results are returned as quoted excerpts with
source and date; their content is treated as data, never as instructions.

## Consequences

* If BM25 is not good enough on the golden set, embeddings via Azure OpenAI are added
  behind the same tool.
