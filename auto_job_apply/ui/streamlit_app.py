from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import webbrowser

import streamlit as st

from auto_job_apply.apply.runner import build_application_attempt
from auto_job_apply.config import load_config
from auto_job_apply.jobs.dedupe import dedupe_jobs
from auto_job_apply.jobs.discovery import discover_from_manual_urls
from auto_job_apply.jobs.matcher import rank_jobs
from auto_job_apply.logging_setup import safe_log, setup_logging
from auto_job_apply.models.answers import AnswerBank, AnswerEntry
from auto_job_apply.models.job import Job
from auto_job_apply.resume.parser import parse_resume
from auto_job_apply.safety.validation import assert_answer_entry_safe
from auto_job_apply.storage.json_store import read_json, write_json
from auto_job_apply.storage.jsonl_store import append_jsonl, read_jsonl
from auto_job_apply.storage.cleanup import clear_data_dir
from auto_job_apply.storage.paths import AppPaths
from auto_job_apply.storage.report_writer import write_report

import logging


logger = setup_logging()


def _resolve_resume_path(paths: AppPaths) -> str | None:
	events = read_jsonl(paths.events_jsonl)
	for row in reversed(events):
		if row.get("event") != "profile_updated":
			continue
		resume = row.get("resume")
		if not resume:
			continue
		candidate = Path(str(resume))
		if candidate.exists():
			return str(candidate)

	resumes_dir = paths.data_dir / "resumes"
	if not resumes_dir.exists():
		return None

	files = [p for p in resumes_dir.iterdir() if p.is_file()]
	if not files:
		return None

	latest = max(files, key=lambda p: p.stat().st_mtime)
	return str(latest)


def _row_to_job(row: dict) -> Job:
	return Job(**row)


def _bootstrap() -> AppPaths:
	cfg = load_config()
	paths = AppPaths(cfg.data_dir)
	paths.ensure()
	if not paths.settings_json.exists():
		write_json(paths.settings_json, {"created_at": datetime.now(UTC).isoformat()})
	safe_log(logger, logging.INFO, "action_completed", action="ui_bootstrap", data_dir=paths.data_dir)
	return paths


def _save_profile(uploaded_file, paths: AppPaths) -> None:
	safe_log(logger, logging.INFO, "action_started", action="ui_save_profile", filename=uploaded_file.name)
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
	safe_log(logger, logging.INFO, "action_completed", action="ui_save_profile", profile_path=paths.profile_json)


def _answer_options() -> dict[str, list[str]]:
	return {
		"needs_sponsorship": ["No", "Yes"],
		"work_authorization": [
			"Authorized to work in the United States",
			"Requires visa sponsorship",
			"Not authorized to work in the United States",
		],
		"veteran_status": [
			"I am not a protected veteran",
			"I identify as a protected veteran",
			"I do not wish to answer",
		],
		"race_ethnicity": [
			"American Indian or Alaska Native",
			"Asian",
			"Black or African American",
			"Hispanic or Latino",
			"Native Hawaiian or Other Pacific Islander",
			"White",
			"Two or More Races",
			"I do not wish to answer",
		],
		"disability_status": [
			"Yes, I have a disability or have had one in the past",
			"No, I do not have a disability and have not had one in the past",
			"I do not wish to answer",
		],
	}


def _default_answer_rows(existing: dict[str, dict]) -> list[tuple[str, str, bool, bool, list[str]]]:
	defaults: list[tuple[str, str | bool, bool]] = [
		("needs_sponsorship", False, False),
		("work_authorization", "Authorized to work in the United States", False),
		("veteran_status", "I do not wish to answer", True),
		("race_ethnicity", "I do not wish to answer", True),
		("disability_status", "I do not wish to answer", True),
	]
	options_map = _answer_options()

	rows: list[tuple[str, str, bool, bool, list[str]]] = []
	for key, default_value, sensitive in defaults:
		current = existing.get(key, {})
		raw_val = current.get("value", default_value)
		if key == "needs_sponsorship":
			val = "Yes" if bool(raw_val) else "No"
		else:
			val = str(raw_val)
		approved = bool(current.get("user_approved_reuse", False))
		options = list(options_map.get(key, []))
		if val not in options:
			options = [val, *options]
		rows.append((key, val, sensitive, approved, options))
	return rows


def _save_answers(paths: AppPaths, payload: dict[str, tuple[str, bool, bool]]) -> None:
	safe_log(logger, logging.INFO, "action_started", action="ui_save_answers", key_count=len(payload))
	existing = read_json(paths.answer_bank_json, default={})
	bank = AnswerBank(answers={k: AnswerEntry(**v) for k, v in existing.items()} if existing else {})

	for key, (raw_value, is_sensitive, approved) in payload.items():
		parsed_value: str | bool
		if key == "needs_sponsorship":
			parsed_value = raw_value.strip().lower() == "yes"
		else:
			parsed_value = raw_value

		entry = AnswerEntry(value=parsed_value, sensitive=is_sensitive, user_approved_reuse=approved)
		assert_answer_entry_safe(key, entry)
		bank.upsert(key, entry)

	write_json(paths.answer_bank_json, {k: v.model_dump(mode="json") for k, v in bank.answers.items()})
	safe_log(logger, logging.INFO, "action_completed", action="ui_save_answers", answer_count=len(bank.answers))


def _discover_jobs(paths: AppPaths, title: str, urls: list[str]) -> int:
	safe_log(logger, logging.INFO, "action_started", action="ui_discover", title=title, url_count=len(urls))
	jobs = discover_from_manual_urls(title=title, urls=urls)
	unique = dedupe_jobs(jobs)
	for job in unique:
		append_jsonl(paths.jobs_discovered_jsonl, job.model_dump(mode="json"))
	safe_log(logger, logging.INFO, "action_completed", action="ui_discover", discovered=len(unique))
	return len(unique)


def _apply_jobs(paths: AppPaths, title: str, max_applications: int, approved_urls: set[str]) -> tuple[int, int]:
	safe_log(
		logger,
		logging.INFO,
		"action_started",
		action="ui_apply",
		title=title,
		max_applications=max_applications,
		approved_count=len(approved_urls),
	)
	discovered_rows = read_jsonl(paths.jobs_discovered_jsonl)
	ranked = rank_jobs([_row_to_job(r) for r in discovered_rows], target_title=title)
	ranked = dedupe_jobs(ranked)
	resume_path = _resolve_resume_path(paths)

	successful = 0
	approved_pending_submit = 0
	for job in ranked:
		if approved_pending_submit >= max_applications:
			break

		approved = str(job.url) in approved_urls
		if approved:
			status = "needs_user"
			reason = "Approved for manual submission; automated submit not available in v0"
			approved_pending_submit += 1
		else:
			status = "user_skipped"
			reason = "User declined submit"

		attempt = build_application_attempt(
			company=job.company,
			title=job.title,
			url=str(job.url),
			status=status,
			reason=reason,
			resume_path=resume_path,
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
				"reason": reason,
			},
		)

		safe_log(
			logger,
			logging.INFO,
			"application_recorded",
			title=job.title,
			company=job.company,
			url=job.url,
			status=status,
			reason=reason,
		)

	safe_log(
		logger,
		logging.INFO,
		"action_completed",
		action="ui_apply",
		successful=successful,
		approved_pending_submit=approved_pending_submit,
	)
	return successful, approved_pending_submit


def _write_report(paths: AppPaths, title: str, requested: int) -> Path:
	safe_log(logger, logging.INFO, "action_started", action="ui_report", title=title, requested=requested)
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
	safe_log(logger, logging.INFO, "action_completed", action="ui_report", report_path=report_path)
	return report_path


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
			safe_log(logger, logging.INFO, "action_started", action="ui_initialize_button")
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
			safe_log(logger, logging.INFO, "action_started", action="ui_clear_data")
			blocked: list[str] = []
			used_windows_fallback = False
			if paths.data_dir.exists():
				result = clear_data_dir(paths.data_dir)
				blocked = result.blocked_paths
				used_windows_fallback = result.used_windows_fallback
			_bootstrap()
			if blocked:
				st.warning("Local data partially cleared. Some files/folders are locked by another process.")
				st.dataframe([{"blocked_path": path} for path in blocked[:20]], use_container_width=True)
				st.info("Close any browser using data/browser_profile, then click Clear local data again.")
			else:
				st.success("Local data cleared and re-initialized.")
				if used_windows_fallback:
					st.caption("Clear status: used Windows fallback cleanup for OneDrive/reparse-point paths.")
				else:
					st.caption("Clear status: standard Python cleanup.")
			safe_log(
				logger,
				logging.INFO,
				"action_completed",
				action="ui_clear_data",
				blocked_count=len(blocked),
				used_windows_fallback=used_windows_fallback,
			)

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
			for key, value, sensitive, approved, options in rows:
				c1, c2 = st.columns([3, 2])
				raw_value = c1.selectbox(f"{key} value", options=options, index=options.index(value))
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
		st.warning(
			"v0 does not auto-fill website forms yet (including Asana/Greenhouse-hosted apply pages). "
			"Run apply records approved links as needs_user for manual completion."
		)
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
			key="apply_selected_jobs",
			help="Selected URLs are recorded as needs_user (approved and pending manual submit); all others are recorded as user_skipped.",
		)

		if "approved_urls" not in st.session_state:
			st.session_state["approved_urls"] = []

		def _extract_url(option: str) -> str:
			return option.rsplit(" | ", 1)[-1]

		approve_col, clear_col = st.columns(2)
		if approve_col.button("Approve selected for manual submit", disabled=not selected):
			current = set(st.session_state.get("approved_urls", []))
			current.update(_extract_url(item) for item in selected)
			st.session_state["approved_urls"] = sorted(current)

		if clear_col.button("Clear approved list", disabled=not st.session_state.get("approved_urls")):
			st.session_state["approved_urls"] = []

		approved_urls = set(st.session_state.get("approved_urls", []))
		st.caption(f"Approved URLs ready for apply: {len(approved_urls)}")
		if approved_urls:
			st.dataframe([{"approved_url": url} for url in sorted(approved_urls)], use_container_width=True)
			if st.button("Open approved links in browser"):
				opened = 0
				for url in sorted(approved_urls):
					if webbrowser.open_new_tab(url):
						opened += 1
				st.info(f"Opened {opened} approved link(s) in your default browser for manual form completion.")
		else:
			st.info("Pick jobs and click 'Approve selected for manual submit' before running apply.")

		if st.button("Run apply", type="primary", disabled=not ranked_options or not approved_urls):
			successful, pending = _apply_jobs(paths, title=title, max_applications=int(max_apps), approved_urls=approved_urls)
			st.success(f"Apply run complete. Successful submissions: {successful}")
			if pending:
				st.warning(f"Approved for manual submit (pending your action): {pending}")

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
