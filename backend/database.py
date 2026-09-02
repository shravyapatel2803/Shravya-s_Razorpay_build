"""
database.py (v2) - SQLite audit ledger for the Autonomous Payment Recovery & Dunning Orchestrator.

Adds:
  - retry_at / retry_count columns on recovery_audit_log (scheduler support)
  - notification_sent / notification_channel columns (notifications support)
  - recovery_notifications table (per-message delivery receipts)
  - get_pending_retries()    -- scheduler polling
  - mark_retry_dispatched()  -- scheduler state update
  - log_notification()       -- notification receipt
  - get_notification_stats() -- rate-limit helper
  - Analytics query helpers used by analytics.py
"""

from __future__ import annotations

import datetime
import sqlite3
from contextlib import contextmanager
from typing import Generator

from models import FailedPaymentEvent, paise_to_rupees

DB_PATH = "recovery_audit.db"


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

@contextmanager
def _get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema bootstrap  (safe to call multiple times -- uses IF NOT EXISTS)
# ---------------------------------------------------------------------------

def init_db() -> None:
    with _get_conn() as conn:
        # Main audit table -- new columns added with ALTER TABLE if missing
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recovery_audit_log (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id            TEXT    NOT NULL,
                payment_id          TEXT    NOT NULL DEFAULT '',
                amount_paise        INTEGER NOT NULL,
                error_code          TEXT    NOT NULL,
                customer_tier       TEXT    NOT NULL DEFAULT 'STANDARD',
                customer_phone      TEXT    NOT NULL DEFAULT '',
                customer_name       TEXT    NOT NULL DEFAULT '',
                customer_email      TEXT    NOT NULL DEFAULT '',
                attempts            INTEGER NOT NULL DEFAULT 0,
                ai_strategy         TEXT    NOT NULL,
                final_action        TEXT    NOT NULL,
                guardrail_override  INTEGER NOT NULL DEFAULT 0,
                override_reason     TEXT,
                payment_link_url    TEXT,
                status              TEXT    NOT NULL,
                -- scheduler columns
                retry_at            TEXT,
                retry_count         INTEGER NOT NULL DEFAULT 0,
                cooldown_seconds    INTEGER NOT NULL DEFAULT 0,
                -- notification columns
                notification_sent   INTEGER NOT NULL DEFAULT 0,
                notification_channel TEXT,
                notification_status TEXT,
                created_at          TEXT    NOT NULL
            )
            """
        )

        # Migrate existing DBs that lack the new columns
        existing_cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(recovery_audit_log)").fetchall()
        }
        new_cols = {
            "customer_phone":       "TEXT    NOT NULL DEFAULT ''",
            "customer_name":        "TEXT    NOT NULL DEFAULT ''",
            "customer_email":       "TEXT    NOT NULL DEFAULT ''",
            "retry_at":             "TEXT",
            "retry_count":          "INTEGER NOT NULL DEFAULT 0",
            "cooldown_seconds":     "INTEGER NOT NULL DEFAULT 0",
            "notification_sent":    "INTEGER NOT NULL DEFAULT 0",
            "notification_channel": "TEXT",
            "notification_status":  "TEXT",
        }
        for col, defn in new_cols.items():
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE recovery_audit_log ADD COLUMN {col} {defn}")

        # Index for idempotency look-ups
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_order_id ON recovery_audit_log (order_id)"
        )
        # Index for scheduler polling
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_status_retry ON recovery_audit_log (status, retry_at)"
        )

        # Notifications receipt table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recovery_notifications (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id         TEXT    NOT NULL,
                customer_phone   TEXT    NOT NULL,
                channel          TEXT    NOT NULL,
                message_preview  TEXT,
                payment_link_url TEXT,
                delivery_status  TEXT    NOT NULL DEFAULT 'QUEUED',
                provider_ref     TEXT,
                sent_at          TEXT    NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_notif_phone ON recovery_notifications (customer_phone, sent_at)"
        )


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

def log_recovery(
    event: FailedPaymentEvent,
    ai_strategy: str,
    final_action: str,
    overridden: bool,
    override_reason: str | None,
    payment_link_url: str | None,
    status: str,
    cooldown_seconds: int = 0,
) -> None:
    now = _utcnow()
    retry_at: str | None = None
    if status == "SCHEDULED_RETRY" and cooldown_seconds > 0:
        retry_at = (
            datetime.datetime.utcnow()
            + datetime.timedelta(seconds=cooldown_seconds)
        ).isoformat(timespec="seconds") + "Z"

    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO recovery_audit_log
                (order_id, payment_id, amount_paise, error_code, customer_tier,
                 customer_phone, customer_name, customer_email,
                 attempts, ai_strategy, final_action, guardrail_override,
                 override_reason, payment_link_url, status,
                 retry_at, cooldown_seconds, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.order_id, event.payment_id, event.amount, event.error_code,
                event.customer_tier, event.customer_phone, event.customer_name,
                event.customer_email, event.attempts_made, ai_strategy, final_action,
                1 if overridden else 0, override_reason, payment_link_url, status,
                retry_at, cooldown_seconds, now,
            ),
        )


def update_notification_status(
    order_id: str,
    sent: bool,
    channel: str | None,
    notif_status: str,
) -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            UPDATE recovery_audit_log
            SET notification_sent = ?,
                notification_channel = ?,
                notification_status  = ?
            WHERE order_id = ?
            """,
            (1 if sent else 0, channel, notif_status, order_id),
        )


def mark_retry_dispatched(order_id: str, new_status: str) -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            UPDATE recovery_audit_log
            SET status      = ?,
                retry_count = retry_count + 1,
                retry_at    = NULL
            WHERE order_id = ?
            """,
            (new_status, order_id),
        )


def log_notification(
    order_id: str,
    phone: str,
    channel: str,
    message_preview: str,
    payment_link_url: str | None,
    delivery_status: str,
    provider_ref: str | None = None,
) -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO recovery_notifications
                (order_id, customer_phone, channel, message_preview,
                 payment_link_url, delivery_status, provider_ref, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id, phone, channel, message_preview[:200],
                payment_link_url, delivery_status, provider_ref, _utcnow(),
            ),
        )


# ---------------------------------------------------------------------------
# Idempotency guard
# ---------------------------------------------------------------------------

def is_order_active_or_resolved(order_id: str) -> bool:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM recovery_audit_log WHERE order_id = ? LIMIT 1",
            (order_id,),
        ).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# Scheduler helpers
# ---------------------------------------------------------------------------

def get_pending_retries(now_iso: str) -> list[dict]:
    """
    Return all SCHEDULED_RETRY rows whose retry_at timestamp is <= now.
    These are ready to be re-dispatched by the background scheduler.
    """
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                order_id, payment_id, amount_paise, error_code,
                customer_tier, customer_phone, customer_name, customer_email,
                attempts, retry_count, cooldown_seconds
            FROM recovery_audit_log
            WHERE status = 'SCHEDULED_RETRY'
              AND retry_at IS NOT NULL
              AND retry_at <= ?
            ORDER BY retry_at ASC
            LIMIT 50
            """,
            (now_iso,),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Notification rate-limit helper
# ---------------------------------------------------------------------------

def get_notification_count_last_24h(phone: str) -> int:
    cutoff = (
        datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    ).isoformat(timespec="seconds") + "Z"
    with _get_conn() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM recovery_notifications
            WHERE customer_phone = ? AND sent_at >= ?
            """,
            (phone, cutoff),
        ).fetchone()
    return row["cnt"] if row else 0


# ---------------------------------------------------------------------------
# Payment success confirmation
# ---------------------------------------------------------------------------

def mark_order_fully_recovered(order_id: str) -> bool:
    """
    Mark an order as FULLY_RECOVERED when Razorpay fires payment.captured.
    Returns True if the row was found and updated.
    """
    with _get_conn() as conn:
        cur = conn.execute(
            """
            UPDATE recovery_audit_log
            SET status = 'FULLY_RECOVERED'
            WHERE order_id = ?
              AND status IN ('RECOVERED_PENDING_PAYMENT', 'SCHEDULED_RETRY')
            """,
            (order_id,),
        )
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

def get_metrics() -> dict:
    with _get_conn() as conn:
        total_row = conn.execute(
            "SELECT COUNT(*) AS cnt, SUM(amount_paise) AS total FROM recovery_audit_log"
        ).fetchone()
        recovered_row = conn.execute(
            "SELECT SUM(amount_paise) AS s FROM recovery_audit_log WHERE status = 'RECOVERED_PENDING_PAYMENT'"
        ).fetchone()
        fully_row = conn.execute(
            "SELECT SUM(amount_paise) AS s FROM recovery_audit_log WHERE status = 'FULLY_RECOVERED'"
        ).fetchone()
        scheduled_row = conn.execute(
            "SELECT SUM(amount_paise) AS s FROM recovery_audit_log WHERE status = 'SCHEDULED_RETRY'"
        ).fetchone()
        aborted_row = conn.execute(
            "SELECT SUM(amount_paise) AS s FROM recovery_audit_log WHERE status = 'ABORTED'"
        ).fetchone()
        override_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM recovery_audit_log WHERE guardrail_override = 1"
        ).fetchone()
        success_count_row = conn.execute(
            """
            SELECT COUNT(*) AS cnt FROM recovery_audit_log
            WHERE status IN ('RECOVERED_PENDING_PAYMENT', 'SCHEDULED_RETRY', 'FULLY_RECOVERED')
            """
        ).fetchone()
        notif_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM recovery_notifications"
        ).fetchone()

    total_events = total_row["cnt"] or 0
    total_paise  = total_row["total"] or 0
    success_count = success_count_row["cnt"] or 0
    recovery_rate = round(success_count / total_events * 100, 2) if total_events else 0.0

    return {
        "total_events_processed":        total_events,
        "total_gmv_at_risk_inr":         paise_to_rupees(total_paise),
        "total_gmv_recovered_inr":       paise_to_rupees(recovered_row["s"] or 0),
        "total_gmv_fully_recovered_inr": paise_to_rupees(fully_row["s"] or 0),
        "total_gmv_scheduled_inr":       paise_to_rupees(scheduled_row["s"] or 0),
        "total_gmv_aborted_inr":         paise_to_rupees(aborted_row["s"] or 0),
        "guardrail_override_count":      override_row["cnt"] or 0,
        "total_notifications_sent":      notif_row["cnt"] or 0,
        "recovery_success_rate_pct":     recovery_rate,
    }


def get_recent_logs(limit: int = 20) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, order_id, payment_id, amount_paise, error_code,
                   customer_tier, customer_name, attempts, ai_strategy,
                   final_action, guardrail_override, override_reason,
                   payment_link_url, status, retry_at, retry_count,
                   notification_sent, notification_channel, notification_status,
                   created_at
            FROM recovery_audit_log
            ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "id":                   r["id"],
            "order_id":             r["order_id"],
            "payment_id":           r["payment_id"],
            "amount_inr":           paise_to_rupees(r["amount_paise"]),
            "error_code":           r["error_code"],
            "customer_tier":        r["customer_tier"],
            "customer_name":        r["customer_name"],
            "attempts":             r["attempts"],
            "ai_strategy":          r["ai_strategy"],
            "final_action":         r["final_action"],
            "guardrail_overridden": bool(r["guardrail_override"]),
            "override_reason":      r["override_reason"],
            "payment_link_url":     r["payment_link_url"],
            "status":               r["status"],
            "retry_at":             r["retry_at"],
            "retry_count":          r["retry_count"],
            "notification_sent":    bool(r["notification_sent"]),
            "notification_channel": r["notification_channel"],
            "notification_status":  r["notification_status"],
            "created_at":           r["created_at"],
        }
        for r in rows
    ]


def get_notification_logs(limit: int = 50) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, order_id, customer_phone, channel, message_preview,
                   payment_link_url, delivery_status, provider_ref, sent_at
            FROM recovery_notifications
            ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Analytics helpers  (used by analytics.py)
# ---------------------------------------------------------------------------

def get_breakdown_by_error_code() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT error_code,
                   COUNT(*) AS count,
                   SUM(amount_paise) AS total_paise,
                   SUM(CASE WHEN status IN ('RECOVERED_PENDING_PAYMENT','FULLY_RECOVERED') THEN amount_paise ELSE 0 END) AS recovered_paise,
                   SUM(CASE WHEN status = 'ABORTED' THEN 1 ELSE 0 END) AS aborted_count
            FROM recovery_audit_log
            GROUP BY error_code
            ORDER BY total_paise DESC
            """
        ).fetchall()
    return [
        {
            "error_code":         r["error_code"],
            "count":              r["count"],
            "total_gmv_inr":      paise_to_rupees(r["total_paise"] or 0),
            "recovered_gmv_inr":  paise_to_rupees(r["recovered_paise"] or 0),
            "aborted_count":      r["aborted_count"],
        }
        for r in rows
    ]


def get_breakdown_by_strategy() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT ai_strategy,
                   COUNT(*) AS count,
                   SUM(amount_paise) AS total_paise,
                   COUNT(CASE WHEN guardrail_override = 1 THEN 1 END) AS guardrail_overrides
            FROM recovery_audit_log
            GROUP BY ai_strategy
            ORDER BY count DESC
            """
        ).fetchall()
    return [
        {
            "strategy":           r["ai_strategy"],
            "count":              r["count"],
            "total_gmv_inr":      paise_to_rupees(r["total_paise"] or 0),
            "guardrail_overrides": r["guardrail_overrides"],
        }
        for r in rows
    ]


def get_breakdown_by_tier() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT customer_tier,
                   COUNT(*) AS count,
                   SUM(amount_paise) AS total_paise,
                   SUM(CASE WHEN status IN ('RECOVERED_PENDING_PAYMENT','FULLY_RECOVERED') THEN amount_paise ELSE 0 END) AS recovered_paise,
                   ROUND(AVG(attempts), 2) AS avg_attempts
            FROM recovery_audit_log
            GROUP BY customer_tier
            ORDER BY total_paise DESC
            """
        ).fetchall()
    return [
        {
            "customer_tier":     r["customer_tier"],
            "count":             r["count"],
            "total_gmv_inr":     paise_to_rupees(r["total_paise"] or 0),
            "recovered_gmv_inr": paise_to_rupees(r["recovered_paise"] or 0),
            "avg_attempts":      r["avg_attempts"],
        }
        for r in rows
    ]


def get_hourly_events(hours: int = 24) -> list[dict]:
    cutoff = (
        datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    ).isoformat(timespec="seconds") + "Z"
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT strftime('%Y-%m-%dT%H:00:00Z', created_at) AS hour,
                   COUNT(*) AS event_count,
                   SUM(amount_paise) AS gmv_paise
            FROM recovery_audit_log
            WHERE created_at >= ?
            GROUP BY hour
            ORDER BY hour ASC
            """,
            (cutoff,),
        ).fetchall()
    return [
        {
            "hour":        r["hour"],
            "event_count": r["event_count"],
            "gmv_inr":     paise_to_rupees(r["gmv_paise"] or 0),
        }
        for r in rows
    ]


def get_guardrail_breakdown() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT override_reason,
                   COUNT(*) AS count,
                   SUM(amount_paise) AS total_paise
            FROM recovery_audit_log
            WHERE guardrail_override = 1
              AND override_reason IS NOT NULL
            GROUP BY override_reason
            ORDER BY count DESC
            """
        ).fetchall()
    return [
        {
            "rule":          r["override_reason"],
            "count":         r["count"],
            "gmv_affected_inr": paise_to_rupees(r["total_paise"] or 0),
        }
        for r in rows
    ]


def get_customer_profile(phone: str) -> dict:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT order_id, amount_paise, error_code, customer_tier,
                   customer_name, ai_strategy, status, created_at
            FROM recovery_audit_log
            WHERE customer_phone = ?
            ORDER BY created_at DESC
            """,
            (phone,),
        ).fetchall()
    if not rows:
        return {}
    events = [dict(r) for r in rows]
    total_paise = sum(r["amount_paise"] for r in events)
    recovered = sum(
        r["amount_paise"] for r in events
        if r["status"] in ("RECOVERED_PENDING_PAYMENT", "FULLY_RECOVERED")
    )
    return {
        "customer_name":     events[0]["customer_name"],
        "customer_tier":     events[0]["customer_tier"],
        "total_events":      len(events),
        "total_gmv_inr":     paise_to_rupees(total_paise),
        "recovered_gmv_inr": paise_to_rupees(recovered),
        "recovery_rate_pct": round(recovered / total_paise * 100, 1) if total_paise else 0.0,
        "recent_events":     events[:10],
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
