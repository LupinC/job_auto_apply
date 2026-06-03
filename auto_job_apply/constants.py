from __future__ import annotations

from pathlib import Path

APP_NAME = "auto-job-apply"

DATA_FILES = {
    "profile": "profile.json",
    "answers": "answer_bank.json",
    "settings": "settings.json",
    "jobs_discovered": "jobs.discovered.jsonl",
    "jobs_filtered": "jobs.filtered.jsonl",
    "applications": "applications.jsonl",
    "events": "events.jsonl",
}

DATA_DIRS = [
    "resumes",
    "cover_letters",
    "screenshots",
    "browser_profile",
    "reports",
]

SENSITIVE_ANSWER_KEYS = {
    "veteran_status",
    "race_ethnicity",
    "disability_status",
    "gender",
    "citizenship",
    "immigration_status",
    "age",
    "religion",
    "sexual_orientation",
}

MASKED = "***REDACTED***"

DEFAULT_MIN_MATCH_SCORE = 0.45

STATUS_SUCCESS = "success"
STATUS_SKIPPED = "skipped"
STATUS_NEEDS_USER = "needs_user"
STATUS_FAILED = "failed"
STATUS_UNKNOWN_NEEDS_REVIEW = "unknown_needs_review"

ROOT_MARKER = Path("pyproject.toml")
