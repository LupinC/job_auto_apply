# Auto Job Apply v0

Local-first, human-supervised job application PoC.

## What v0 supports

- Local project initialization and data directory setup.
- Resume parsing (TXT/PDF/DOCX best-effort) into `data/profile.json`.
- Reusable answer bank saved to `data/answer_bank.json`.
- Manual job URL intake into `data/jobs.discovered.jsonl`.
- Basic matching and dedupe for manual jobs.
- Safe event/application logging with API key redaction.
- User-approved submission workflow (no autonomous submit).
- Final local markdown report in `data/reports/`.

## Install

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e .[dev]
python -m playwright install chromium
```

## CLI

```bash
python -m auto_job_apply.main init
python -m auto_job_apply.main profile --resume ./data/resumes/resume.txt
python -m auto_job_apply.main answers
python -m auto_job_apply.main discover --title "Software Engineer II" --url "https://example.com/job/123"
python -m auto_job_apply.main apply --title "Software Engineer II" --max-applications 1
python -m auto_job_apply.main report --title "Software Engineer II" --requested 1
python -m auto_job_apply.main clear-data --yes
```

## Safety notes

- This PoC does not bypass CAPTCHA/MFA/login walls.
- This PoC never auto-submits without explicit user confirmation.
- Do not commit `data/` or `.env`.
