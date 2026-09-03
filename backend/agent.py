"""
agent.py — Gemini-powered structured policy engine.

Uses the official google-genai SDK to call gemini-3.5-flash with a strict
Pydantic schema so the model returns machine-parseable JSON every time.

Falls back to a deterministic rule-based plan if:
  - GEMINI_API_KEY is absent
  - The network call fails
  - The response cannot be parsed
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
load_dotenv()  # loads .env from cwd

from models import FailedPaymentEvent, LLMRecoveryPlan

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client bootstrap
# ---------------------------------------------------------------------------

_GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
_genai_client: Any = None

if _GEMINI_API_KEY:
    try:
        from google import genai  # type: ignore[import]
        from google.genai import types as genai_types  # type: ignore[import]
        _genai_client = genai.Client(api_key=_GEMINI_API_KEY)
        logger.info("Gemini client initialised (gemini-3.5-flash).")
    except Exception as exc:  # noqa: BLE001
        logger.warning("google-genai init failed (%s); LLM will use rule-based fallback.", exc)
else:
    logger.info(
        "GEMINI_API_KEY not set — agent will use deterministic rule-based fallback."
    )

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are Razorpay's autonomous Revenue Recovery Policy Agent — a specialist in
payment failure triage and intelligent dunning orchestration.

## YOUR ROLE
You receive structured data about a failed payment event and must output a
precise, actionable recovery policy in the exact JSON schema provided.

## PAYMENT FAILURE TAXONOMY

| Error Pattern                     | Root Cause Classification         |
|-----------------------------------|-----------------------------------|
| TIMED_OUT, GATEWAY_ERROR,         |                                   |
| SERVER_ERROR, NETWORK_ERROR       | GATEWAY_TECHNICAL_FAILURE         |
| INSUFFICIENT_FUNDS, LOW_BALANCE,  |                                   |
| PAYMENT_FAILED, CREDIT_LIMIT      | CUSTOMER_BALANCE_DEFICIT          |
| OTP_EXPIRED, OTP_INCORRECT,       |                                   |
| SESSION_EXPIRED, ABANDONED        | AUTHENTICATION_ABANDONMENT        |
| RISK_THRESHOLD, VELOCITY_BREACH,  |                                   |
| FRAUD_SUSPECTED, BLOCKED          | SUSPECTED_RISK                    |

## STRATEGY RULES (ADVISORY — deterministic guardrails will enforce hard limits)

1. GATEWAY_TECHNICAL_FAILURE → prefer SILENT_BACKGROUND_RETRY with 300–900s cooldown.
   Do NOT contact the customer; the failure is not their fault.

2. CUSTOMER_BALANCE_DEFICIT → prefer DISPATCH_DYNAMIC_PAYMENT_LINK via SMS
   with an empathetic Hinglish message. Nudge gently, only once.

3. AUTHENTICATION_ABANDONMENT → prefer DISPATCH_DYNAMIC_PAYMENT_LINK.
   The customer likely wants to pay but got confused. A friendly reminder helps.

4. SUSPECTED_RISK → HALT_AND_ABORT. Never automate recovery for risk flags.
   Manual review is required.

5. If attempts_made >= 3 → always recommend HALT_AND_ABORT regardless of cause.

6. VIP customers receive a premium-feel message.
   REPEAT_DROPOFF customers need a slightly more persuasive tone.

## AMOUNT RULES
- You MUST NOT modify, suggest modifying, or reference changing the transaction amount.
- Amounts are immutable.

## NUDGE MESSAGE STYLE
- Language: Hinglish (natural mix of Hindi and English, written in Roman script).
- Tone: Warm, respectful, not pushy. Never create urgency anxiety.
- Max 2 sentences.
- Include the first name of the customer.
- Example: "Priya ji, aapka Rs.2,500 ka payment complete nahi hua. 
  Is link se 2 minute mein retry karein — hum ready hain!"

## OUTPUT
Return ONLY valid JSON matching the provided schema. No markdown, no commentary."""

# ---------------------------------------------------------------------------
# Main inference entry point
# ---------------------------------------------------------------------------

def evaluate_failure_policy(event: FailedPaymentEvent) -> LLMRecoveryPlan:
    """
    Analyse a failed payment event and return a structured LLMRecoveryPlan.

    Tries the Gemini API first; falls back to deterministic rules on any failure.
    """
    if _genai_client is not None:
        try:
            return _call_gemini(event)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Gemini inference failed for order %s: %s — using fallback.",
                event.order_id,
                exc,
            )

    return _deterministic_fallback(event)


# ---------------------------------------------------------------------------
# Gemini call
# ---------------------------------------------------------------------------

def _build_user_prompt(event: FailedPaymentEvent) -> str:
    amount_inr = event.amount / 100
    return f"""Analyse this failed payment and produce a recovery plan.

## Failed Payment Event

- Order ID       : {event.order_id}
- Payment ID     : {event.payment_id}
- Amount         : Rs.{amount_inr:,.2f} ({event.amount} paise)
- Currency       : {event.currency}
- Error Code     : {event.error_code}
- Error Desc     : {event.error_description}
- Customer       : {event.customer_name}
- Phone          : {event.customer_phone}
- Email          : {event.customer_email}
- Tier           : {event.customer_tier}
- Attempts Made  : {event.attempts_made}
- Is Mandate     : {event.is_mandate}

Apply the taxonomy and strategy rules from your system instructions.
Return only the JSON policy object."""


def _call_gemini(event: FailedPaymentEvent) -> LLMRecoveryPlan:
    """Call gemini-3.5-flash with strict JSON schema enforcement."""
    from google import genai  # type: ignore[import]
    from google.genai import types as genai_types  # type: ignore[import]

    response = _genai_client.models.generate_content(
        model="gemini-3.5-flash",
        contents=[
            genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=_build_user_prompt(event))],
            )
        ],
        config=genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=1.0,
            thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
            response_mime_type="application/json",
            response_schema=LLMRecoveryPlan,
        ),
    )

    raw_text: str = response.text
    logger.debug("Gemini raw response for order %s: %s", event.order_id, raw_text[:300])

    # Parse and validate via Pydantic
    plan = LLMRecoveryPlan.model_validate_json(raw_text)
    logger.info(
        "Gemini plan for order %s: strategy=%s, cause=%s, confidence=%.2f",
        event.order_id,
        plan.recommended_strategy,
        plan.root_cause_classification,
        plan.confidence_score,
    )
    return plan


# ---------------------------------------------------------------------------
# Deterministic fallback — no external dependency
# ---------------------------------------------------------------------------

_GATEWAY_ERRORS: frozenset[str] = frozenset(
    {
        "BAD_REQUEST_PAYMENT_TIMED_OUT",
        "GATEWAY_ERROR",
        "SERVER_ERROR",
        "NETWORK_ERROR",
        "BAD_REQUEST_PAYMENT_GATEWAY_TECHNICAL_ERROR",
        "BAD_REQUEST_PAYMENT_BANK_SYSTEM_ERROR",
    }
)
_BALANCE_ERRORS: frozenset[str] = frozenset(
    {
        "BAD_REQUEST_PAYMENT_CARD_INSUFFICIENT_FUNDS",
        "INSUFFICIENT_FUNDS",
        "BAD_REQUEST_INSUFFICIENT_FUNDS",
        "LOW_BALANCE",
        "CREDIT_LIMIT_EXCEEDED",
    }
)
_AUTH_ERRORS: frozenset[str] = frozenset(
    {
        "BAD_REQUEST_PAYMENT_OTP_EXPIRED",
        "BAD_REQUEST_PAYMENT_OTP_INCORRECT",
        "BAD_REQUEST_PAYMENT_OTP_VALIDATION_REQUIRED",
        "SESSION_EXPIRED",
        "AUTHENTICATION_FAILED",
        "BAD_REQUEST_USER_NOT_AUTHENTICATED",
        "BAD_REQUEST_PAYMENT_CARD_HOLDER_AUTHENTICATION_FAILED",
    }
)
_RISK_ERRORS: frozenset[str] = frozenset(
    {
        "RISK_THRESHOLD",
        "VELOCITY_BREACH",
        "FRAUD_SUSPECTED",
        "BLOCKED",
        "BAD_REQUEST_PAYMENT_POSSIBLE_FRAUD",
        "BAD_REQUEST_FRAUD_GATEWAY_DECLINED",
    }
)


def _deterministic_fallback(event: FailedPaymentEvent) -> LLMRecoveryPlan:
    """
    Rule-based recovery plan used when Gemini is unavailable.
    Mirrors the taxonomy and strategies described in the system prompt.
    """
    code = event.error_code.upper()

    # --- Classify ---
    if any(err in code for err in ["TIMEOUT", "TIMED_OUT", "GATEWAY", "SERVER_ERROR", "NETWORK"]):
        cause = "GATEWAY_TECHNICAL_FAILURE"
    elif code in _GATEWAY_ERRORS:
        cause = "GATEWAY_TECHNICAL_FAILURE"
    elif any(err in code for err in ["INSUFFICIENT", "BALANCE", "CREDIT_LIMIT"]):
        cause = "CUSTOMER_BALANCE_DEFICIT"
    elif code in _BALANCE_ERRORS:
        cause = "CUSTOMER_BALANCE_DEFICIT"
    elif any(err in code for err in ["OTP", "SESSION", "AUTHENTICATION", "ABANDONED"]):
        cause = "AUTHENTICATION_ABANDONMENT"
    elif code in _AUTH_ERRORS:
        cause = "AUTHENTICATION_ABANDONMENT"
    elif any(err in code for err in ["RISK", "FRAUD", "BLOCKED", "VELOCITY"]):
        cause = "SUSPECTED_RISK"
    elif code in _RISK_ERRORS:
        cause = "SUSPECTED_RISK"
    else:
        # Default: treat unknown errors as authentication abandonment
        cause = "AUTHENTICATION_ABANDONMENT"

    # --- Select strategy ---
    if event.attempts_made >= 3:
        return LLMRecoveryPlan(
            root_cause=cause, root_cause_classification=cause,
            strategy="HALT_AND_ABORT", recommended_strategy="HALT_AND_ABORT",
            channel="NONE", recommended_channel="NONE",
            cooldown_seconds=0,
            confidence_score=0.99,
            nudge_message="",
            technical_reasoning=(
                f"Deterministic fallback: attempts_made={event.attempts_made} "
                f"exceeds hard ceiling of 3. Halting."
            ),
        )

    if cause == "GATEWAY_TECHNICAL_FAILURE":
        return LLMRecoveryPlan(
            root_cause=cause, root_cause_classification=cause,
            strategy="SILENT_BACKGROUND_RETRY", recommended_strategy="SILENT_BACKGROUND_RETRY",
            channel="NONE", recommended_channel="NONE",
            cooldown_seconds=600,
            confidence_score=0.92,
            nudge_message="",
            technical_reasoning=(
                "Gateway/bank technical failure detected. Silent retry after cooldown; "
                "customer notification suppressed (not customer fault)."
            ),
        )

    if cause == "SUSPECTED_RISK":
        return LLMRecoveryPlan(
            root_cause=cause, root_cause_classification=cause,
            strategy="HALT_AND_ABORT", recommended_strategy="HALT_AND_ABORT",
            channel="NONE", recommended_channel="NONE",
            cooldown_seconds=0,
            confidence_score=0.97,
            nudge_message="",
            technical_reasoning=(
                "Risk/fraud signal detected. Automated recovery halted; "
                "manual risk-team review required."
            ),
        )

    # Customer balance deficit or authentication abandonment → dispatch link
    first_name = event.customer_name.split()[0] if event.customer_name else "Customer"
    amount_inr = int(event.amount / 100)
    channel = "SMS"

    if cause == "AUTHENTICATION_ABANDONMENT":
        nudge = (
            f"{first_name} ji, aapka Rs.{amount_inr:,} ka payment almost complete tha! "
            f"Is link se sirf 1 minute mein complete karein."
        )
        cooldown = 120
    else:  # CUSTOMER_BALANCE_DEFICIT
        nudge = (
            f"{first_name} ji, aapka Rs.{amount_inr:,} ka payment process nahi ho saka. "
            f"Kripya doosre payment method se try karein — link ready hai!"
        )
        cooldown = 300

    return LLMRecoveryPlan(
        root_cause=cause, root_cause_classification=cause,
        strategy="DISPATCH_DYNAMIC_PAYMENT_LINK", recommended_strategy="DISPATCH_DYNAMIC_PAYMENT_LINK",
        channel=channel, recommended_channel=channel,
        cooldown_seconds=cooldown,
        confidence_score=0.85,
        nudge_message=nudge,
        technical_reasoning=(
            f"Deterministic fallback: cause={cause}, tier={event.customer_tier}. "
            f"Dispatching payment link via {channel}."
        ),
    )


def is_live() -> bool:
    return _genai_client is not None
