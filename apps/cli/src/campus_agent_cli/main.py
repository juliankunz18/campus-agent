"""``campus-agent`` command line: init | provision | doctor."""

from __future__ import annotations

import os
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from campus_agent_core.config import (
    CampusAgentConfig,
    ConfigError,
    RuntimeSettings,
    load_config,
)
from campus_agent_core.modules import (
    LoadedModule,
    ModuleLoadError,
    ToolRegistry,
    discover_manifests,
    load_modules,
)

app = typer.Typer(
    help="Set up and check a campus-agent installation.",
    no_args_is_help=True,
    add_completion=False,
)

# Files copied by `init`: packaged source -> target path relative to the directory.
EXAMPLE_FILES = {
    "campus-agent.yaml": "campus-agent.yaml",
    "env.example": ".env.example",
    "templates/bescheinigung.html.j2": "templates/bescheinigung.html.j2",
}

ConfigOption = Annotated[Path, typer.Option("--config", "-c", help="Path to campus-agent.yaml.")]
EnvFileOption = Annotated[
    Path | None,
    typer.Option("--env-file", help="KEY=VALUE file with the variables used in the config."),
]

OK, FAIL, SKIP = "[ok]  ", "[fail]", "[skip]"


@app.command()
def init(
    directory: Annotated[Path, typer.Argument(help="Target directory.")] = Path("."),
    force: Annotated[bool, typer.Option(help="Overwrite existing files.")] = False,
) -> None:
    """Copy the Musterverein example configuration as a starting point."""
    source = resources.files("campus_agent_cli").joinpath("example")
    targets = {directory / target: source_name for source_name, target in EXAMPLE_FILES.items()}
    existing = [path for path in targets if path.exists()]
    if existing and not force:
        for path in existing:
            typer.echo(f"exists: {path}", err=True)
        typer.echo("Nothing copied. Use --force to overwrite.", err=True)
        raise typer.Exit(1)

    for target, source_name in targets.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_read(source.joinpath(*source_name.split("/"))), encoding="utf-8")
        typer.echo(f"created {target}")
    typer.echo(
        "\nNext steps:\n"
        "  1. Adapt campus-agent.yaml to your group.\n"
        "  2. Copy .env.example to .env and fill in your IDs (never commit .env).\n"
        "  3. Run `campus-agent doctor --env-file .env`."
    )


@app.command()
def provision(
    config: ConfigOption = Path("campus-agent.yaml"),
    env_file: EnvFileOption = None,
    apply: Annotated[
        bool, typer.Option("--apply", help="Create the lists (not implemented yet).")
    ] = False,
) -> None:
    """Show (and later create) the SharePoint lists of all active modules."""
    loaded_config, modules = _load_or_exit(config, env_file)
    # Imported here so that `init` and `doctor` work without the Graph SDK being loaded.
    from campus_agent_integrations.sharepoint import plan_lists

    try:
        plan = plan_lists(modules)
    except ValueError as error:
        typer.echo(f"{FAIL} {error}", err=True)
        raise typer.Exit(1) from error

    typer.echo(f"SharePoint site: {loaded_config.sharepoint.site_id}")
    typer.echo(f"Planned lists and libraries ({len(plan)}):")
    for item in plan:
        columns = ", ".join(column.name for column in item.spec.columns) or "-"
        typer.echo(
            f"  - {item.spec.name} ({item.spec.kind.value}, module {item.module}): {columns}"
        )

    if apply:
        typer.echo(
            "\nProvisioning against SharePoint is not implemented yet. Nothing was changed.",
            err=True,
        )
        raise typer.Exit(2)
    typer.echo("\nDry run only. Nothing was changed.")


@app.command()
def doctor(
    config: ConfigOption = Path("campus-agent.yaml"),
    env_file: EnvFileOption = None,
) -> None:
    """Check configuration, modules, texts and (later) tenant permissions."""
    env = _environment(env_file)
    failures = 0

    try:
        settings = RuntimeSettings.model_validate(env)
        typer.echo(f"{OK} environment: CAMPUS_AGENT_ENV={settings.env.value}")
    except ValidationError as error:
        failures += 1
        typer.echo(f"{FAIL} environment: {_first_error(error)}")

    try:
        loaded_config = load_config(config, env=env)
        typer.echo(f"{OK} configuration: {config} ({loaded_config.group.name})")
    except ConfigError as error:
        typer.echo(f"{FAIL} configuration: {config}")
        for issue in error.issues:
            typer.echo(f"         {issue}")
        raise typer.Exit(1) from error

    roles = " < ".join(loaded_config.role_hierarchy().roles)
    typer.echo(f"{OK} roles: {roles}")

    try:
        modules = load_modules(loaded_config, discover_manifests())
    except ModuleLoadError as error:
        typer.echo(f"{FAIL} modules")
        for issue in error.issues:
            typer.echo(f"         {issue}")
        raise typer.Exit(1) from error
    registry = ToolRegistry(
        modules, loaded_config.role_hierarchy(), language=loaded_config.group.language
    )
    names = ", ".join(f"{m.name} {m.manifest.version}" for m in modules)
    typer.echo(f"{OK} modules: {names}")
    typer.echo(f"{OK} tools and texts: {len(registry.all())} tools")

    failures += _check_template(loaded_config, config)

    for check in (
        "tenant and app registration",
        "Graph permissions (Sites.Selected)",
        "SharePoint lists",
        "Azure OpenAI deployment",
    ):
        typer.echo(f"{SKIP} {check}: not implemented yet")

    if failures:
        raise typer.Exit(1)


def _check_template(config: CampusAgentConfig, config_path: Path) -> int:
    settings = config.modules.get("certificates")
    if settings is None:
        return 0
    template = settings.get("template")
    if not isinstance(template, str) or template.startswith("builtin:"):
        typer.echo(f"{OK} certificate template: built-in")
        return 0
    path = config_path.parent / template
    if path.is_file():
        typer.echo(f"{OK} certificate template: {path}")
        return 0
    typer.echo(f"{FAIL} certificate template not found: {path}")
    return 1


def _load_or_exit(
    config: Path, env_file: Path | None
) -> tuple[CampusAgentConfig, list[LoadedModule]]:
    env = _environment(env_file)
    try:
        loaded = load_config(config, env=env)
        return loaded, load_modules(loaded, discover_manifests())
    except (ConfigError, ModuleLoadError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error


def _environment(env_file: Path | None) -> dict[str, str]:
    env = dict(os.environ)
    if env_file is not None:
        env.update(read_env_file(env_file))
    return env


def read_env_file(path: Path) -> dict[str, str]:
    """Minimal KEY=VALUE parser (comments and blank lines ignored, quotes stripped)."""
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip().removeprefix("export ").strip()] = value.strip().strip("\"'")
    return values


def _first_error(error: ValidationError) -> str:
    item = error.errors()[0]
    location = ".".join(str(part) for part in item["loc"])
    return f"{location}: {item['msg']}" if location else item["msg"]


def _read(resource: Traversable) -> str:
    return resource.read_text(encoding="utf-8")
