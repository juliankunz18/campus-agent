# Architecture decision records

Every fundamental decision is recorded as a short ADR (context, decision,
consequences). New ADRs get the next number; a decision is changed by a new ADR that
supersedes the old one, never by rewriting history.

| No. | Decision | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-framework-first-and-private-deployments.md) | Framework first, deployments in private repositories | Accepted |
| [0003](0003-single-technology-path.md) | One technology path: Teams, SharePoint, Azure OpenAI | Accepted |
| [0004](0004-python-and-uv-workspace.md) | Python 3.12 and a uv workspace monorepo | Accepted |
| [0005](0005-own-agent-loop.md) | Own agent loop, no agent framework | Accepted |
| [0006](0006-microsoft-365-agents-sdk.md) | Microsoft 365 Agents SDK for Teams | Accepted |
| [0007](0007-mcp-server-as-single-writer.md) | MCP server as the only writer, enforcing all rules | Accepted |
| [0008](0008-tool-classes-and-confirmation-cards.md) | Tool classes and confirmation cards | Accepted |
| [0009](0009-identity-from-verified-request.md) | Identity from the verified request, roles from Entra groups | Accepted |
| [0010](0010-application-workflow-and-four-eyes.md) | Application workflow and four-eyes principle in the core | Accepted |
| [0011](0011-modules-via-entry-points.md) | Modules via entry points and manifests | Accepted |
| [0012](0012-sharepoint-and-table-storage.md) | Business data in SharePoint, runtime state in Table Storage | Accepted |
| [0013](0013-llm-behind-port.md) | Language model behind a port | Accepted |
| [0014](0014-pdf-with-jinja2-and-weasyprint.md) | Certificates as PDF from Jinja2 and WeasyPrint | Accepted |
| [0015](0015-bicep-and-github-actions-oidc.md) | Infrastructure with Bicep, CI/CD with GitHub Actions and OIDC | Accepted |
| [0016](0016-german-first-translatable-texts.md) | German first, translatable texts | Accepted |
| [0017](0017-bm25-knowledge-search.md) | Keyword search (BM25) for knowledge in the MVP | Accepted |
| [0018](0018-apache-license-and-dco.md) | Apache License 2.0 and DCO instead of a CLA | Accepted |
| [0019](0019-configurable-role-slots.md) | Configurable role slots | Accepted |
