# 18. Apache License 2.0 and DCO instead of a CLA

Date: 2026-09-30 · Status: Accepted

## Context

The framework is created by Julian Kunz and used by the pilot group under its
open-source license; other groups and contributors should be able to use, fork and
extend it. The technical design left the choice between Apache-2.0 and MIT open.

## Decision

* License: Apache License 2.0, with a NOTICE file. Compared with MIT it adds an
  explicit patent grant and clear rules for contributions (section 5).
* Copyright: Julian Kunz and contributors. Contributors keep the copyright of their
  contributions, which are licensed under the project license ("inbound = outbound").
* Contributions need a Developer Certificate of Origin sign-off (`git commit -s`),
  checked in CI. There is no contributor license agreement.

## Consequences

* A relicensing would need the consent of all copyright holders.
* Group-specific content (configuration, templates, data) is not part of the project
  and stays with each group.
