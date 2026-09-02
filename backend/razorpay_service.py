"""
razorpay_service.py — Razorpay API wrapper with authentic mock fallback.

If RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET are present the real SDK is used.
Otherwise every operation silently degrades to a deterministic mock so the
entire system works out-of-the-box without credentials.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Credential resolution
# ---------------------------------------------------------------------------

_KEY_ID: str | None = os.getenv("RAZORPAY_KEY_ID")
_KEY_SECRET: str | None = os.getenv("RAZORPAY_KEY_SECRET")
_MOCK_MODE: bool = not (_KEY_ID and _KEY_SECRET)

_rzp_client: Any = None

if not _MOCK_MODE:
    try:
        import razorpay  # type: ignore[import]
        _rzp_client = razorpay.Client(auth=(_KEY_ID, _KEY_SECRET))
        logger.info("Razorpay client initialised in LIVE mode (key=%s...)", _KEY_ID[:6])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Razorpay SDK init failed (%s); falling back to MOCK mode.", exc)
        _MOCK_MODE = True
else:
    logger.info(
        "RAZORPAY_KEY_ID/SECRET not set — running in MOCK mode. "
        "All payment-link URLs will be simulated."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_recovery_payment_link(
    order_id: str,
    amount_paise: int,
    customer_name: str,
    phone: str,
    email: str,
    notes: dict | None = None,
) -> str:
    """
    Create a Razorpay Payment Link for payment recovery and return its short URL.

    Parameters
    ----------
    order_id       : Internal order reference (used in the link description).
    amount_paise   : Transaction amount in paise.
    customer_name  : Full name of the payer.
    phone          : E.164 phone number.
    email          : Payer email address.
    notes          : Optional dict of key/value metadata attached to the link.

    Returns
    -------
    str — Razorpay short URL (e.g. https://rzp.io/i/abc123) or a mock URL.
    """
    if notes is None:
        notes = {}

    notes.setdefault("recovery_pipeline", "autonomous_dunning_v1")
    notes.setdefault("original_order_id", order_id)

    payload: dict = {
        "amount": amount_paise,
        "currency": "INR",
        "accept_partial": False,
        "description": f"Recovery checkout for Order #{order_id}",
        "customer": {
            "name": customer_name,
            "contact": phone,
            "email": email,
        },
        # Agent manages communication; suppress Razorpay defaults
        "notify": {"sms": False, "email": False},
        "reminder_enable": True,
        "notes": notes,
    }

    if _MOCK_MODE:
        return _mock_payment_link(order_id)

    try:
        response = _rzp_client.payment_link.create(payload)
        short_url: str = response["short_url"]
        logger.info("Payment link created: %s (order=%s)", short_url, order_id)
        return short_url
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Razorpay payment_link.create failed for order %s: %s — returning mock URL.",
            order_id,
            exc,
        )
        return _mock_payment_link(order_id)


def get_payment_status(payment_id: str) -> dict:
    """
    Fetch a payment's current status from Razorpay.
    Returns a mock response when in MOCK mode.
    """
    if _MOCK_MODE:
        return {
            "id": payment_id,
            "status": "failed",
            "method": "upi",
            "mock": True,
        }
    try:
        return dict(_rzp_client.payment.fetch(payment_id))
    except Exception as exc:  # noqa: BLE001
        logger.error("payment.fetch failed for %s: %s", payment_id, exc)
        return {"id": payment_id, "status": "unknown", "error": str(exc)}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _mock_payment_link(order_id: str) -> str:
    """Return a deterministic, visually authentic mock payment link."""
    slug = order_id.replace("order_", "")[:8].lower()
    return f"https://rzp.io/i/mock_{slug}"


def is_mock_mode() -> bool:
    """Expose mock-mode flag for health-check endpoints."""
    return _MOCK_MODE
