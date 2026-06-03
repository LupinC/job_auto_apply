from __future__ import annotations

from datetime import datetime
from pathlib import Path


def build_screenshot_path(dir_path: Path, name: str) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = "".join(ch if ch.isalnum() else "_" for ch in name).strip("_") or "shot"
    return dir_path / f"{safe}_{stamp}.png"
