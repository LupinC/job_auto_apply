from __future__ import annotations

from pathlib import Path


def launch_browser_session(profile_dir: Path) -> dict[str, str]:
    # v0 returns a placeholder session until full Playwright wiring is enabled.
    profile_dir.mkdir(parents=True, exist_ok=True)
    return {"status": "needs_user", "profile_dir": str(profile_dir)}
