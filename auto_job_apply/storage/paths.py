from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from auto_job_apply.constants import DATA_DIRS, DATA_FILES


@dataclass(frozen=True)
class AppPaths:
    data_dir: Path

    def ensure(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for dirname in DATA_DIRS:
            (self.data_dir / dirname).mkdir(parents=True, exist_ok=True)

    @property
    def profile_json(self) -> Path:
        return self.data_dir / DATA_FILES["profile"]

    @property
    def answer_bank_json(self) -> Path:
        return self.data_dir / DATA_FILES["answers"]

    @property
    def settings_json(self) -> Path:
        return self.data_dir / DATA_FILES["settings"]

    @property
    def jobs_discovered_jsonl(self) -> Path:
        return self.data_dir / DATA_FILES["jobs_discovered"]

    @property
    def jobs_filtered_jsonl(self) -> Path:
        return self.data_dir / DATA_FILES["jobs_filtered"]

    @property
    def applications_jsonl(self) -> Path:
        return self.data_dir / DATA_FILES["applications"]

    @property
    def events_jsonl(self) -> Path:
        return self.data_dir / DATA_FILES["events"]

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"

    @property
    def screenshots_dir(self) -> Path:
        return self.data_dir / "screenshots"

    @property
    def browser_profile_dir(self) -> Path:
        return self.data_dir / "browser_profile"
