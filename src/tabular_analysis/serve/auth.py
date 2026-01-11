"""Authentication helpers for serving."""

from __future__ import annotations

import hashlib
import hmac
from typing import Iterable


def verify_api_key(value: str | None, api_keys: Iterable[str]) -> bool:
    keys = tuple(api_keys)
    if not keys:
        return True
    if not value:
        return False
    for key in keys:
        if hmac.compare_digest(value, key):
            return True
    return False


def api_key_fingerprint(value: str | None) -> str | None:
    if not value:
        return None
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest[:12]


def resolve_principal(value: str | None, api_keys: Iterable[str]) -> str:
    keys = tuple(api_keys)
    if not keys:
        return "anonymous"
    fingerprint = api_key_fingerprint(value)
    if fingerprint:
        return f"api_key:{fingerprint}"
    return "unknown"


__all__ = ["api_key_fingerprint", "resolve_principal", "verify_api_key"]
