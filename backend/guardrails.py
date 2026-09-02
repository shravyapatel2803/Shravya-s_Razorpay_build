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

from models import FailedPaymentEvent, LLMRecoveryPlan

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Threshold constants — centralised so they can be adjusted without hunting
# ---------------------------------------------------------------------------
MAX_RETRY_ATTEMPTS: int = 3          # Rule 1 — anti-fatigue ceiling
TECHNICAL_MIN_COOLDOWN_S: int = 300  # Rule 2 — minimum cooldown for gateway failures
HIGH_VALUE_THRESHOLD_PAISE: int = 5_000_000  # Rule 3 — Rs.50,000


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
    # Rule 3 — High-Value Channel Security
    # SMS is susceptible to spoofing / SIM-swap attacks.  For transactions
    # above Rs.50,000, mandate WhatsApp which provides richer, verified UI
    # and end-to-end encryption.
    # -----------------------------------------------------------------------
    if (
        event.amount > HIGH_VALUE_THRESHOLD_PAISE
        and final_plan.recommended_channel == "SMS"
    ):
        final_plan.recommended_channel = "WHATSAPP"
        msg = (
            f"[Rule 3] High-value order (Rs.{event.amount / 100:,.0f}): "
            f"SMS channel overridden to WHATSAPP (anti-spoofing policy)."
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

    was_overridden = len(override_reasons) > 0
    override_reason: str | None = (
        " | ".join(override_reasons) if was_overridden else None
    )

    return final_plan, was_overridden, override_reason
