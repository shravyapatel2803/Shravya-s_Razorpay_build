"""
rate_limiter.py — Sliding-window rate limiter using slowapi (memory-based).

Limits:
  Auth endpoints (login/register): 10 req/min per IP    (brute-force protection)
  Webhook endpoint:                100 req/min per merchant
  Read/GET endpoints:              300 req/min per merchant
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# ---------------------------------------------------------------------------
# Single limiter instance — imported into main.py and route files
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


def get_merchant_key(request) -> str:
    """
    Custom key for per-merchant rate limiting.
    Uses the resolved merchant_id if available (set by auth middleware),
    falls back to remote IP for unauthenticated requests.
    """
    merchant_id = getattr(request.state, "merchant_id", None)
    if merchant_id:
        return f"merchant:{merchant_id}"
    return get_remote_address(request)
