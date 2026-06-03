from __future__ import annotations


def page_is_blocked(text: str) -> bool:
    lower = text.lower()
    blockers = ["captcha", "multi-factor", "mfa", "sign in", "login"]
    return any(token in lower for token in blockers)
