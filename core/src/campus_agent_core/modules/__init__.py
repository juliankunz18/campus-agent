"""Module system: manifests are declared in ``ports.module``, loaded and filtered here."""

from campus_agent_core.modules.loader import (
    CORE_MODULE,
    ENTRY_POINT_GROUP,
    LoadedModule,
    ModuleLoadError,
    discover_manifests,
    load_modules,
)
from campus_agent_core.modules.registry import RegisteredTool, ToolRegistry

__all__ = [
    "CORE_MODULE",
    "ENTRY_POINT_GROUP",
    "LoadedModule",
    "ModuleLoadError",
    "RegisteredTool",
    "ToolRegistry",
    "discover_manifests",
    "load_modules",
]
