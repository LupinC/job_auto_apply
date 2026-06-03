from __future__ import annotations

from auto_job_apply.safety.secrets import redact_text


def test_secret_redaction_masks_api_keys() -> None:
    text = "api=sk-1234567890abcdef123456"
    redacted = redact_text(text)
    assert "sk-1234567890abcdef123456" not in redacted
    assert "..." in redacted
