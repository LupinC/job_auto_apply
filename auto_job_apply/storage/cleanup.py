from __future__ import annotations

from pathlib import Path
import os
import stat
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class ClearDataResult:
    blocked_paths: list[str]
    used_windows_fallback: bool


def clear_data_dir(data_dir: Path) -> ClearDataResult:
    """Best-effort recursive delete.

    Returns a list of paths that could not be removed (for example, locked by
    another process on Windows).
    """
    blocked: list[str] = []
    used_windows_fallback = False
    if not data_dir.exists():
        return ClearDataResult(blocked_paths=[], used_windows_fallback=False)

    for root, dirs, files in os.walk(data_dir, topdown=False):
        root_path = Path(root)

        for filename in files:
            file_path = root_path / filename
            if not file_path.exists():
                continue
            try:
                _unlink_file(file_path)
            except OSError:
                blocked.append(str(file_path))

        for dirname in dirs:
            dir_path = root_path / dirname
            if not dir_path.exists():
                continue
            try:
                dir_path.rmdir()
            except OSError:
                blocked.append(str(dir_path))

    try:
        data_dir.rmdir()
    except OSError:
        blocked.append(str(data_dir))

    if blocked and os.name == "nt":
        used_windows_fallback = True
        subprocess.run(
            ["cmd", "/c", "rd", "/s", "/q", str(data_dir)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    # Return only paths that still exist after all delete attempts.
    return ClearDataResult(
        blocked_paths=[path for path in blocked if Path(path).exists()],
        used_windows_fallback=used_windows_fallback,
    )


def _unlink_file(file_path: Path) -> None:
    try:
        file_path.unlink()
        return
    except PermissionError:
        # Retry after forcing write bit for read-only files.
        mode = file_path.stat().st_mode
        file_path.chmod(mode | stat.S_IWRITE)
        file_path.unlink()
