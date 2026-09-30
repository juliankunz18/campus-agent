# 12. Business data in SharePoint, runtime state in Table Storage

Date: 2026-09-30 · Status: Accepted

## Context

The board must be able to see and correct association data without the bot. The bot
itself needs fast storage for history, pending actions and the audit log.

## Decision

* Business data lives in SharePoint lists and libraries on a dedicated site: members,
  teams, activities, applications (one list for all kinds, distinguished by type),
  certificates and knowledge. Lists get unique permissions: only the board has direct
  access; the knowledge library is readable by all members.
* Technical runtime state (conversation history, pending actions, audit log) lives in
  Azure Table Storage behind the `RuntimeStore` port; locally Azurite emulates it.

## Consequences

* SharePoint stays the single source of truth that the board can inspect.
* Only the repository adapters know list and column names.
* Table Storage is cheap and covered by the non-profit Azure credit.
