from __future__ import annotations

from pathlib import Path

from auto_job_apply.storage.jsonl_store import append_jsonl, read_jsonl


def test_jsonl_append_preserves_existing_lines(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    append_jsonl(path, {"event": "one"})
    append_jsonl(path, {"event": "two"})

    rows = read_jsonl(path)
    assert [r["event"] for r in rows] == ["one", "two"]
