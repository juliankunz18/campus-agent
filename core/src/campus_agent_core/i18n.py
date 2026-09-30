"""Translatable texts.

Every package keeps its user-visible texts (tool descriptions, prompt fragments, card
texts, error messages) in ``locales/<lang>/messages.yaml``. Nested YAML keys are
flattened to dotted keys such as ``tools.get_my_profile.description``.
"""

from __future__ import annotations

from collections.abc import Mapping
from importlib import resources
from types import MappingProxyType
from typing import Final, cast

import yaml

SUPPORTED_LANGUAGES: Final = ("de", "en")
DEFAULT_LANGUAGE: Final = "de"


class CatalogError(ValueError):
    pass


class Catalog:
    """Messages of one package, per language."""

    __slots__ = ("_messages", "package")

    def __init__(self, package: str, messages: Mapping[str, Mapping[str, str]]) -> None:
        self.package = package
        self._messages: Mapping[str, Mapping[str, str]] = MappingProxyType(
            {lang: MappingProxyType(dict(texts)) for lang, texts in messages.items()}
        )

    def languages(self) -> tuple[str, ...]:
        return tuple(self._messages)

    def keys(self, language: str) -> frozenset[str]:
        return frozenset(self._messages.get(language, {}))

    def has(self, key: str, language: str) -> bool:
        return key in self._messages.get(language, {})

    def get(self, key: str, language: str) -> str:
        """Return the text, falling back to the default language."""
        for lang in (language, DEFAULT_LANGUAGE):
            text = self._messages.get(lang, {}).get(key)
            if text is not None:
                return text
        raise KeyError(f"{self.package}: no text for {key!r} in {language!r}")


def load_catalog(package: str) -> Catalog:
    """Load ``<package>/locales/<lang>/messages.yaml`` for every supported language."""
    root = resources.files(package).joinpath("locales")
    messages: dict[str, dict[str, str]] = {}
    for language in SUPPORTED_LANGUAGES:
        path = root.joinpath(language, "messages.yaml")
        if not path.is_file():
            continue
        data: object = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data is None:
            messages[language] = {}
            continue
        if not isinstance(data, dict):
            raise CatalogError(f"{package}/locales/{language}: expected a mapping")
        messages[language] = _flatten(cast(dict[object, object], data), prefix="", origin=package)
    return Catalog(package, messages)


def _flatten(data: Mapping[object, object], *, prefix: str, origin: str) -> dict[str, str]:
    flat: dict[str, str] = {}
    for key, value in data.items():
        full_key = f"{prefix}{key}"
        if isinstance(value, dict):
            nested = cast(dict[object, object], value)
            flat.update(_flatten(nested, prefix=f"{full_key}.", origin=origin))
        elif isinstance(value, str):
            flat[full_key] = value.strip()
        else:
            raise CatalogError(f"{origin}: {full_key!r} must be a string")
    return flat
