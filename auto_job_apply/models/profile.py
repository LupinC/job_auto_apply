from __future__ import annotations

from pydantic import BaseModel, Field


class Profile(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    skills: list[str] = Field(default_factory=list)
    years_experience: float | None = None
    education: list[dict] = Field(default_factory=list)
    experience: list[dict] = Field(default_factory=list)
