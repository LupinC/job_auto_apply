from __future__ import annotations


def wait_for_user(message: str = "Manual action required. Press Enter to continue.") -> None:
    input(message)
