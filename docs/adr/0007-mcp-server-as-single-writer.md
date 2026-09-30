# 7. MCP server as the only writer, enforcing all rules

Date: 2026-09-30 · Status: Accepted

## Context

The model can be manipulated through prompts or documents. Authorization that lives in
the prompt or in the bot alone can be bypassed.

## Decision

* A separate MCP server (official `mcp` SDK, Streamable HTTP) is the only component with
  write access to SharePoint. It is reachable only from the bot backend (internal
  ingress).
* The server enforces every rule itself - role, four-eyes principle, state machine,
  data minimisation - regardless of what the model proposes, and writes an audit entry
  for every writing action.
* Layers: tool definitions without business logic, services with the rules,
  repositories as the only place that knows list and column names.
* The Graph app registration gets `Sites.Selected` with write access to the group's own
  site only.

## Consequences

* Tools can be tested in isolation with the MCP Inspector, without a model.
* The MCP server must verify the caller's Entra token before trusting the forwarded
  user ID; until that is implemented it only starts in local development.
