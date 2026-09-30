"""Runtime settings from environment variables, validated at startup."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


class RuntimeSettings(BaseSettings):
    """Settings shared by bot and MCP server.

    ``CAMPUS_AGENT_ENV`` has no default on purpose: a deployment must state where it
    runs, so that local-only switches can never be active by accident.
    """

    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    env: Environment = Field(validation_alias="CAMPUS_AGENT_ENV")
    config_path: Path = Field(
        default=Path("campus-agent.yaml"), validation_alias="CAMPUS_AGENT_CONFIG"
    )
    dev_fake_user: str | None = Field(
        default=None,
        validation_alias="DEV_FAKE_USER",
        description="Test user ID for local development without Teams. Local only.",
    )

    dev_fake_role: str | None = Field(
        default=None,
        validation_alias="DEV_FAKE_ROLE",
        description="Role of the local test user; defaults to the lowest role. Local only.",
    )

    @model_validator(mode="after")
    def _fake_user_only_locally(self) -> Self:
        for name, value in (
            ("DEV_FAKE_USER", self.dev_fake_user),
            ("DEV_FAKE_ROLE", self.dev_fake_role),
        ):
            if value and self.env is not Environment.LOCAL:
                raise ValueError(
                    f"{name} is only allowed with CAMPUS_AGENT_ENV=local "
                    f"(current: {self.env.value})"
                )
        return self
