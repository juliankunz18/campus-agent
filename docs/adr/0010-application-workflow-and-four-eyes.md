# 10. Application workflow and four-eyes principle in the core

Date: 2026-09-30 · Status: Accepted

## Context

Certificate applications and data change requests go through the same approval process.
Several modules need it, and the rules must not be weakened by a module.

## Decision

The application workflow lives in the core (`campus_agent_core.domain.applications`) as
pure functions:

* States DRAFT, SUBMITTED, CLARIFICATION, APPROVED, REJECTED with exactly these
  transitions: submit and discard (draft); approve, reject and request clarification
  (submitted); answer and expiry after 30 days (clarification). APPROVED and REJECTED
  are final. Invalid transitions raise `INVALID_STATE`.
* Four-eyes principle: applicants can neither approve nor reject their own application
  (`FORBIDDEN`). We apply the same rule to requesting clarification. Bulk approval skips
  own applications.
* Only the applicant may submit, answer or discard (`NOT_FOUND` for others, so that
  foreign applications cannot be probed).

The core tools (`submit_application`, `approve_application`, `approve_all_open`, ...)
are shipped by a built-in `core` module registered like any other module.

## Consequences

* Rules are not configurable and cannot be switched off.
* Corrections to decided applications always need a new application.
