"""
models.py — Pydantic v2 schemas for the Autonomous Payment Recovery & Dunning Orchestrator.
Covers inbound webhook events, structured LLM policy output, and final execution results.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Inbound event — emitted by Razorpay webhook or the simulation harness
# ---------------------------------------------------------------------------

class FailedPaymentEvent(BaseModel):
    """Represents a single failed payment that enters the recovery pipeline."""

    order_id: str = Field(
        ...,
        description="Razorpay Order ID (e.g. order_ABC123).",
        examples=["order_OjBCXKAFBOeRoZ"],
    )
    payment_id: str = Field(
        ...,
        description="Razorpay Payment ID of the failed attempt.",
        examples=["pay_OjBCXKAFBOeRoZ"],
    )
    amount: int = Field(
        ...,
        gt=0,
        description="Transaction amount in paise. 250000 == Rs.2,500.",
        examples=[250000],
    )
    currency: str = Field(default="INR", description="ISO 4217 currency code.")
    error_code: str = Field(
        ...,
        description="Machine-readable Razorpay error code.",
        examples=["BAD_REQUEST_PAYMENT_TIMED_OUT"],
    )
    error_description: str = Field(
        ...,
        description="Human-readable failure description from the gateway.",
    )
    customer_name: str = Field(..., description="Full name of the payer.")
    customer_phone: str = Field(..., description="E.164 phone number.")
    customer_email: str = Field(..., description="Payer email address.")
    customer_tier: Literal["STANDARD", "VIP", "REPEAT_DROPOFF"] = Field(
        ...,
        description=(
            "Customer segment. VIP = high-LTV, REPEAT_DROPOFF = known cart abandoner, "
            "STANDARD = default."
        ),
    )
    attempts_made: int = Field(
        ...,
        ge=0,
        description="Number of recovery interventions already attempted for this order.",
    )
    is_mandate: bool = Field(
        default=False,
        description="True if the payment is part of an auto-debit / e-NACH mandate.",
    )

    @field_validator("currency")
    @classmethod
    def currency_must_be_uppercase(cls, v: str) -> str:
        return v.upper()

    @field_validator("customer_phone")
    @classmethod
    def phone_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("customer_phone cannot be blank.")
        return v.strip()


# ---------------------------------------------------------------------------
# LLM output — structured schema returned by Gemini
# ---------------------------------------------------------------------------

class LLMRecoveryPlan(BaseModel):
    """
    The structured policy decision produced by the Gemini recovery agent.
    Gemini is constrained to return exactly this schema via response_schema.
    """

    root_cause_classification: Literal[
        "GATEWAY_TECHNICAL_FAILURE",
        "CUSTOMER_BALANCE_DEFICIT",
        "AUTHENTICATION_ABANDONMENT",
        "SUSPECTED_RISK",
    ] = Field(
        ...,
        description=(
            "The root cause bucket inferred from the error taxonomy and event context. "
            "GATEWAY_TECHNICAL_FAILURE = bank/network outage; "
            "CUSTOMER_BALANCE_DEFICIT = insufficient funds/credit; "
            "AUTHENTICATION_ABANDONMENT = OTP expired / customer dropped; "
            "SUSPECTED_RISK = velocity checks or fraud signals."
        ),
    )

    recommended_strategy: Literal[
        "SILENT_BACKGROUND_RETRY",
        "DISPATCH_DYNAMIC_PAYMENT_LINK",
        "HALT_AND_ABORT",
    ] = Field(
        ...,
        description=(
            "SILENT_BACKGROUND_RETRY = schedule an automated retry after cooldown. "
            "DISPATCH_DYNAMIC_PAYMENT_LINK = create a Razorpay payment link and notify the customer. "
            "HALT_AND_ABORT = do nothing; manual intervention required."
        ),
    )

    recommended_channel: Literal["NONE", "WHATSAPP", "SMS"] = Field(
        ...,
        description=(
            "Communication channel through which the recovery nudge should be dispatched. "
            "NONE when strategy is SILENT_BACKGROUND_RETRY or HALT_AND_ABORT."
        ),
    )

    cooldown_seconds: int = Field(
        ...,
        ge=0,
        description=(
            "Seconds to wait before executing the recovery action. "
            "0 for immediate action. Minimum 300 for technical failures."
        ),
    )

    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence in the recommended strategy (0.0 to 1.0).",
    )

    nudge_message: str = Field(
        ...,
        description=(
            "Culturally fluent, respectful Hinglish message to send to the customer. "
            "Must be empty string if recommended_channel is NONE."
        ),
    )

    technical_reasoning: str = Field(
        ...,
        description="Internal reasoning trace explaining the classification and strategy choice.",
    )

    @model_validator(mode="after")
    def validate_channel_message_consistency(self) -> "LLMRecoveryPlan":
        if self.recommended_channel == "NONE" and self.nudge_message.strip():
            self.nudge_message = ""
        if self.recommended_channel != "NONE" and not self.nudge_message.strip():
            self.nudge_message = (
                "Aapka payment process nahi ho saka. Kripya neeche diye gaye link se "
                "dobara try karein. Shukriya!"
            )
        return self


# ---------------------------------------------------------------------------
# Final execution result returned to the caller
# ---------------------------------------------------------------------------

class ExecutionResult(BaseModel):
    """The complete outcome of processing a single FailedPaymentEvent."""

    order_id: str
    original_amount: int = Field(description="Amount in paise.")
    ai_strategy: str = Field(description="Strategy recommended by the LLM before guardrails.")
    final_action_taken: str = Field(description="The action that was actually executed.")
    guardrail_overridden: bool = Field(
        description="True if a deterministic guardrail modified the LLM plan."
    )
    override_reason: str | None = Field(
        default=None,
        description="Human-readable explanation of which guardrail fired and why.",
    )
    payment_link_url: str | None = Field(
        default=None,
        description="Razorpay short URL if a payment link was generated.",
    )
    status: Literal[
        "RECOVERED_PENDING_PAYMENT",
        "SCHEDULED_RETRY",
        "ABORTED",
    ] = Field(description="The pipeline terminal state for this event.")
    audit_logged: bool = Field(description="True if the event was persisted to the audit ledger.")


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def paise_to_rupees(paise: int) -> float:
    """Convert integer paise to float rupees, rounded to 2 decimal places."""
    return round(paise / 100, 2)
