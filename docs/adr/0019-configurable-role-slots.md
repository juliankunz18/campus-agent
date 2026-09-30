# 19. Configurable role slots

Date: 2026-09-30 · Status: Accepted · Amends [0010](0010-application-workflow-and-four-eyes.md) and [0011](0011-modules-via-entry-points.md)

## Context

The first scaffold let tools name fixed role IDs (`member`, `team_lead`, `board`). A
group with other role names (for example `mitglied < leitung < vorstand`) could not
start the framework, which contradicts "framework first". The settings
`certificates.approver_role` and `events.organizer_role` were validated but had no
effect, and approval - a core tool for every kind of application - was configured in
the certificates module.

## Decision

Tools name a **role slot** - a function - instead of a role ID. The loader maps every
slot to one of the group's configured roles at start.

* **Core slots:** `base` is the lowest role (everybody in the tenant). `approver`
  decides on applications; it is set with `applications.approver_role` and defaults to
  the highest role. Every module may use the core slots.
* **Module slots** are declared in `ModuleManifest.required_roles` as `RoleSlot`: a name,
  either a positional `default` (`lowest`, `above_lowest`, `highest`) or `inherits`
  (another slot), and optionally the settings field that overrides it.
* **Precedence:** explicit setting, then default or parent slot.
* **Privileged slots** see other people's data or act for them. They may never resolve
  to the lowest role; the loader rejects such a configuration with a clear message. All
  slots are privileged unless declared otherwise (only `base` is not).
* The four-eyes principle, the state machine and the identity from the verified request
  are independent of slots and cannot be configured.

Slots of the four core modules:

| Slot | Module | Default | Setting | Tools |
|---|---|---|---|---|
| `base` | core | lowest role | - | all member tools |
| `approver` | core | highest role | `applications.approver_role` | list/get/approve/reject/clarify/bulk approve applications |
| `member_admin` | members | `approver` | `modules.members.admin_role` | `search_members`, `update_member` |
| `activity_confirmer` | certificates | second-lowest role | `modules.certificates.confirmer_role` | `list_team_activities`, `confirm_activity` |
| `organizer` | events | `approver` | `modules.events.organizer_role` | `create_event`, `list_registrations` |

Per-kind approver roles (for example a different approver for certificates than for
data changes) are deliberately out of scope for v1.

## Consequences

* Groups name their roles freely; a hierarchy needs at least two roles because the
  privileged slots must sit above the lowest one.
* `ModuleManifest.required_roles` holds `RoleSlot` entries and `ToolSpec.min_role` names
  a slot (breaking change for module authors before 1.0).
* The permission matrix derives expected permissions from the resolved slots and runs
  for the Musterverein and for a group with different role names and changed slots.
* `campus-agent doctor` prints the slot mapping.
