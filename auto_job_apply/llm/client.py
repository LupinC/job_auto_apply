from __future__ import annotations


def llm_enabled(api_key: str | None) -> bool:
    return bool(api_key)
