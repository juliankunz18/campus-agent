"""The verified identity of the person talking to the agent."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class UserContext(BaseModel):
    """Identity and role of the caller, taken from the verified request.

    The model never supplies these values: ``user_id`` comes from the validated Teams or
    Entra token, ``role`` is resolved server-side from Entra group membership.
    """

    model_config = ConfigDict(frozen=True)

    user_id: str = Field(min_length=1, description="Entra object ID of the caller.")
    first_name: str = Field(default="", description="Used for the greeting in the prompt.")
    role: str = Field(min_length=1, description="Effective role ID from the configuration.")
