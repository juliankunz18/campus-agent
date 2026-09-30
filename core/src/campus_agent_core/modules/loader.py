"""Discover modules via entry points and validate them against the configuration."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from importlib.metadata import EntryPoint, entry_points

from pydantic import BaseModel, JsonValue, ValidationError

from campus_agent_core.config.errors import format_location
from campus_agent_core.config.schema import CampusAgentConfig
from campus_agent_core.i18n import SUPPORTED_LANGUAGES, Catalog, CatalogError, load_catalog
from campus_agent_core.modules.slots import resolve_slots
from campus_agent_core.ports.module import CORE_SLOTS, ROLES_CONTEXT_KEY, ModuleManifest

ENTRY_POINT_GROUP = "campus_agent.modules"
CORE_MODULE = "core"


class ModuleLoadError(Exception):
    """Modules could not be loaded. ``issues`` lists every problem."""

    def __init__(self, issues: Sequence[str]) -> None:
        self.issues: tuple[str, ...] = tuple(issues)
        lines = "\n".join(f"  - {issue}" for issue in self.issues)
        super().__init__(f"cannot load modules:\n{lines}")


@dataclass(frozen=True)
class LoadedModule:
    """A validated, active module with its texts and parsed settings."""

    manifest: ModuleManifest
    catalog: Catalog
    settings: BaseModel | None = None
    raw_settings: Mapping[str, JsonValue] = field(default_factory=dict[str, JsonValue])
    slot_roles: Mapping[str, str] = field(default_factory=dict[str, str])
    """Role ID per role slot usable by this module (own slots and core slots)."""

    @property
    def name(self) -> str:
        return self.manifest.name


def discover_manifests(
    candidates: Iterable[EntryPoint] | None = None,
) -> dict[str, ModuleManifest]:
    """Load every manifest registered under ``campus_agent.modules``."""
    found = entry_points(group=ENTRY_POINT_GROUP) if candidates is None else candidates
    manifests: dict[str, ModuleManifest] = {}
    issues: list[str] = []
    for entry_point in found:
        try:
            loaded: object = entry_point.load()
            manifest = loaded if isinstance(loaded, ModuleManifest) else _call(loaded)
        except Exception as error:  # a broken third-party module must not hide the others
            issues.append(f"entry point {entry_point.name!r}: {error}")
            continue
        if manifest is None:
            issues.append(f"entry point {entry_point.name!r}: does not provide a ModuleManifest")
        elif manifest.name != entry_point.name:
            issues.append(f"entry point {entry_point.name!r}: manifest is named {manifest.name!r}")
        elif manifest.name in manifests:
            issues.append(f"module {manifest.name!r} is registered more than once")
        else:
            manifests[manifest.name] = manifest
    if issues:
        raise ModuleLoadError(issues)
    return manifests


def load_modules(
    config: CampusAgentConfig,
    manifests: Mapping[str, ModuleManifest],
    *,
    catalog_loader: Callable[[str], Catalog] = load_catalog,
) -> list[LoadedModule]:
    """Validate and return the core module plus every module enabled in the config.

    Role slots are resolved here: first the core slots, then each module's own slots.
    """
    hierarchy = config.role_hierarchy()
    roles = hierarchy.roles
    names = [CORE_MODULE, *(name for name in config.modules if name != CORE_MODULE)]
    issues: list[str] = []
    loaded: list[LoadedModule] = []
    tool_owner: dict[str, str] = {}
    core_slots: dict[str, str] = {}

    for name in names:
        manifest = manifests.get(name)
        if manifest is None:
            available = ", ".join(sorted(manifests)) or "none"
            issues.append(f"modules.{name}: module is not installed (available: {available})")
            continue

        for tool in manifest.tools:
            owner = tool_owner.setdefault(tool.name, name)
            if owner != name:
                issues.append(f"modules.{name}: tool {tool.name!r} is already defined by {owner!r}")

        try:
            catalog = catalog_loader(manifest.locale_package)
        except (CatalogError, ModuleNotFoundError) as error:
            issues.append(f"modules.{name}: cannot load texts: {error}")
            continue
        issues.extend(f"modules.{name}: {issue}" for issue in _missing_texts(manifest, catalog))

        # The core is configured through the top-level "applications" section.
        is_core = name == CORE_MODULE
        prefix = "applications." if is_core else f"modules.{name}."
        raw_settings = _core_settings(config) if is_core else config.modules.get(name, {})
        settings, settings_issues = _validate_settings(manifest, raw_settings, roles)
        issues.extend(f"{prefix}{issue}" for issue in settings_issues)

        slot_roles, slot_issues = resolve_slots(
            manifest, raw_settings, hierarchy, inherited={} if is_core else core_slots
        )
        issues.extend(f"{prefix}{issue}" for issue in slot_issues)
        if is_core:
            core_slots = {slot: slot_roles[slot] for slot in CORE_SLOTS if slot in slot_roles}
        loaded.append(LoadedModule(manifest, catalog, settings, raw_settings, slot_roles))

    if issues:
        raise ModuleLoadError(issues)
    return loaded


def _core_settings(config: CampusAgentConfig) -> dict[str, JsonValue]:
    approver = config.applications.approver_role
    return {} if approver is None else {"approver_role": approver}


def _call(factory: object) -> ModuleManifest | None:
    if callable(factory):
        result: object = factory()
        if isinstance(result, ModuleManifest):
            return result
    return None


def _missing_texts(manifest: ModuleManifest, catalog: Catalog) -> list[str]:
    required: list[str] = []
    for tool in manifest.tools:
        required.append(tool.description_key)
        required.extend(tool.parameter_key(field) for field in tool.input_model.model_fields)
    required.extend(manifest.prompt_fragments)
    return [
        f"missing text {key!r} for language {language!r}"
        for language in SUPPORTED_LANGUAGES
        for key in required
        if not catalog.has(key, language)
    ]


def _validate_settings(
    manifest: ModuleManifest, raw: Mapping[str, JsonValue], roles: tuple[str, ...]
) -> tuple[BaseModel | None, list[str]]:
    if manifest.config_model is None:
        if raw:
            return None, [f"{key}: module takes no settings" for key in raw]
        return None, []
    try:
        settings = manifest.config_model.model_validate(
            dict(raw), context={ROLES_CONTEXT_KEY: roles}
        )
    except ValidationError as error:
        return None, [f"{format_location(item['loc'])}: {item['msg']}" for item in error.errors()]
    return settings, []
