# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Configurable role slots: tools name a function (`base`, `approver`, `member_admin`,
  `activity_confirmer`, `organizer`) that each group maps to its own roles;
  `applications.approver_role`, `members.admin_role`, `certificates.confirmer_role` and
  `events.organizer_role` take effect, and `doctor` shows the mapping.
- uv workspace with core, integrations, four modules (members, certificates, knowledge,
  events) and three apps (bot, MCP server, CLI).
- Roles with inheritance from the configuration and role checks for tools.
- Application state machine (draft, submitted, clarification, approved, rejected) with
  the four-eyes principle and bulk approval that skips own applications.
- Tool policy: `read` and `draft` tools run in the agent loop, `commit` tools become
  pending actions with an idempotency key and 24 h validity.
- Configuration schema for `campus-agent.yaml` with `${ENV}` substitution and readable
  errors; fictional Musterverein example.
- Module system with entry points, Pydantic manifests, German and English texts and a
  role-filtered tool registry; permission matrix test over all roles and tools.
- Agent loop skeleton with the limits from the design as configuration.
- MCP server (official `mcp` SDK, Streamable HTTP) and bot backend (aiohttp) with health
  checks; CLI with `init`, `provision` (dry run) and `doctor`.
- Adapter stubs for Teams, SharePoint/Graph, Azure OpenAI and Table Storage, plus fakes.
- Evaluation runner skeleton with synthetic golden set and attack cases.
- Dockerfiles, compose setup with Azurite, CI with gitleaks and DCO check, ADRs.

[Unreleased]: https://github.com/juliankunz18/campus-agent/commits/main
