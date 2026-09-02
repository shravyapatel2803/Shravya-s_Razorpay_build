"""
notifications.py -- WhatsApp and SMS dispatch for recovery nudges.

Uses Twilio as the provider (real or mock fallback).
Rate-limit: max 3 notifications per customer phone per 24 hours.

Environment variables (all optional -- falls back to mock):
    TWILIO_ACCOUNT_SID
    TWILIO_AUTH_TOKEN
    TWILIO_FROM_WHATSAPP  (e.g. whatsapp:+14155238886)
    TWILIO_FROM_SMS       (e.g. +14155238886)
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass

import database

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider bootstrap
# ---------------------------------------------------------------------------

_TWILIO_SID    = os.getenv("TWILIO_ACCOUNT_SID")
_TWILIO_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
_FROM_WA       = os.getenv("TWILIO_FROM_WHATSAPP", "whatsapp:+14155238886")
_FROM_SMS      = os.getenv("TWILIO_FROM_SMS",       "+14155238886")
_MOCK_MODE     = not (_TWILIO_SID and _TWILIO_TOKEN)

_twilio_client = None
if not _MOCK_MODE:
    try:
        from twilio.rest import Client as TwilioClient  # type: ignore[import]
        _twilio_client = TwilioClient(_TWILIO_SID, _TWILIO_TOKEN)
        logger.info("Twilio client initialised (LIVE mode).")
    except Exception as exc:
        logger.warning("Twilio SDK init failed (%s); MOCK mode active.", exc)
        _MOCK_MODE = True
else:
    logger.info("Twilio credentials not set -- notifications running in MOCK mode.")

# Anti-spam: max notifications per customer per 24h
MAX_NOTIFICATIONS_PER_DAY = 3


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

@dataclass
class NotificationResult:
    sent:         bool
    channel:      str
    status:       str   # DELIVERED | QUEUED | RATE_LIMITED | MOCK_SENT | FAILED
    provider_ref: str | None
    reason:       str | None = None


def dispatch_nudge(
    order_id: str,
    channel: str,           # "WHATSAPP" or "SMS"
    phone: str,
    message: str,
    payment_link_url: str | None,
) -> NotificationResult:
    """
    Send a recovery nudge via the requested channel.
    Enforces per-customer rate limiting before dispatching.

    Returns a NotificationResult with delivery details.
    """
    # ------------------------------------------------------------------
    # Rate-limit check
    # ------------------------------------------------------------------
    count_24h = database.get_notification_count_last_24h(phone)
    if count_24h >= MAX_NOTIFICATIONS_PER_DAY:
        reason = (
            f"Rate limit: {count_24h} notifications already sent to {phone[-4:]}*** "
            f"in the last 24h (max {MAX_NOTIFICATIONS_PER_DAY})."
        )
        logger.warning("NOTIF | RATE_LIMITED | order=%s | %s", order_id, reason)
        database.log_notification(
            order_id=order_id, phone=phone, channel=channel,
            message_preview=message[:100], payment_link_url=payment_link_url,
            delivery_status="RATE_LIMITED",
        )
        return NotificationResult(sent=False, channel=channel, status="RATE_LIMITED",
                                  provider_ref=None, reason=reason)

    # Append payment link to the message if provided
    full_message = message
    if payment_link_url:
        full_message = message.rstrip() + "\n\n" + payment_link_url

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    if _MOCK_MODE:
        result = _mock_send(order_id, channel, phone, full_message)
    elif channel == "WHATSAPP":
        result = _twilio_whatsapp(order_id, phone, full_message)
    else:
        result = _twilio_sms(order_id, phone, full_message)

    # ------------------------------------------------------------------
    # Persist receipt
    # ------------------------------------------------------------------
    database.log_notification(
        order_id=order_id, phone=phone, channel=channel,
        message_preview=full_message[:200], payment_link_url=payment_link_url,
        delivery_status=result.status, provider_ref=result.provider_ref,
    )
    database.update_notification_status(
        order_id=order_id,
        sent=result.sent,
        channel=channel,
        notif_status=result.status,
    )
    return result


def is_mock_mode() -> bool:
    return _MOCK_MODE


# ---------------------------------------------------------------------------
# Twilio senders
# ---------------------------------------------------------------------------

def _twilio_whatsapp(order_id: str, phone: str, body: str) -> NotificationResult:
    to = f"whatsapp:{phone}" if not phone.startswith("whatsapp:") else phone
    try:
        msg = _twilio_client.messages.create(body=body, from_=_FROM_WA, to=to)
        logger.info("NOTIF | WHATSAPP | order=%s | sid=%s | status=%s", order_id, msg.sid, msg.status)
        return NotificationResult(sent=True, channel="WHATSAPP",
                                  status=msg.status.upper(), provider_ref=msg.sid)
    except Exception as exc:
        logger.error("NOTIF | WHATSAPP FAILED | order=%s | %s", order_id, exc)
        return NotificationResult(sent=False, channel="WHATSAPP",
                                  status="FAILED", provider_ref=None, reason=str(exc))


def _twilio_sms(order_id: str, phone: str, body: str) -> NotificationResult:
    try:
        msg = _twilio_client.messages.create(body=body, from_=_FROM_SMS, to=phone)
        logger.info("NOTIF | SMS | order=%s | sid=%s | status=%s", order_id, msg.sid, msg.status)
        return NotificationResult(sent=True, channel="SMS",
                                  status=msg.status.upper(), provider_ref=msg.sid)
    except Exception as exc:
        logger.error("NOTIF | SMS FAILED | order=%s | %s", order_id, exc)
        return NotificationResult(sent=False, channel="SMS",
                                  status="FAILED", provider_ref=None, reason=str(exc))


# ---------------------------------------------------------------------------
# Mock sender (dev / CI mode)
# ---------------------------------------------------------------------------

def _mock_send(order_id: str, channel: str, phone: str, body: str) -> NotificationResult:
    ref = "MOCK_" + uuid.uuid4().hex[:12].upper()
    logger.info(
        "NOTIF | MOCK_%s | order=%s | to=%s*** | ref=%s | preview=%s",
        channel, order_id, phone[-4:], ref, body[:60],
    )
    return NotificationResult(sent=True, channel=channel, status="MOCK_SENT", provider_ref=ref)
