from __future__ import annotations

import logging
import re
from typing import Any

from auto_job_apply.safety.secrets import redact_text

API_KEY_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9]{10,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}\b"),
]


class SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(str(record.msg))
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(redact_text(str(a)) for a in record.args)
            elif isinstance(record.args, dict):
                record.args = {k: redact_text(str(v)) for k, v in record.args.items()}
            else:
                record.args = redact_text(str(record.args))
        return True


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("auto_job_apply")
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        handler.addFilter(SecretRedactionFilter())
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    return logger


def safe_log(logger: logging.Logger, level: int, message: str, **kwargs: Any) -> None:
    parts = [message]
    for key, value in kwargs.items():
        parts.append(f"{key}={redact_text(str(value))}")
    logger.log(level, " ".join(parts))
