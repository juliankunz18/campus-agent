# 2. Framework first, deployments in private repositories

Date: 2026-09-30 · Status: Accepted

## Context

The assistant is built for one pilot group first, but other non-profit student groups
need the same basics: roles, applications with approval, certificates, knowledge,
events. Association data must never get near a public repository.

## Decision

* The public repository `campus-agent` contains only the framework: core, modules,
  adapters, documentation and the fictional example group "Musterverein" with test
  data. Nothing in the core is specific to one group.
* Each group keeps a private deployment repository with its `campus-agent.yaml`,
  templates with logo and signature, infrastructure parameters and its real golden set.
  It deploys a versioned container image released from the public repository.

## Consequences

* Group-specific wishes must be expressible as configuration or as a module.
* Real data, IDs and secrets are forbidden in this repository; CI and pre-commit run
  gitleaks, and reviews check for real names and IDs.
* Releases follow SemVer and are published as container images.
