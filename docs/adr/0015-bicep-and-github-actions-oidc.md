# 15. Infrastructure with Bicep, CI/CD with GitHub Actions and OIDC

Date: 2026-09-30 · Status: Accepted

## Context

Groups need a reproducible setup they can understand, and no Azure secrets should be
stored in GitHub.

## Decision

* Infrastructure is described in Bicep in this repository, plus a "Deploy to Azure"
  template for new groups: Container Apps for bot and MCP server, Storage, Key Vault,
  Azure OpenAI, managed identities.
* GitHub Actions: pull requests run ruff, pyright, tests (including the permission
  matrix), gitleaks and the DCO check. Merges to `main` build images, push them to the
  GitHub Container Registry and deploy to `dev`. Release tags run the evaluation against
  `dev` and deploy the same image to `prod` after a maintainer approves the `prod`
  environment.
* Azure access from GitHub uses OIDC federation, never stored credentials.

## Consequences

* A rollback activates the previous Container Apps revision; no rebuild is needed.
* Group-specific parameters stay in the private deployment repository.
