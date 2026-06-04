from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


def _find_project_root(start: Path) -> Path:
    current = start.resolve()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return start.resolve()


@dataclass(frozen=True)
class AppConfig:
    project_root: Path
    data_dir: Path
    llm_api_key: str | None
    llm_base_url: str | None

    @property
    def browser_profile_dir(self) -> Path:
        return self.data_dir / "browser_profile"



def load_config() -> AppConfig:
    root = _find_project_root(Path.cwd())
    load_dotenv(root / ".env", override=False)

    data_dir_raw = os.getenv("AUTO_JOB_APPLY_DATA_DIR", "./data")
    data_dir = (root / data_dir_raw).resolve() if not Path(data_dir_raw).is_absolute() else Path(data_dir_raw)
    llm_base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")

    return AppConfig(
        project_root=root,
        data_dir=data_dir,
        llm_api_key=os.getenv("OPENAI_API_KEY"),
        llm_base_url=llm_base_url,
    )
