from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class FailedPaymentEvent(BaseModel):
    order_id: str
    payment_id: str
    amount: int = Field(gt=0)
    currency: str = "INR"
    error_code: str
    error_description: str
    customer_name: str
    customer_phone: str
    customer_tier: Literal["STANDARD", "VIP", "REPEAT_DROPOFF"] = "STANDARD"
    customer_email: Optional[str] = "customer@example.com"
    attempts_made: int = Field(default=0, ge=0)
    is_mandate: bool = False

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, v: str) -> str:
        return v.upper()


class LLMRecoveryPlan(BaseModel):
    # Support both schema styles seamlessly
    root_cause_classification: Optional[
        Literal[
            "GATEWAY_TECHNICAL_FAILURE",
            "CUSTOMER_BALANCE_DEFICIT",
            "AUTHENTICATION_ABANDONMENT",
            "SUSPECTED_RISK",
        ]
    ] = None
    root_cause: Optional[
        Literal[
            "GATEWAY_TECHNICAL_FAILURE",
            "CUSTOMER_BALANCE_DEFICIT",
            "AUTHENTICATION_ABANDONMENT",
            "SUSPECTED_RISK",
        ]
    ] = None

    recommended_strategy: Optional[
        Literal[
            "SILENT_BACKGROUND_RETRY",
            "DISPATCH_DYNAMIC_PAYMENT_LINK",
            "HALT_AND_ABORT",
        ]
    ] = None
    strategy: Optional[
        Literal[
            "SILENT_BACKGROUND_RETRY",
            "DISPATCH_DYNAMIC_PAYMENT_LINK",
            "HALT_AND_ABORT",
        ]
    ] = None

    recommended_channel: Optional[Literal["NONE", "WHATSAPP", "SMS"]] = None
    channel: Optional[Literal["NONE", "WHATSAPP", "SMS"]] = None

    cooldown_seconds: int = Field(default=0, ge=0)
    confidence_score: float = Field(default=0.9, ge=0.0, le=1.0)
    nudge_message: str = ""
    technical_reasoning: str = ""

    @model_validator(mode="after")
    def sync_aliases(self) -> "LLMRecoveryPlan":
        # Synchronize root cause
        if not self.root_cause and self.root_cause_classification:
            self.root_cause = self.root_cause_classification
        elif not self.root_cause_classification and self.root_cause:
            self.root_cause_classification = self.root_cause
        
        # Synchronize strategy
        if not self.strategy and self.recommended_strategy:
            self.strategy = self.recommended_strategy
        elif not self.recommended_strategy and self.strategy:
            self.recommended_strategy = self.strategy

        # Synchronize channel
        if not self.channel and self.recommended_channel:
            self.channel = self.recommended_channel
        elif not self.recommended_channel and self.channel:
            self.recommended_channel = self.channel

        # Handle channel & message alignment
        effective_channel = self.channel or self.recommended_channel or "NONE"
        if effective_channel == "NONE":
            self.nudge_message = ""
        elif not self.nudge_message.strip():
            self.nudge_message = (
                "Aapka payment complete nahi ho saka. "
                "Kripya is link se retry karein. Dhanyavaad!"
            )
        return self


class ExecutionResult(BaseModel):
    order_id: str
    original_amount: Optional[int] = None
    amount_paise: Optional[int] = None
    ai_strategy: str
    final_action_taken: str
    guardrail_overridden: bool
    override_reason: Optional[str] = None
    payment_link_url: Optional[str] = None
    nudge_message_sent: Optional[str] = None
    status: Literal["RECOVERED_PENDING_PAYMENT", "SCHEDULED_RETRY", "ABORTED"]
    audit_logged: Optional[bool] = True


def paise_to_rupees(paise: int) -> float:
    return round(paise / 100, 2)

def paise_to_inr(paise: int) -> float:
    return round(paise / 100, 2)
