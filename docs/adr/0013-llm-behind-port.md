# 13. Language model behind a port

Date: 2026-09-30 · Status: Accepted

## Context

Azure OpenAI is covered by the non-profit Azure credit and can process data in the EU.
Other models may be compared on the golden set later, and tests must not depend on a
real model.

## Decision

The core defines an `LLMProvider` port (chat completion with tool calling). The Azure
OpenAI adapter implements it with the `openai` SDK and Managed Identity authentication.
Tests use a scriptable `FakeLLM`.

## Consequences

* Switching or comparing models means writing another adapter, not changing the core.
* The model deployment is configured per group (`llm.deployment`).
