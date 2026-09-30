# 9. Identity from the verified request, roles from Entra groups

Date: 2026-09-30 · Status: Accepted

## Context

All members of a group use the bot. The most important security property is that a
member can never see or change someone else's data, even by clever prompting.

## Decision

* The user ID comes from the validated Teams token and is passed by the bot backend to
  the MCP server out of band (header), never as a tool argument. **No tool has a
  parameter for the user ID or role**; manifests with such parameters are rejected, and
  tool input models reject unknown arguments.
* Roles are configured from lowest to highest (e.g. `member < team_lead < board`);
  higher roles inherit everything below. The role is derived from Entra group
  membership on every request (cached for 5 minutes) and never stored with the member.
* The model only sees the tools of the user's role; every tool checks the role again.
* `DEV_FAKE_USER` provides a test user for local development and is refused outside
  `CAMPUS_AGENT_ENV=local`.

## Consequences

* A generated permission matrix test checks every role against every tool of every
  installed module; a release requires it to pass without exception.
