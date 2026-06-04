from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
import logging
import shutil

import typer
from rich import print

from auto_job_apply.apply.runner import build_application_attempt
from auto_job_apply.config import load_config
from auto_job_apply.jobs.dedupe import dedupe_jobs
from auto_job_apply.jobs.discovery import discover_from_manual_urls
from auto_job_apply.jobs.matcher import rank_jobs
from auto_job_apply.logging_setup import safe_log, setup_logging
from auto_job_apply.models.answers import AnswerBank, AnswerEntry
from auto_job_apply.resume.parser import parse_resume
from auto_job_apply.storage.json_store import read_json, write_json
from auto_job_apply.storage.jsonl_store import append_jsonl, read_jsonl
from auto_job_apply.storage.paths import AppPaths
from auto_job_apply.storage.report_writer import write_report
from auto_job_apply.safety.secrets import mask_api_key
from auto_job_apply.safety.validation import assert_answer_entry_safe
from auto_job_apply.ui.cli import run_ui

app = typer.Typer(help="Auto Job Apply local-first v0")
logger = setup_logging()


@app.command()
def init() -> None:
    cfg = load_config()
    paths = AppPaths(cfg.data_dir)
    paths.ensure()

    if not paths.settings_json.exists():
        write_json(paths.settings_json, {"created_at": datetime.now(UTC).isoformat()})

    print(f"[green]Initialized data dir:[/green] {cfg.data_dir}")


@app.command()
def profile(resume: Path = typer.Option(..., exists=True, file_okay=True, dir_okay=False)) -> None:
    cfg = load_config()
    paths = AppPaths(cfg.data_dir)
    paths.ensure()

    profile_model = parse_resume(resume)
    write_json(paths.profile_json, profile_model.model_dump(mode="json"))
    append_jsonl(
        paths.events_jsonl,
        {
            "ts": datetime.now(UTC).isoformat(),
            "level": "info",
            "event": "profile_updated",
            "resume": str(resume),
        },
    )
    print(f"[green]Profile saved:[/green] {paths.profile_json}")


@app.command()
def answers() -> None:
    cfg = load_config()
    paths = AppPaths(cfg.data_dir)
    paths.ensure()

    existing = read_json(paths.answer_bank_json, default={})
    bank = AnswerBank(
        answers={k: AnswerEntry(**v) for k, v in existing.items()} if existing else {}
    )

    prompts = [
        ("needs_sponsorship", False, False),
        ("work_authorization", "Authorized to work in the United States", False),
        ("veteran_status", "I do not wish to answer", True),
        ("race_ethnicity", "I do not wish to answer", True),
        ("disability_status", "I do not wish to answer", True),
    ]

    for key, default_value, sensitive in prompts:
        raw = typer.prompt(f"{key} (Enter for default)", default=str(default_value))
        approved = typer.confirm(f"Allow reuse for {key}?", default=True)
        value: str | bool
        if isinstance(default_value, bool):
            value = raw.strip().lower() in {"true", "1", "yes", "y"}
        else:
            value = raw

        entry = AnswerEntry(value=value, sensitive=sensitive, user_approved_reuse=approved)
        assert_answer_entry_safe(key, entry)
        bank.upsert(key, entry)

    write_json(
        paths.answer_bank_json,
        {k: v.model_dump(mode="json") for k, v in bank.answers.items()},
    )
    print(f"[green]Answer bank saved:[/green] {paths.answer_bank_json}")


@app.command()
def discover(
    title: str = typer.Option(..., help="Target title"),
    url: list[str] = typer.Option([], help="Manual job URL, can be repeated"),
) -> None:
    cfg = load_config()
    paths = AppPaths(cfg.data_dir)
    paths.ensure()

    jobs = discover_from_manual_urls(title=title, urls=url)
    unique = dedupe_jobs(jobs)
    for job in unique:
        append_jsonl(paths.jobs_discovered_jsonl, job.model_dump(mode="json"))

    print(f"[green]Discovered jobs saved:[/green] {len(unique)}")


@app.command()
def apply(
    title: str = typer.Option(..., help="Target title"),
    max_applications: int = typer.Option(1, min=1),
    auto_approve_submit: bool = typer.Option(False, help="Test-only shortcut"),
) -> None:
    cfg = load_config()
    paths = AppPaths(cfg.data_dir)
    paths.ensure()

    discovered_rows = read_jsonl(paths.jobs_discovered_jsonl)
    if not discovered_rows:
        print("[yellow]No discovered jobs found. Run discover first.[/yellow]")
        raise typer.Exit(code=1)

    ranked = rank_jobs([_row_to_job(r) for r in discovered_rows], target_title=title)
    ranked = dedupe_jobs(ranked)

    successful = 0
    for job in ranked:
        if successful >= max_applications:
            break

        if not auto_approve_submit:
            typer.echo(f"Open URL manually in browser: {job.apply_url or job.url}")
            approved = typer.confirm("Approve submit for this application?", default=False)
        else:
            approved = True

        status = "submitted" if approved else "user_skipped"
        if status == "submitted":
            successful += 1

        attempt = build_application_attempt(
            company=job.company,
            title=job.title,
            url=str(job.url),
            status=status,
            reason=None if approved else "User declined submit",
        )
        append_jsonl(paths.applications_jsonl, attempt.model_dump(mode="json"))
        append_jsonl(
            paths.events_jsonl,
            {
                "ts": datetime.now(UTC).isoformat(),
                "level": "info",
                "event": "application_attempted",
                "company": job.company,
                "title": job.title,
                "url": str(job.url),
                "status": status,
            },
        )

    print(f"[green]Apply run complete. Successful submissions:[/green] {successful}")


@app.command()
def report(
    title: str = typer.Option(...),
    requested: int = typer.Option(..., min=1),
) -> None:
    cfg = load_config()
    paths = AppPaths(cfg.data_dir)
    paths.ensure()

    rows = read_jsonl(paths.applications_jsonl)
    successful = sum(1 for r in rows if r.get("status") == "submitted")
    skipped = sum(1 for r in rows if r.get("status") in {"user_skipped", "skipped_low_match", "skipped_duplicate"})
    failed = sum(1 for r in rows if r.get("status") == "failed")
    needs_user = sum(1 for r in rows if r.get("status") in {"needs_user", "unknown_needs_review"})

    table_rows = [
        {
            "company": r.get("company") or "",
            "title": r.get("title") or "",
            "url": r.get("url") or "",
            "status": r.get("status") or "",
            "notes": r.get("reason") or "",
        }
        for r in rows
    ]

    report_path = write_report(
        reports_dir=paths.reports_dir,
        title=title,
        requested=requested,
        successful=successful,
        skipped=skipped,
        failed=failed,
        needs_user=needs_user,
        rows=table_rows,
    )
    print(f"[green]Report saved:[/green] {report_path}")


@app.command("clear-data")
def clear_data(yes: bool = typer.Option(False, "--yes", help="Skip confirmation")) -> None:
    cfg = load_config()
    paths = AppPaths(cfg.data_dir)
    if not yes and not typer.confirm(f"Delete local data at {cfg.data_dir}?", default=False):
        raise typer.Exit(code=0)
    if paths.data_dir.exists():
        shutil.rmtree(paths.data_dir)
    print("[green]Local data cleared.[/green]")


@app.command()
def show_config() -> None:
    cfg = load_config()
    safe_log(logger, logging.INFO, "Config loaded", data_dir=cfg.data_dir, llm_api_key=mask_api_key(cfg.llm_api_key))
    print({"data_dir": str(cfg.data_dir), "llm_base_url": cfg.llm_base_url})


@app.command()
def ui(
    host: str = typer.Option("127.0.0.1", help="Streamlit host"),
    port: int = typer.Option(8501, min=1, max=65535, help="Streamlit port"),
) -> None:
    try:
        run_ui(host=host, port=port)
    except RuntimeError as exc:
        raise typer.BadParameter("Streamlit is not installed. Install with: pip install streamlit") from exc


def _row_to_job(row: dict):
    from auto_job_apply.models.job import Job

    return Job(**row)


def run() -> None:
    app()


if __name__ == "__main__":
    run()
