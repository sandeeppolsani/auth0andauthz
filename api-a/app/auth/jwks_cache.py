import json
import logging
import time
from datetime import datetime, timezone

import httpx


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": record.getMessage(),
        }
        if hasattr(record, "kid"):
            log_entry["kid"] = record.kid
        if hasattr(record, "key_count"):
            log_entry["key_count"] = record.key_count
        return json.dumps(log_entry)


_handler = logging.StreamHandler()
_handler.setFormatter(_JsonFormatter())

logger = logging.getLogger(__name__)
logger.addHandler(_handler)
logger.setLevel(logging.INFO)
logger.propagate = False


class JWKSCache:
    def __init__(self, jwks_uri: str, ttl_seconds: int = 600):
        self.jwks_uri = jwks_uri
        self.ttl_seconds = ttl_seconds
        self._keys: dict = {}
        self._fetched_at: float = 0.0

    def get_key(self, kid: str) -> dict | None:
        age = time.time() - self._fetched_at
        if not self._keys or age > self.ttl_seconds:
            logger.info("JWKS_CACHE_MISS", extra={"kid": kid})
            try:
                self._fetch()
            except Exception:
                return None

        if kid in self._keys:
            logger.info("JWKS_CACHE_HIT", extra={"kid": kid})
            return self._keys[kid]

        logger.info("JWKS_KID_NOT_FOUND", extra={"kid": kid})
        return None

    def invalidate_and_refetch(self) -> None:
        self._keys = {}
        self._fetched_at = 0.0
        logger.info("JWKS_CACHE_INVALIDATED_REFETCH")
        try:
            self._fetch()
        except Exception:
            pass

    def _fetch(self) -> None:
        response = httpx.get(self.jwks_uri, timeout=10)
        response.raise_for_status()
        data = response.json()
        self._keys = {key["kid"]: key for key in data["keys"]}
        self._fetched_at = time.time()
        logger.info("JWKS_CACHE_REFRESHED", extra={"key_count": len(self._keys)})
