"""Tests for api-b/app/db/mock_db.py — Task 3.1"""
import importlib
import app.db.mock_db as mock_db


def _reset():
    """Reset module-level state between tests."""
    mock_db._analytics.update({
        "total_users": 42,
        "active_sessions": 7,
        "last_updated": "2026-03-22T00:00:00Z",
    })
    mock_db._config.clear()
    mock_db._config.update({
        "maintenance_mode": False,
        "log_level": "INFO",
        "feature_flags": {"dark_mode": True, "beta_features": False},
    })
    mock_db._audit_log.clear()


# ---------------------------------------------------------------------------
# TC-1  get_analytics returns seed data
# ---------------------------------------------------------------------------

def test_get_analytics_seed_values():
    _reset()
    result = mock_db.get_analytics()
    assert result["total_users"] == 42
    assert result["active_sessions"] == 7
    assert result["last_updated"] == "2026-03-22T00:00:00Z"


def test_get_analytics_returns_copy():
    _reset()
    r1 = mock_db.get_analytics()
    r1["total_users"] = 999
    r2 = mock_db.get_analytics()
    assert r2["total_users"] == 42  # original untouched


# ---------------------------------------------------------------------------
# TC-2  get_config returns seed data
# ---------------------------------------------------------------------------

def test_get_config_seed_values():
    _reset()
    result = mock_db.get_config()
    assert result["maintenance_mode"] is False
    assert result["log_level"] == "INFO"
    assert result["feature_flags"]["dark_mode"] is True
    assert result["feature_flags"]["beta_features"] is False


def test_get_config_returns_copy():
    _reset()
    r1 = mock_db.get_config()
    r1["log_level"] = "DEBUG"
    r2 = mock_db.get_config()
    assert r2["log_level"] == "INFO"  # original untouched


# ---------------------------------------------------------------------------
# TC-3  update_config patches correctly
# ---------------------------------------------------------------------------

def test_update_config_patches_key():
    _reset()
    mock_db.update_config({"log_level": "DEBUG"})
    assert mock_db.get_config()["log_level"] == "DEBUG"


def test_update_config_leaves_unrelated_keys_unchanged():
    _reset()
    mock_db.update_config({"log_level": "WARNING"})
    result = mock_db.get_config()
    assert result["maintenance_mode"] is False
    assert result["feature_flags"]["dark_mode"] is True


def test_update_config_adds_new_key():
    _reset()
    mock_db.update_config({"new_key": "new_value"})
    assert mock_db.get_config()["new_key"] == "new_value"


def test_update_config_returns_updated_state():
    _reset()
    returned = mock_db.update_config({"maintenance_mode": True})
    assert returned["maintenance_mode"] is True


def test_update_config_return_is_copy():
    _reset()
    returned = mock_db.update_config({"log_level": "ERROR"})
    returned["log_level"] = "MUTATED"
    assert mock_db.get_config()["log_level"] == "ERROR"


# ---------------------------------------------------------------------------
# TC-4  append_audit_entry + get_audit_log
# ---------------------------------------------------------------------------

def test_append_audit_entry_appears_in_log():
    _reset()
    entry = {"timestamp": "2026-03-22T10:00:00Z", "subject": "alice@example.com",
              "route": "/api/analytics/summary", "outcome": "pass"}
    mock_db.append_audit_entry(entry)
    log = mock_db.get_audit_log()
    assert len(log) == 1
    assert log[0] == entry


def test_append_audit_entry_multiple_entries_ordered():
    _reset()
    e1 = {"timestamp": "T1", "subject": "alice@example.com", "route": "/api/analytics/summary", "outcome": "pass"}
    e2 = {"timestamp": "T2", "subject": "admin@example.com", "route": "/api/config", "outcome": "pass"}
    mock_db.append_audit_entry(e1)
    mock_db.append_audit_entry(e2)
    log = mock_db.get_audit_log()
    assert len(log) == 2
    assert log[0]["timestamp"] == "T1"
    assert log[1]["timestamp"] == "T2"


def test_get_audit_log_returns_copy():
    _reset()
    entry = {"timestamp": "T", "subject": "s", "route": "r", "outcome": "o"}
    mock_db.append_audit_entry(entry)
    log = mock_db.get_audit_log()
    log.append({"timestamp": "extra"})
    assert len(mock_db.get_audit_log()) == 1  # internal list untouched


# ---------------------------------------------------------------------------
# TC-5  audit_log starts empty
# ---------------------------------------------------------------------------

def test_audit_log_starts_empty():
    _reset()
    assert mock_db.get_audit_log() == []


# ---------------------------------------------------------------------------
# TC-6  No fastapi / jose imports
# ---------------------------------------------------------------------------

def test_update_config_empty_dict_is_noop():
    _reset()
    before = mock_db.get_config()
    mock_db.update_config({})
    after = mock_db.get_config()
    assert after == before


def test_update_config_nested_dict_replaces_not_merges():
    _reset()
    mock_db.update_config({"feature_flags": {"dark_mode": False}})
    flags = mock_db.get_config()["feature_flags"]
    # dict.update replaces the nested dict wholesale — beta_features key is gone
    assert flags == {"dark_mode": False}


# ---------------------------------------------------------------------------
# TC-6  No fastapi / jose imports
# ---------------------------------------------------------------------------

def test_no_fastapi_or_jose_imported():
    import ast, pathlib
    src = pathlib.Path("app/db/mock_db.py").read_text()
    tree = ast.parse(src)
    bad = {"fastapi", "jose"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [n.name for n in getattr(node, "names", [])]
            module = getattr(node, "module", "") or ""
            top = module.split(".")[0] if module else ""
            for name in names + [top]:
                assert name not in bad, f"Forbidden import found: {name}"
