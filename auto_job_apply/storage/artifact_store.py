from __future__ import annotations

from pathlib import Path


def safe_join(base: Path, relative: str) -> Path:
    target = (base / relative).resolve()
    base_resolved = base.resolve()
    if base_resolved not in [target, *target.parents]:
        raise ValueError("Path traversal detected")
    return target
