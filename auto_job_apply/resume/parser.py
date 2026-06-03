from __future__ import annotations

from pathlib import Path
import re

from auto_job_apply.errors import ResumeParseError
from auto_job_apply.models.profile import Profile
from auto_job_apply.resume.extractor import extract_text
from auto_job_apply.resume.normalizer import clean_resume_text

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{3}\)?[\s\-]?)\d{3}[\s\-]?\d{4}")
LINKEDIN_RE = re.compile(r"https?://(?:www\.)?linkedin\.com/\S+", re.IGNORECASE)
GITHUB_RE = re.compile(r"https?://(?:www\.)?github\.com/\S+", re.IGNORECASE)
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


def parse_resume(path: Path) -> Profile:
    if not path.exists() or not path.is_file():
        raise ResumeParseError(f"Resume file not found: {path}")

    try:
        raw = extract_text(path)
    except Exception as exc:
        raise ResumeParseError(str(exc)) from exc

    text = clean_resume_text(raw)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    full_name = lines[0] if lines else None

    first_name = None
    last_name = None
    if full_name and " " in full_name:
        chunks = full_name.split()
        first_name = chunks[0]
        last_name = chunks[-1]

    email = _first_match(EMAIL_RE, text)
    phone = _first_match(PHONE_RE, text)
    linkedin = _first_match(LINKEDIN_RE, text)
    github = _first_match(GITHUB_RE, text)
    portfolio = _first_portfolio(URL_RE.findall(text), linkedin, github)

    skills = _extract_skills(text)

    return Profile(
        first_name=first_name,
        last_name=last_name,
        full_name=full_name,
        email=email,
        phone=phone,
        linkedin=linkedin,
        github=github,
        portfolio=portfolio,
        skills=skills,
    )


def _first_match(pattern: re.Pattern[str], text: str) -> str | None:
    m = pattern.search(text)
    return m.group(0) if m else None


def _first_portfolio(urls: list[str], linkedin: str | None, github: str | None) -> str | None:
    blocked = {linkedin, github, None}
    for url in urls:
        if url not in blocked:
            return url
    return None


def _extract_skills(text: str) -> list[str]:
    known = ["python", "java", "javascript", "typescript", "aws", "react", "sql", "docker"]
    lower = text.lower()
    return [skill.upper() if skill == "aws" else skill.title() for skill in known if skill in lower]
