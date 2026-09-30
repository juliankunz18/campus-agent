# 11. Modules via entry points and manifests

Date: 2026-09-30 · Status: Accepted

## Context

Groups want different features (for example cooperation events) without forking the
core, and modules should be developable and testable without a tenant.

## Decision

* A module is a Python package that registers a manifest under the entry point group
  `campus_agent.modules`, in this repository or published separately.
* The Pydantic manifest declares name, version, required roles, SharePoint lists with
  columns, tools and prompt fragments, plus an optional settings model.
* Modules import only `campus_agent_core.ports`; they never import adapters, apps or
  other modules. An architecture test enforces this.
* The loader validates manifests, texts in every language and module settings against
  the configuration, and builds a tool registry filtered by role.

## Consequences

* `campus-agent provision` creates the lists of all active modules; `doctor` checks the
  configuration.
* Open question: module settings such as `organizer_role` are validated but do not yet
  override the fixed minimum roles of the tool catalog.
