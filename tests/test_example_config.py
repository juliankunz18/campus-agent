"""The Musterverein example must always validate against the current schema."""

from campus_agent_core.modules import discover_manifests, load_modules
from tests.helpers import EXAMPLE, example_config


def test_musterverein_config_validates_with_example_env():
    config = example_config()

    assert config.group.short_name == "musterverein"
    assert config.role_hierarchy().roles == ("member", "team_lead", "board")
    assert set(config.modules) == {"members", "certificates", "knowledge", "events"}


def test_musterverein_module_settings_validate():
    config = example_config()

    loaded = {module.name: module for module in load_modules(config, discover_manifests())}

    assert set(loaded) == {"core", "members", "certificates", "knowledge", "events"}
    certificates = loaded["certificates"].settings
    assert certificates is not None
    assert certificates.model_dump()["number_format"] == "MUSTER-{year}-{seq:03d}"


def test_certificate_template_referenced_by_example_exists():
    template = example_config().modules["certificates"]["template"]

    assert isinstance(template, str)
    assert (EXAMPLE / template).is_file()
