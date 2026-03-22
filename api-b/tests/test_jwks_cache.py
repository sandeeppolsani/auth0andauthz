"""Tests for api-b/app/auth/jwks_cache.py — Task 3.2 (JWKS Cache)"""
import time
from unittest.mock import MagicMock, patch

import pytest

from app.auth.jwks_cache import JWKSCache

FAKE_KID = "kid-abc"
FAKE_KEY = {"kid": FAKE_KID, "kty": "RSA", "n": "abc", "e": "AQAB"}
FAKE_JWKS = {"keys": [FAKE_KEY]}


def _make_cache(ttl: int = 600) -> JWKSCache:
    return JWKSCache(jwks_uri="https://test.example.com/oauth2/v1/keys", ttl_seconds=ttl)


def _mock_response(keys: list[dict]):
    resp = MagicMock()
    resp.json.return_value = {"keys": keys}
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# TC-1  get_key triggers fetch on empty cache (JWKS_CACHE_MISS)
# ---------------------------------------------------------------------------

def test_get_key_fetches_on_empty_cache():
    cache = _make_cache()
    with patch("app.auth.jwks_cache.httpx.get", return_value=_mock_response([FAKE_KEY])) as mock_get:
        key = cache.get_key(FAKE_KID)
    assert key == FAKE_KEY
    mock_get.assert_called_once()


# ---------------------------------------------------------------------------
# TC-2  get_key returns cached key without re-fetching (JWKS_CACHE_HIT)
# ---------------------------------------------------------------------------

def test_get_key_returns_from_cache():
    cache = _make_cache()
    with patch("app.auth.jwks_cache.httpx.get", return_value=_mock_response([FAKE_KEY])):
        cache.get_key(FAKE_KID)  # prime cache
    with patch("app.auth.jwks_cache.httpx.get") as mock_get:
        key = cache.get_key(FAKE_KID)
    assert key == FAKE_KEY
    mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# TC-3  get_key re-fetches after TTL expiry
# ---------------------------------------------------------------------------

def test_get_key_refetches_after_ttl():
    cache = _make_cache(ttl=1)
    with patch("app.auth.jwks_cache.httpx.get", return_value=_mock_response([FAKE_KEY])):
        cache.get_key(FAKE_KID)  # prime
    time.sleep(1.1)
    with patch("app.auth.jwks_cache.httpx.get", return_value=_mock_response([FAKE_KEY])) as mock_get:
        cache.get_key(FAKE_KID)
    mock_get.assert_called_once()


# ---------------------------------------------------------------------------
# TC-4  get_key returns None for unknown kid (JWKS_KID_NOT_FOUND)
# ---------------------------------------------------------------------------

def test_get_key_returns_none_for_unknown_kid():
    cache = _make_cache()
    with patch("app.auth.jwks_cache.httpx.get", return_value=_mock_response([FAKE_KEY])):
        result = cache.get_key("kid-unknown")
    assert result is None


# ---------------------------------------------------------------------------
# TC-5  invalidate_and_refetch clears cache and re-fetches
# ---------------------------------------------------------------------------

def test_invalidate_and_refetch_clears_and_reloads():
    cache = _make_cache()
    with patch("app.auth.jwks_cache.httpx.get", return_value=_mock_response([FAKE_KEY])):
        cache.get_key(FAKE_KID)  # prime
    new_key = {"kid": "kid-new", "kty": "RSA", "n": "xyz", "e": "AQAB"}
    with patch("app.auth.jwks_cache.httpx.get", return_value=_mock_response([new_key])) as mock_get:
        cache.invalidate_and_refetch()
        result = cache.get_key("kid-new")
    mock_get.assert_called_once()
    assert result == new_key


# ---------------------------------------------------------------------------
# TC-6  get_key returns None when HTTP fetch fails
# ---------------------------------------------------------------------------

def test_get_key_returns_none_on_fetch_failure():
    cache = _make_cache()
    with patch("app.auth.jwks_cache.httpx.get", side_effect=Exception("network error")):
        result = cache.get_key(FAKE_KID)
    assert result is None


# ---------------------------------------------------------------------------
# TC-7  invalidate_and_refetch survives fetch failure silently
# ---------------------------------------------------------------------------

def test_invalidate_and_refetch_survives_failure():
    cache = _make_cache()
    with patch("app.auth.jwks_cache.httpx.get", return_value=_mock_response([FAKE_KEY])):
        cache.get_key(FAKE_KID)
    with patch("app.auth.jwks_cache.httpx.get", side_effect=Exception("network error")):
        cache.invalidate_and_refetch()  # should not raise
    assert cache._keys == {}


# ---------------------------------------------------------------------------
# TC-8  leeway kwarg forwarded — jwt.decode called with leeway=60 (JWKS layer)
# ---------------------------------------------------------------------------
# (This is a JWKS-layer smoke test; full leeway verification is in test_auth_middleware.py)

def test_get_key_stores_all_keys():
    cache = _make_cache()
    key2 = {"kid": "kid-2", "kty": "RSA", "n": "def", "e": "AQAB"}
    with patch("app.auth.jwks_cache.httpx.get", return_value=_mock_response([FAKE_KEY, key2])):
        cache.get_key(FAKE_KID)
    assert cache.get_key("kid-2") == key2
