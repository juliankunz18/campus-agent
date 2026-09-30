"""Pydantic model of ``campus-agent.yaml``."""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

from campus_agent_core.domain.applications import DEFAULT_CLARIFICATION_DEADLINE
from campus_agent_core.domain.roles import RoleHierarchy

type Slug = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]
type NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GroupConfig(_Strict):
    name: NonEmpty
    short_name: Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9-]*$")]
    language: Literal["de", "en"] = "de"


class RoleSource(StrEnum):
    ALL_TENANT_USERS = "all_tenant_users"


class RoleConfig(_Strict):
    """A role. Exactly one of ``source`` or ``entra_group`` defines its members."""

    id: Slug
    label: NonEmpty
    source: RoleSource | None = None
    entra_group: NonEmpty | None = None

    @model_validator(mode="after")
    def _one_membership_source(self) -> Self:
        if (self.source is None) == (self.entra_group is None):
            raise ValueError("set exactly one of 'source' or 'entra_group'")
        return self


class SharePointConfig(_Strict):
    site_id: NonEmpty


class LLMConfig(_Strict):
    deployment: NonEmpty


class AgentLimits(_Strict):
    """Limits of the agent loop. Start values from the design; tune during the pilot.

    Durations accept ISO 8601 (``PT30S``) or seconds.
    """

    max_tool_rounds: int = Field(default=6, ge=1, le=20)
    llm_timeout: timedelta = Field(default=timedelta(seconds=30), gt=timedelta(0))
    history_max_messages: int = Field(default=10, ge=0, le=100)
    history_max_age: timedelta = Field(default=timedelta(hours=24), gt=timedelta(0))
    role_cache_ttl: timedelta = Field(default=timedelta(minutes=5), ge=timedelta(0))
    rate_limit_per_hour: int = Field(default=30, ge=1)
    pending_action_ttl: timedelta = Field(default=timedelta(hours=24), gt=timedelta(0))
    tool_result_max_tokens: int = Field(default=4000, ge=100)


class ApplicationsConfig(_Strict):
    clarification_deadline: timedelta = Field(
        default=DEFAULT_CLARIFICATION_DEADLINE, gt=timedelta(0)
    )


class CampusAgentConfig(_Strict):
    """Root of ``campus-agent.yaml``."""

    group: GroupConfig
    roles: list[RoleConfig] = Field(min_length=1, description="Lowest role first.")
    sharepoint: SharePointConfig
    llm: LLMConfig
    agent: AgentLimits = AgentLimits()
    applications: ApplicationsConfig = ApplicationsConfig()
    modules: dict[Slug, dict[str, JsonValue]] = Field(
        default_factory=dict[str, dict[str, JsonValue]],
        description="Enabled modules and their settings; validated by each module.",
    )

    @field_validator("roles")
    @classmethod
    def _check_roles(cls, roles: list[RoleConfig]) -> list[RoleConfig]:
        ids = [role.id for role in roles]
        duplicates = sorted({role_id for role_id in ids if ids.count(role_id) > 1})
        if duplicates:
            raise ValueError(f"duplicate role ids: {', '.join(duplicates)}")
        if roles[0].source is None:
            raise ValueError(f"the lowest role {roles[0].id!r} must use 'source: all_tenant_users'")
        higher_with_source = [role.id for role in roles[1:] if role.source is not None]
        if higher_with_source:
            raise ValueError(
                "only the lowest role may use 'source'; use 'entra_group' for: "
                + ", ".join(higher_with_source)
            )
        return roles

    def role_hierarchy(self) -> RoleHierarchy:
        return RoleHierarchy([role.id for role in self.roles])
