# Infrastructure

Planned content (see ADR 0015), not implemented yet:

| Path | Content |
|---|---|
| `main.bicep` | Container Apps environment with bot (external ingress) and MCP server (internal ingress only), Azure OpenAI deployment, Storage account (Table Storage), Key Vault, Log Analytics, user-assigned managed identities |
| `azuredeploy.json` | "Deploy to Azure" template compiled from Bicep for new groups |
| `teams/manifest.json` | Teams app manifest template (bot ID and names as parameters) |
| `parameters.example.json` | Fictional example parameters |

Group-specific parameters (`parameters.prod.json`) belong in the group's private
deployment repository, never here.

Principles:

* Managed Identity for Azure OpenAI, Table Storage, Key Vault and Graph; no secrets in
  code, images or GitHub.
* The MCP server is reachable only from the bot backend.
* Graph permission `Sites.Selected` with write access to the group's own site only.
* GitHub Actions deploy with OIDC federation, never with stored Azure credentials.
