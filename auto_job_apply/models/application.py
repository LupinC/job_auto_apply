from __future__ import annotations

from pydantic import BaseModel


class ApplicationAttempt(BaseModel):
    ts: str
    company: str | None = None
    title: str
    url: str
    status: str
    resume_path: str | None = None
    cover_letter_path: str | None = None
    screenshot_path: str | None = None
    reason: str | None = None
    confirmation_text: str | None = None
