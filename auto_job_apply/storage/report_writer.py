from __future__ import annotations

from datetime import datetime
from pathlib import Path


def write_report(
    reports_dir: Path,
    title: str,
    requested: int,
    successful: int,
    skipped: int,
    failed: int,
    needs_user: int,
    rows: list[dict[str, str]],
) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out = reports_dir / f"report_{ts}.md"

    lines = [
        "# Auto Job Apply Report",
        "",
        f"Target title: {title}",
        f"Requested submissions: {requested}",
        f"Successful submissions: {successful}",
        f"Skipped: {skipped}",
        f"Failed: {failed}",
        f"Needs user review: {needs_user}",
        "",
        "| Company | Title | URL | Status | Notes |",
        "|---|---|---|---|---|",
    ]

    for row in rows:
        lines.append(
            f"| {row.get('company', '')} | {row.get('title', '')} | {row.get('url', '')} | {row.get('status', '')} | {row.get('notes', '')} |"
        )

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
