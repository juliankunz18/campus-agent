# 5. Own agent loop, no agent framework

Date: 2026-09-30 · Status: Accepted

## Context

The loop must guarantee that the model only sees the tools of the user's role, that
binding actions never run on the model's request, and that fixed limits apply. Agent
frameworks (LangChain, LlamaIndex, CrewAI) add many dependencies and abstractions that
make these guarantees harder to see and to test.

## Decision

The agent loop is our own code in `campus_agent_core.agent` (a few hundred lines):
build context, call the model with a timeout, apply the tool policy, execute read and
draft tools, return commit tools as pending actions, stop after the configured number
of tool rounds. No agent framework is used.

## Consequences

* Full control over role filtering, tool release and confirmations, with few
  dependencies.
* The loop is tested with a scripted fake model.
* Features such as streaming or parallel tool execution must be built by us if needed.
