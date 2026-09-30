"""Settings of the certificates module under ``modules.certificates``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from campus_agent_core.ports import RoleRef

DEFAULT_TEMPLATE = "builtin:certificate.de.html.j2"


class CertificatesSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    approver_role: RoleRef = "board"
    template: str = Field(
        default=DEFAULT_TEMPLATE,
        description="Path relative to the configuration file, or the built-in template.",
    )
    number_format: str = Field(
        default="{year}-{seq:03d}",
        description="Python format string with the fields 'year' and 'seq'.",
    )

    @field_validator("number_format")
    @classmethod
    def _formattable(cls, value: str) -> str:
        if "{seq" not in value:
            raise ValueError("number_format must contain '{seq}'")
        try:
            value.format(year=2000, seq=1)
        except (KeyError, IndexError, ValueError) as error:
            raise ValueError(f"invalid number_format: {error}") from error
        return value
