from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from campus_agent_certificates import tools
from campus_agent_certificates.manifest import manifest
from campus_agent_certificates.settings import CertificatesSettings
from campus_agent_core.ports import ToolContext, UserContext

CONTEXT = ToolContext(
    user=UserContext(user_id="user-1", role="member"), now=datetime(2026, 10, 1, tzinfo=UTC)
)


def test_period_must_be_ordered():
    with pytest.raises(ValidationError, match="start must not be after end"):
        tools.CreateCertificateDraftInput(start=date(2026, 9, 1), end=date(2026, 3, 1))


def test_number_format_needs_a_sequence():
    assert CertificatesSettings(number_format="X-{year}-{seq:04d}").number_format.startswith("X")

    with pytest.raises(ValidationError, match="must contain"):
        CertificatesSettings(number_format="{year}")
    with pytest.raises(ValidationError, match="invalid number_format"):
        CertificatesSettings(number_format="{seq}-{unknown}")


def test_activity_confirmation_uses_its_own_role_slot():
    (slot,) = manifest.required_roles

    assert slot.name == "activity_confirmer"
    assert slot.setting == "confirmer_role"
    assert slot.privileged
    assert {t.min_role for t in manifest.tools if t.name.endswith("team_activities")} == {
        "activity_confirmer"
    }


def test_approval_is_configured_in_the_core_not_here():
    with pytest.raises(ValidationError, match="approver_role"):
        CertificatesSettings.model_validate({"approver_role": "board"})


def test_builtin_template_is_packaged():
    from importlib import resources

    template = resources.files("campus_agent_certificates").joinpath(
        "templates", "certificate.de.html.j2"
    )
    assert "Engagementbescheinigung" in template.read_text(encoding="utf-8")


@pytest.mark.parametrize("spec", manifest.tools, ids=lambda spec: spec.name)
async def test_handlers_are_stubs(spec):
    with pytest.raises(NotImplementedError, match=spec.name):
        await spec.handler(CONTEXT, spec.input_model.model_construct())
