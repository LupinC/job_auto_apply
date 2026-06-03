from __future__ import annotations


def should_log_sensitive(sensitive: bool, explicit_user_opt_in: bool) -> bool:
    return sensitive and explicit_user_opt_in
