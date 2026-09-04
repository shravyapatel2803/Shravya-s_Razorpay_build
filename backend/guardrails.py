"""
guardrails.py — Deterministic, non-negotiable fintech business rules.

The guardrail engine sits BETWEEN the LLM output and execution.  It is the
single source of truth for compliance constraints.  The LLM is creative;
the guardrail engine is authoritative.

enforce_guardrails() is a pure function: it takes a plan, applies rules in
priority order, and returns the (possibly mutated) plan plus an audit trail.
"""

from __future__ import annotations

import copy
import logging
import re
import threading
import time
from collections import defaultdict, deque
from typing import Deque

from models import FailedPaymentEvent, LLMRecoveryPlan

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Threshold constants — centralised so they can be adjusted without hunting
# ---------------------------------------------------------------------------
MAX_RETRY_ATTEMPTS: int = 3          # Rule 1 — anti-fatigue ceiling
TECHNICAL_MIN_COOLDOWN_S: int = 300  # Rule 2 — minimum cooldown for gateway failures
HIGH_VALUE_THRESHOLD_PAISE: int = 5_000_000  # Rule 3 — Rs.50,000

# ---------------------------------------------------------------------------
# Rule 5 — Issuer Outage Circuit Breaker constants
# ---------------------------------------------------------------------------
CIRCUIT_BREAKER_WINDOW_S: int = 300        # 5-minute sliding window
CIRCUIT_BREAKER_THRESHOLD: int = 3         # >3 failures trips the breaker
CIRCUIT_BREAKER_COOLDOWN_S: int = 1_800    # 30-minute breaker cooldown

# ---------------------------------------------------------------------------
# Circuit Breaker State (in-memory, thread-safe)
# Maps issuer_code -> deque of failure timestamps (float epoch seconds)
# Maps issuer_code -> trip_timestamp (float epoch seconds) or None
# ---------------------------------------------------------------------------
_cb_lock = threading.Lock()
_issuer_failure_times: dict[str, Deque[float]] = defaultdict(deque)
_issuer_tripped_at: dict[str, float] = {}


def _extract_issuer_code(error_code: str) -> str:
    """
    Derive a canonical issuer token from the raw error_code string.
    Examples:
      'GATEWAY_ERROR_BANK_SYSTEM_ERROR'  -> 'BANK_SYSTEM_ERROR'
      'GATEWAY_ERROR_HDFC_SYSTEM_DOWN'   -> 'HDFC_SYSTEM_DOWN'
      'BAD_REQUEST_PAYMENT_OTP_EXPIRED'  -> 'OTHER'
    Only GATEWAY_ERROR_* codes contribute to the circuit breaker.
    """
    m = re.match(r"GATEWAY_ERROR_(.+)", error_code)
    if m:
        return m.group(1)
    return "OTHER"


def record_issuer_failure(error_code: str) -> None:
    """
    Record a failure for the issuer inferred from error_code.
    Call this BEFORE enforce_guardrails so the counter is always current.
    """
    issuer = _extract_issuer_code(error_code)
    if issuer == "OTHER":
        return  # Only track gateway/issuer-level failures
    now = time.monotonic()
    with _cb_lock:
        dq = _issuer_failure_times[issuer]
        dq.append(now)
        # Evict entries outside the sliding window
        cutoff = now - CIRCUIT_BREAKER_WINDOW_S
        while dq and dq[0] < cutoff:
            dq.popleft()
        # Trip the breaker if threshold exceeded and not already tripped
        if len(dq) > CIRCUIT_BREAKER_THRESHOLD and issuer not in _issuer_tripped_at:
            _issuer_tripped_at[issuer] = now
            logger.warning(
                "[CircuitBreaker] Issuer '%s' tripped — %d failures in %.0fs window. "
                "Suppressing all notifications for %ds.",
                issuer, len(dq), CIRCUIT_BREAKER_WINDOW_S, CIRCUIT_BREAKER_COOLDOWN_S,
            )


def is_circuit_open(error_code: str) -> bool:
    """Return True if the circuit breaker is currently tripped for this issuer."""
    issuer = _extract_issuer_code(error_code)
    if issuer == "OTHER":
        return False
    now = time.monotonic()
    with _cb_lock:
        tripped_at = _issuer_tripped_at.get(issuer)
        if tripped_at is None:
            return False
        if now - tripped_at >= CIRCUIT_BREAKER_COOLDOWN_S:
            # Auto-reset after cooldown
            del _issuer_tripped_at[issuer]
            _issuer_failure_times[issuer].clear()
            logger.info(
                "[CircuitBreaker] Issuer '%s' recovered — circuit reset after %ds cooldown.",
                issuer, CIRCUIT_BREAKER_COOLDOWN_S,
            )
            return False
        return True


def get_circuit_breaker_status() -> dict[str, dict]:
    """
    Return a snapshot of all issuer circuit breaker states.
    Useful for health-check / admin endpoints.
    """
    now = time.monotonic()
    with _cb_lock:
        result = {}
        for issuer, dq in _issuer_failure_times.items():
            tripped_at = _issuer_tripped_at.get(issuer)
            result[issuer] = {
                "failures_in_window": len(dq),
                "tripped": tripped_at is not None,
                "cooldown_remaining_s": max(
                    0, CIRCUIT_BREAKER_COOLDOWN_S - (now - tripped_at)
                ) if tripped_at else 0,
            }
    return result


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def enforce_guardrails(
    event: FailedPaymentEvent,
    plan: LLMRecoveryPlan,
) -> tuple[LLMRecoveryPlan, bool, str | None]:
    """
    Apply deterministic compliance rules to an LLM-generated recovery plan.

    Parameters
    ----------
    event : FailedPaymentEvent
        The original payment failure context.
    plan : LLMRecoveryPlan
        The plan produced by the Gemini agent (may be mutated).

    Returns
    -------
    (final_plan, was_overridden, override_reason)
        final_plan      : LLMRecoveryPlan — the approved (and possibly modified) plan.
        was_overridden  : bool            — True if any rule fired.
        override_reason : str | None      — Concatenated explanation of all rules that fired.
    """
    # Work on a deep copy so the original plan remains traceable in logs
    final_plan = copy.deepcopy(plan)
    override_reasons: list[str] = []

    # -----------------------------------------------------------------------
    # Rule 1 — Anti-Fatigue Ceiling
    # Hard ceiling: once an order has reached MAX_RETRY_ATTEMPTS recovery
    # interventions, no further automated actions are permitted.
    # -----------------------------------------------------------------------
    if (
        event.attempts_made >= MAX_RETRY_ATTEMPTS
        and final_plan.recommended_strategy != "HALT_AND_ABORT"
    ):
        msg = (
            f"[Rule 1] Hard ceiling: Max {MAX_RETRY_ATTEMPTS} retry interventions reached "
            f"(attempts_made={event.attempts_made}). Strategy forced to HALT_AND_ABORT."
        )
        logger.warning(msg)
        final_plan.recommended_strategy = "HALT_AND_ABORT"
        final_plan.recommended_channel = "NONE"
        final_plan.nudge_message = ""
        override_reasons.append(msg)

    # -----------------------------------------------------------------------
    # Rule 2 — Anti-Disturbance / Technical Outage
    # Bank or gateway technical failures are not the customer's fault.
    # Pinging customers for issues they cannot resolve creates noise and
    # damages brand trust.  Force a silent background retry with adequate
    # cooldown.
    # -----------------------------------------------------------------------
    if final_plan.root_cause_classification == "GATEWAY_TECHNICAL_FAILURE":
        changed = False
        parts: list[str] = []
        if final_plan.recommended_channel != "NONE":
            final_plan.recommended_channel = "NONE"
            final_plan.nudge_message = ""
            parts.append("channel forced to NONE (no customer contact for gateway failures)")
            changed = True
        if final_plan.recommended_strategy not in (
            "SILENT_BACKGROUND_RETRY",
            "HALT_AND_ABORT",
        ):
            final_plan.recommended_strategy = "SILENT_BACKGROUND_RETRY"
            parts.append("strategy forced to SILENT_BACKGROUND_RETRY")
            changed = True
        if final_plan.cooldown_seconds < TECHNICAL_MIN_COOLDOWN_S:
            final_plan.cooldown_seconds = TECHNICAL_MIN_COOLDOWN_S
            parts.append(
                f"cooldown raised to minimum {TECHNICAL_MIN_COOLDOWN_S}s for technical failures"
            )
            changed = True
        if changed:
            msg = f"[Rule 2] GATEWAY_TECHNICAL_FAILURE: {'; '.join(parts)}."
            logger.warning(msg)
            override_reasons.append(msg)

    # -----------------------------------------------------------------------
    # Rule 3 — High-Value Transaction Verification Guard
    # For transactions above Rs.50,000, ensure channel is verified and not NONE
    # when dynamic payment links are dispatched.
    # -----------------------------------------------------------------------
    if (
        event.amount > HIGH_VALUE_THRESHOLD_PAISE
        and final_plan.recommended_strategy == "DISPATCH_DYNAMIC_PAYMENT_LINK"
        and final_plan.recommended_channel == "NONE"
    ):
        final_plan.recommended_channel = "SMS"
        msg = (
            f"[Rule 3] High-value order (Rs.{event.amount / 100:,.0f}): "
            f"Recovery channel mandated for high-ticket transaction."
        )
        logger.warning(msg)
        override_reasons.append(msg)

    # -----------------------------------------------------------------------
    # Rule 4 — Amount Immutability (defensive sanity check)
    # The LLM schema does not expose amount fields, but we log a hard assertion
    # here as a future-proofing guard.  If this assertion ever fails something
    # has gone deeply wrong upstream.
    # -----------------------------------------------------------------------
    # (No LLM field to mutate; this rule is enforced by schema design.)

    # -----------------------------------------------------------------------
    # Rule 5 — Issuer Outage Circuit Breaker
    # If more than CIRCUIT_BREAKER_THRESHOLD transactions from the same issuer
    # fail within CIRCUIT_BREAKER_WINDOW_S seconds, trip the circuit breaker
    # for CIRCUIT_BREAKER_COOLDOWN_S seconds.  During this window, all events
    # from the affected issuer are forced into SILENT_BACKGROUND_RETRY and all
    # buyer notifications are suppressed.  This prevents burning merchant
    # WhatsApp budget during bank-side outages (e.g. HDFC / SBI core banking
    # downtime) and avoids frustrating buyers with messages they cannot act on.
    # -----------------------------------------------------------------------
    if is_circuit_open(event.error_code):
        issuer = _extract_issuer_code(event.error_code)
        parts_cb: list[str] = []
        changed_cb = False

        if final_plan.recommended_strategy not in (
            "SILENT_BACKGROUND_RETRY",
            "HALT_AND_ABORT",
        ):
            final_plan.recommended_strategy = "SILENT_BACKGROUND_RETRY"
            parts_cb.append("strategy forced to SILENT_BACKGROUND_RETRY")
            changed_cb = True

        if final_plan.recommended_channel != "NONE":
            final_plan.recommended_channel = "NONE"
            final_plan.nudge_message = ""
            parts_cb.append("buyer notification suppressed (issuer circuit open)")
            changed_cb = True

        if final_plan.cooldown_seconds < CIRCUIT_BREAKER_COOLDOWN_S:
            final_plan.cooldown_seconds = CIRCUIT_BREAKER_COOLDOWN_S
            parts_cb.append(
                f"cooldown raised to {CIRCUIT_BREAKER_COOLDOWN_S}s (circuit breaker duration)"
            )
            changed_cb = True

        if changed_cb:
            msg = (
                f"[Rule 5] Circuit breaker OPEN for issuer '{issuer}': "
                f"{'; '.join(parts_cb)}. "
                f"Bank outage detected — retrying silently for {CIRCUIT_BREAKER_COOLDOWN_S // 60}min."
            )
            logger.warning(msg)
            override_reasons.append(msg)

    was_overridden = len(override_reasons) > 0
    override_reason: str | None = (
        " | ".join(override_reasons) if was_overridden else None
    )

    return final_plan, was_overridden, override_reason
