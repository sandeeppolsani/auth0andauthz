_analytics: dict = {
    "total_users": 42,
    "active_sessions": 7,
    "last_updated": "2026-03-22T00:00:00Z",
}

_config: dict = {
    "maintenance_mode": False,
    "log_level": "INFO",
    "feature_flags": {"dark_mode": True, "beta_features": False},
}

_audit_log: list[dict] = []


def get_analytics() -> dict:
    return _analytics.copy()


def get_config() -> dict:
    return _config.copy()


def update_config(updates: dict) -> dict:
    _config.update(updates)
    return _config.copy()


def append_audit_entry(entry: dict) -> None:
    """entry must have: timestamp (str), subject (str), route (str), outcome (str)"""
    _audit_log.append(entry)


def get_audit_log() -> list[dict]:
    return list(_audit_log)
