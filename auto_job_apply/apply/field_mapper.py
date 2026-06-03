from __future__ import annotations

from auto_job_apply.constants import SENSITIVE_ANSWER_KEYS

LABEL_TO_KEY = {
    "first name": "profile.first_name",
    "given name": "profile.first_name",
    "last name": "profile.last_name",
    "family name": "profile.last_name",
    "surname": "profile.last_name",
    "email": "profile.email",
    "email address": "profile.email",
    "phone": "profile.phone",
    "mobile": "profile.phone",
    "telephone": "profile.phone",
    "linkedin": "profile.linkedin",
    "linkedin profile": "profile.linkedin",
    "github": "profile.github",
    "github profile": "profile.github",
    "website": "profile.portfolio",
    "portfolio": "profile.portfolio",
    "require sponsorship": "answer_bank.needs_sponsorship",
    "work authorization": "answer_bank.work_authorization",
}


def map_field_label(label: str) -> str | None:
    normalized = " ".join(label.lower().strip().replace("?", "").split())
    for alias, mapped in LABEL_TO_KEY.items():
        if alias in normalized:
            return mapped
    return None


def is_sensitive_mapping(mapped_key: str | None) -> bool:
    if not mapped_key:
        return False
    if not mapped_key.startswith("answer_bank."):
        return False
    answer_key = mapped_key.split(".", 1)[1]
    return answer_key in SENSITIVE_ANSWER_KEYS
