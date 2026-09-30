"""Wiring of the agent loop for the bot backend."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from campus_agent_core.agent import PROMPT_VERSION, AgentLoop, ToolPolicy, build_system_prompt
from campus_agent_core.config import CampusAgentConfig
from campus_agent_core.domain.user import UserContext
from campus_agent_core.i18n import load_catalog
from campus_agent_core.modules import LoadedModule, ToolRegistry
from campus_agent_core.ports.llm import LLMProvider
from campus_agent_core.ports.tools import ToolExecutor


@dataclass(frozen=True)
class BotRuntime:
    config: CampusAgentConfig
    modules: list[LoadedModule]
    registry: ToolRegistry
    policy: ToolPolicy
    loop: AgentLoop

    @property
    def prompt_version(self) -> str:
        return PROMPT_VERSION

    def system_prompt(self, user: UserContext, today: date) -> str:
        return build_system_prompt(
            core_catalog=load_catalog("campus_agent_core"),
            modules=self.modules,
            group=self.config.group,
            user=user,
            role_label=self.config.role_label(user.role),
            today=today,
        )


def build_runtime(
    config: CampusAgentConfig,
    modules: list[LoadedModule],
    *,
    llm: LLMProvider,
    executor: ToolExecutor,
) -> BotRuntime:
    """All limits (tool rounds, timeouts, pending action validity, ...) come from
    ``agent:`` in campus-agent.yaml."""
    registry = ToolRegistry(modules, config.role_hierarchy(), language=config.group.language)
    policy = ToolPolicy(registry, pending_ttl=config.agent.pending_action_ttl)
    loop = AgentLoop(
        llm=llm, registry=registry, policy=policy, executor=executor, limits=config.agent
    )
    return BotRuntime(config=config, modules=modules, registry=registry, policy=policy, loop=loop)
