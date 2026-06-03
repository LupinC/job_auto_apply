from __future__ import annotations


def submit_with_user_approval(approved: bool) -> str:
    return "submitted" if approved else "user_skipped"
