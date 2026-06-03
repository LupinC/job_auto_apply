from __future__ import annotations

from pydantic import BaseModel


class LlmMappingDecision(BaseModel):
    mapped_key: str | None = None
    answer: str | bool | int | float | None = None
    confidence: float
    requires_user_review: bool = False
    reason: str | None = None
