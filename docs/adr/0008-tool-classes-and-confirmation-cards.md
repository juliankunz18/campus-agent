# 8. Tool classes and confirmation cards

Date: 2026-09-30 · Status: Accepted

## Context

The model should be able to read data and prepare drafts, but nothing binding may
happen without an explicit human decision. Half-executed actions after a model or
network failure must be impossible.

## Decision

Every tool has one of three classes:

| Class | Execution |
|---|---|
| `read` | immediately inside the loop |
| `draft` | immediately; only creates a draft |
| `commit` | never from the model: stored as a pending action with an idempotency key and 24 h validity, executed only after a click on a confirmation card, without the model |

On confirmation the user and role are checked again, and the idempotency key ensures
the action runs at most once (`CONFLICT` on repetition).

## Consequences

* Card content is built only from server-side data, never from model text.
* A failed LLM or MCP call yields a short message with an error ID; binding actions
  cannot be half executed.
