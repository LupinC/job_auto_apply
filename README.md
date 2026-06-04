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
- Apply run records approvals only; it does not auto-fill third-party job forms yet (including Asana/Greenhouse-hosted pages).
- Final local markdown report in `data/reports/`.

## Install

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e .[dev]
python -m playwright install chromium
```

For UI support:

```bash
pip install -e .[ui]
```

If you want CLI only, you do not need to install `.[ui]`.

If you want UI only, you can install just UI extras:

```bash
pip install -e .[ui]
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

## UI (Streamlit)

Launch from UI module directly (UI-only mode):

```bash
python -m auto_job_apply.ui.cli --host 127.0.0.1 --port 8501
```

Or with Streamlit command:

```bash
streamlit run auto_job_apply/ui/streamlit_app.py
```

Optional launch from CLI command:

```bash
python -m auto_job_apply.main ui --host 127.0.0.1 --port 8501
```

Or direct script entrypoint:

```bash
auto-job-apply-ui
```

The UI and CLI share the same local data directory, so you can mix both workflows.

UI-only mode now supports the full v0 workflow, including config visibility and local data clearing.

## Safety notes

- This PoC does not bypass CAPTCHA/MFA/login walls.
- This PoC never auto-submits without explicit user confirmation.
- Do not commit `data/` or `.env`.
