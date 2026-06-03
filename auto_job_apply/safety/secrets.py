from __future__ import annotations

import re

API_KEY_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9]{10,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
]


def mask_api_key(value: str | None) -> str | None:
    if not value:
        return value
    if len(value) <= 8:
        return "****"
    return f"{value[:3]}...{value[-4:]}"


def redact_text(text: str) -> str:
    redacted = text
    for pattern in API_KEY_PATTERNS:
        redacted = pattern.sub(lambda m: mask_api_key(m.group(0)) or "****", redacted)
    return redacted
