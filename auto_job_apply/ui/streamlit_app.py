from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import streamlit as st

from auto_job_apply.apply.runner import build_application_attempt
from auto_job_apply.config import load_config
from auto_job_apply.jobs.dedupe import dedupe_jobs
from auto_job_apply.jobs.discovery import discover_from_manual_urls
from auto_job_apply.jobs.matcher import rank_jobs
from auto_job_apply.models.answers import AnswerBank, AnswerEntry
from auto_job_apply.models.job import Job
from auto_job_apply.resume.parser import parse_resume
from auto_job_apply.safety.validation import assert_answer_entry_safe
from auto_job_apply.storage.json_store import read_json, write_json
from auto_job_apply.storage.jsonl_store import append_jsonl, read_jsonl
from auto_job_apply.storage.paths import AppPaths
from auto_job_apply.storage.report_writer import write_report
import shutil


def _row_to_job(row: dict) -> Job:
	return Job(**row)


def _bootstrap() -> AppPaths:
	cfg = load_config()
	paths = AppPaths(cfg.data_dir)
	paths.ensure()
	if not paths.settings_json.exists():
		write_json(paths.settings_json, {"created_at": datetime.now(UTC).isoformat()})
	return paths


def _save_profile(uploaded_file, paths: AppPaths) -> None:
	resume_path = paths.data_dir / "resumes" / uploaded_file.name
	resume_path.parent.mkdir(parents=True, exist_ok=True)
	resume_path.write_bytes(uploaded_file.getvalue())
	profile_model = parse_resume(resume_path)
	write_json(paths.profile_json, profile_model.model_dump(mode="json"))
	append_jsonl(
		paths.events_jsonl,
		{
			"ts": datetime.now(UTC).isoformat(),
			"level": "info",
			"event": "profile_updated",
			"resume": str(resume_path),
		},
	)


def _default_answer_rows(existing: dict[str, dict]) -> list[tuple[str, str, bool, bool]]:
	defaults: list[tuple[str, str | bool, bool]] = [
		("needs_sponsorship", False, False),
		("work_authorization", "Authorized to work in the United States", False),
		("veteran_status", "I do not wish to answer", True),
		("race_ethnicity", "I do not wish to answer", True),
		("disability_status", "I do not wish to answer", True),
	]

	rows: list[tuple[str, str, bool, bool]] = []
	for key, default_value, sensitive in defaults:
		current = existing.get(key, {})
		val = current.get("value", default_value)
		approved = bool(current.get("user_approved_reuse", False))
		rows.append((key, str(val), sensitive, approved))
	return rows


def _save_answers(paths: AppPaths, payload: dict[str, tuple[str, bool, bool]]) -> None:
	existing = read_json(paths.answer_bank_json, default={})
	bank = AnswerBank(answers={k: AnswerEntry(**v) for k, v in existing.items()} if existing else {})

	for key, (raw_value, is_sensitive, approved) in payload.items():
		parsed_value: str | bool
		if key == "needs_sponsorship":
			parsed_value = raw_value.strip().lower() in {"true", "1", "yes", "y"}
		else:
			parsed_value = raw_value

		entry = AnswerEntry(value=parsed_value, sensitive=is_sensitive, user_approved_reuse=approved)
		assert_answer_entry_safe(key, entry)
		bank.upsert(key, entry)

	write_json(paths.answer_bank_json, {k: v.model_dump(mode="json") for k, v in bank.answers.items()})


def _discover_jobs(paths: AppPaths, title: str, urls: list[str]) -> int:
	jobs = discover_from_manual_urls(title=title, urls=urls)
	unique = dedupe_jobs(jobs)
	for job in unique:
		append_jsonl(paths.jobs_discovered_jsonl, job.model_dump(mode="json"))
	return len(unique)


def _apply_jobs(paths: AppPaths, title: str, max_applications: int, approved_urls: set[str]) -> int:
	discovered_rows = read_jsonl(paths.jobs_discovered_jsonl)
	ranked = rank_jobs([_row_to_job(r) for r in discovered_rows], target_title=title)
	ranked = dedupe_jobs(ranked)

	successful = 0
	for job in ranked:
		if successful >= max_applications:
			break

		approved = str(job.url) in approved_urls
		status = "submitted" if approved else "user_skipped"
		if approved:
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

	return successful


def _write_report(paths: AppPaths, title: str, requested: int) -> Path:
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

	return write_report(
		reports_dir=paths.reports_dir,
		title=title,
		requested=requested,
		successful=successful,
		skipped=skipped,
		failed=failed,
		needs_user=needs_user,
		rows=table_rows,
	)


def main() -> None:
	st.set_page_config(page_title="Auto Job Apply", page_icon="🧭", layout="wide")
	st.title("Auto Job Apply")
	st.caption("Local-first, human-supervised workflow with shared CLI and UI data")

	paths = _bootstrap()
	st.info(f"Data directory: {paths.data_dir}")

	tab_setup, tab_profile, tab_answers, tab_discover, tab_apply, tab_report = st.tabs(
		["Setup", "Profile", "Answers", "Discover", "Apply", "Report"]
	)

	with tab_setup:
		st.subheader("Initialize local data")
		if st.button("Initialize", type="primary"):
			_bootstrap()
			st.success("Initialized data directories and settings.")

		st.divider()
		st.subheader("Current config")
		cfg = load_config()
		st.json({"data_dir": str(cfg.data_dir), "llm_base_url": cfg.llm_base_url})

		st.divider()
		st.subheader("Danger zone")
		confirm_clear = st.checkbox("I understand this will permanently delete local data")
		if st.button("Clear local data", disabled=not confirm_clear):
			if paths.data_dir.exists():
				shutil.rmtree(paths.data_dir)
			_bootstrap()
			st.success("Local data cleared and re-initialized.")

	with tab_profile:
		st.subheader("Parse resume")
		uploaded = st.file_uploader("Upload resume", type=["txt", "pdf", "docx"])
		if st.button("Save profile from resume", disabled=uploaded is None):
			_save_profile(uploaded, paths)
			st.success(f"Profile saved to {paths.profile_json}")

	with tab_answers:
		st.subheader("Manage reusable answers")
		existing = read_json(paths.answer_bank_json, default={})
		rows = _default_answer_rows(existing)
		answer_payload: dict[str, tuple[str, bool, bool]] = {}

		with st.form("answers_form"):
			for key, value, sensitive, approved in rows:
				c1, c2 = st.columns([3, 2])
				raw_value = c1.text_input(f"{key} value", value=value)
				approve = c2.checkbox(f"Allow reuse for {key}", value=approved)
				answer_payload[key] = (raw_value, sensitive, approve)

			submitted = st.form_submit_button("Save answers", type="primary")

		if submitted:
			_save_answers(paths, answer_payload)
			st.success(f"Answer bank saved to {paths.answer_bank_json}")

	with tab_discover:
		st.subheader("Add manual job URLs")
		title = st.text_input("Target title", value="Software Engineer II", key="discover_title")
		raw_urls = st.text_area("Job URLs (one per line)", height=150)
		if st.button("Discover jobs", type="primary"):
			urls = [line.strip() for line in raw_urls.splitlines() if line.strip()]
			count = _discover_jobs(paths, title=title, urls=urls)
			st.success(f"Discovered and stored {count} unique jobs.")

		discovered_rows = read_jsonl(paths.jobs_discovered_jsonl)
		if discovered_rows:
			st.caption(f"Stored discovered jobs: {len(discovered_rows)}")
			st.dataframe(discovered_rows, use_container_width=True)

	with tab_apply:
		st.subheader("Human-approved apply run")
		title = st.text_input("Target title", value="Software Engineer II", key="apply_title")
		max_apps = st.number_input("Max applications", min_value=1, value=1, step=1)

		discovered_rows = read_jsonl(paths.jobs_discovered_jsonl)
		ranked_options: list[str] = []
		if discovered_rows:
			ranked = rank_jobs([_row_to_job(r) for r in discovered_rows], target_title=title)
			ranked = dedupe_jobs(ranked)
			ranked_options = [f"{job.title} | {job.company or 'Unknown'} | {job.url}" for job in ranked]

		selected = st.multiselect(
			"Select jobs you approve for submit",
			options=ranked_options,
			help="Only selected URLs will be marked as submitted; all other processed jobs are recorded as user_skipped.",
		)

		if st.button("Run apply", type="primary", disabled=not ranked_options):
			approved_urls = {item.split(" | ")[-1] for item in selected}
			successful = _apply_jobs(paths, title=title, max_applications=int(max_apps), approved_urls=approved_urls)
			st.success(f"Apply run complete. Successful submissions: {successful}")

		app_rows = read_jsonl(paths.applications_jsonl)
		if app_rows:
			st.caption(f"Application attempts logged: {len(app_rows)}")
			st.dataframe(app_rows[-50:], use_container_width=True)

	with tab_report:
		st.subheader("Generate markdown report")
		title = st.text_input("Target title", value="Software Engineer II", key="report_title")
		requested = st.number_input("Requested submissions", min_value=1, value=1, step=1)
		if st.button("Generate report", type="primary"):
			report_path = _write_report(paths, title=title, requested=int(requested))
			st.success(f"Report saved: {report_path}")
			st.markdown(report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
	main()
