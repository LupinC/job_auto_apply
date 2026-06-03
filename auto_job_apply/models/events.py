from __future__ import annotations

from pydantic import BaseModel


class EventRecord(BaseModel):
    ts: str
    level: str
    event: str
    details: dict[str, str | int | float | bool | None] = {}
