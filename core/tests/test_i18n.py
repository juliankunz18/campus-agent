from pathlib import Path

import pytest

from campus_agent_core.i18n import SUPPORTED_LANGUAGES, Catalog, CatalogError, load_catalog


def test_core_catalog_has_the_same_keys_in_every_language():
    catalog = load_catalog("campus_agent_core")

    assert catalog.languages() == SUPPORTED_LANGUAGES
    assert catalog.keys("de") == catalog.keys("en")
    assert catalog.get("errors.NOT_FOUND", "de") == "Das habe ich nicht gefunden."


def test_nested_keys_are_flattened():
    catalog = load_catalog("campus_agent_core")

    assert catalog.has("tools.approve_application.params.application_id", "de")
    assert catalog.has("prompt.system.security", "en")


def test_falls_back_to_german():
    catalog = Catalog("test", {"de": {"a": "Hallo"}, "en": {}})

    assert catalog.get("a", "en") == "Hallo"
    with pytest.raises(KeyError, match="'b'"):
        catalog.get("b", "en")


def test_non_string_values_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    package = tmp_path / "broken_texts"
    (package / "locales" / "de").mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "locales" / "de" / "messages.yaml").write_text("a:\n  b: 3\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    with pytest.raises(CatalogError, match=r"'a.b' must be a string"):
        load_catalog("broken_texts")
