from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProfileCopilotAnswer(BaseModel):
    question: str = Field(min_length=1, max_length=300)
    answer: str = Field(min_length=1, max_length=4000)


class ProfileCopilotExtractRequest(BaseModel):
    answers: list[ProfileCopilotAnswer] = Field(default_factory=list, min_length=1, max_length=12)
    current_profile: dict[str, Any] = Field(default_factory=dict)
    timeout: float = Field(default=30.0, ge=5.0, le=120.0)
