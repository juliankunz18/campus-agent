# Security policy

campus-agent processes personal data of association members. We take reports seriously.

## Supported versions

The project is in early development and has no release yet. Security fixes land on
`main`. Once releases exist, the latest minor version receives fixes.

## Reporting a vulnerability

Please **do not open a public issue**. Report privately through GitHub:
[Report a vulnerability](https://github.com/juliankunz18/campus-agent/security/advisories/new)
(Security tab → "Report a vulnerability").

Please include:

* affected component (core, module, bot, MCP server, CLI, infrastructure) and version
  or commit,
* steps to reproduce, ideally with the fictional Musterverein example,
* impact, for example "a member can read another member's data".

Never include real member data, tokens or tenant IDs in a report.

The maintainers are volunteers. We aim to acknowledge reports within a week and will
coordinate a fix and disclosure with you, but cannot guarantee response times.

## Security model in short

* The user ID comes from the verified Teams/Entra token, never from the model or a tool
  argument; the role is derived from Entra groups on the server.
* The model only sees the tools of the user's role; every tool checks the role again.
* Binding actions need a click on a confirmation card and run without the model, with
  an idempotency key; decisions on applications follow the four-eyes principle.
* The MCP server is not publicly reachable and is the only component with write access
  to SharePoint (`Sites.Selected` on the group's site only).
* Content from documents and tool results is treated as data, not instructions.
* Secrets live in Azure Key Vault or are replaced by Managed Identity; CI deploys with
  OIDC. gitleaks runs in CI and as a pre-commit hook.
