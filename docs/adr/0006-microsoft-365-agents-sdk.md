# 6. Microsoft 365 Agents SDK for Teams

Date: 2026-09-30 · Status: Accepted

## Context

The Bot Framework SDK for Python is being replaced by the Microsoft 365 Agents SDK,
which has been at version 1.x since May 2026. It covers Teams activities, Adaptive
Cards, authentication (MSAL) and aiohttp hosting.

## Decision

The bot backend uses the Microsoft 365 Agents SDK with `microsoft-agents-hosting-aiohttp`
and `microsoft-agents-authentication-msal`. For Teams-specific features it uses
`microsoft-agents-hosting-msteams`.

The technical design named `microsoft-agents-hosting-teams`; version 1.7.0 of that
package marks itself as deprecated in favour of `microsoft-agents-hosting-msteams`, so
the successor is used.

## Consequences

* Locally, the Microsoft 365 Agents Playground simulates Teams including Adaptive Cards.
* The SDK is young; APIs are verified against the pinned version before use, and
  unclear parts stay TODO instead of guessed code.
