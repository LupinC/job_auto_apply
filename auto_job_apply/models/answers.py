from __future__ import annotations

from datetime import datetime, UTC

from pydantic import BaseModel, Field


class AnswerEntry(BaseModel):
    value: str | bool | int | float | None
    sensitive: bool = False
    user_approved_reuse: bool = False
    updated_at: str | None = None


class AnswerBank(BaseModel):
    answers: dict[str, AnswerEntry] = Field(default_factory=dict)

    def upsert(self, key: str, entry: AnswerEntry) -> None:
        entry.updated_at = datetime.now(UTC).isoformat()
        self.answers[key] = entry

    def get_value(self, key: str) -> str | bool | int | float | None:
        entry = self.answers.get(key)
        if not entry:
            return None
        return entry.value
