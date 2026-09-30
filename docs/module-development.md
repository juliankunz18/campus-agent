# Developing a module

A module adds features without changing the core. It is a Python package that
registers a manifest under the entry point group `campus_agent.modules`. It can live in
this repository (`modules/<name>/`) or be published separately.

## Layout

```text
modules/example/
├── pyproject.toml
├── src/campus_agent_example/
│   ├── __init__.py
│   ├── manifest.py          # ModuleManifest, lists, settings model
│   ├── tools.py             # input models and handlers
│   └── locales/
│       ├── de/messages.yaml
│       └── en/messages.yaml
└── tests/
```

```toml
# pyproject.toml
[project]
name = "campus-agent-example"
dependencies = ["campus-agent-core"]

[project.entry-points."campus_agent.modules"]
example = "campus_agent_example.manifest:manifest"
```

The entry point name must equal the manifest name.

## Rules

* Import only from `campus_agent_core.ports`. Never import adapters
  (`campus_agent_integrations`), apps, other modules or SDKs.
* Tool names are English snake_case. Every tool has a class (`read`, `draft`,
  `commit`), a minimum role and an input model derived from `ToolInput`.
* **No tool takes a user ID or role.** The caller is `context.user`, taken from the
  verified request. The manifest validation rejects identity parameters, and input
  models reject unknown arguments.
* Anything binding is a `commit` tool: it runs only after the person confirms a card.
* Return only the fields the use case needs, plus a short `summary`. Sensitive fields
  (bank details, birth date, address) never reach the model.
* User-visible texts live in the locale files, German first.

## Manifest and tools

```python
from pydantic import BaseModel, ConfigDict, Field

from campus_agent_core.ports import (
    APPROVER_SLOT,
    BASE_SLOT,
    ModuleManifest,
    RoleSlot,
    ToolClass,
    ToolContext,
    ToolInput,
    ToolResult,
    ToolSpec,
)


class ListThingsInput(ToolInput):
    query: str = Field(min_length=2, max_length=100)


async def list_things(context: ToolContext, params: ListThingsInput) -> ToolResult:
    # context.user is the verified caller; context.module_config holds the settings
    return ToolResult(summary="2 Einträge", data={"items": []})


class ExampleSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    owner_role: str | None = None  # overrides the "owner" role slot


manifest = ModuleManifest(
    name="example",
    version="0.1.0",
    required_roles=(
        # Privileged by default: may never resolve to the lowest role.
        RoleSlot(name="owner", inherits=APPROVER_SLOT, setting="owner_role"),
    ),
    locale_package="campus_agent_example",
    prompt_fragments=("prompt.example",),
    config_model=ExampleSettings,
    tools=(
        ToolSpec(
            name="list_things",
            tool_class=ToolClass.READ,
            min_role=BASE_SLOT,  # everybody; use "owner" for privileged tools
            input_model=ListThingsInput,
            handler=list_things,
        ),
    ),
)
```

## Role slots

Tools never name role IDs, because every group names its roles differently. A tool's
`min_role` is a role slot (ADR 0019):

* core slots, always available: `base` (lowest role) and `approver` (decides on
  applications, `applications.approver_role`, default: highest role);
* own slots, declared in `required_roles` with either `default` (`lowest`,
  `above_lowest`, `highest`) or `inherits` (another slot), and optionally a `setting`
  field of the module settings that overrides it.

Slots are privileged unless declared with `privileged=False`. Use privileged slots for
every tool that shows other people's data or acts for others; the loader refuses to map
them to the lowest role. `campus-agent doctor` prints the resulting mapping.

Declare SharePoint lists with `ListSpec` and `ListColumn`; `campus-agent provision`
creates them in dependency order (lookup targets first).

## Texts

```yaml
# locales/de/messages.yaml
tools:
  list_things:
    description: >-
      Listet Dinge auf. Passt, wenn … ; nicht für … .
    params:
      query: Suchbegriff.
prompt:
  example: Ein Satz, den das Modell über dieses Modul wissen muss.
```

Every tool description says in one sentence when the tool fits and when it does not.
The loader refuses to start if a description, parameter text or prompt fragment is
missing in any supported language.

## Settings

Enable the module and pass its settings in `campus-agent.yaml`:

```yaml
modules:
  example:
    owner_role: board
```

## Tests

```python
from campus_agent_core.modules import ToolRegistry, load_modules
from campus_agent_core.testing import catalog_for, minimal_config

config = minimal_config("modules:\n  example: {}\n")
```

Use the fakes from `campus_agent_integrations.fakes` for loop tests. The repository-wide
permission matrix (`tests/test_permission_matrix.py`) automatically covers every tool of
every installed module.
