"""
main.py — FastAPI application: Autonomous Payment Recovery & Dunning Orchestrator.

Endpoints
---------
GET  /                          Health check & system metadata
POST /webhook/payment-failed    Ingests a FailedPaymentEvent and runs the full pipeline
GET  /audit/metrics             Aggregated GMV metrics
GET  /audit/logs                Recent audit log entries
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
load_dotenv()  # load .env before any module reads env vars
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import agent
import database
import guardrails
import razorpay_service
from models import ExecutionResult, FailedPaymentEvent

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan — database initialisation
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initialising SQLite audit ledger…")
    database.init_db()
    logger.info("Recovery engine ready.")
    yield
    logger.info("Recovery engine shutting down.")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Razorpay AI Revenue Recovery Engine",
    description=(
        "Autonomous Payment Recovery & Dunning Orchestrator — Track 03 of the "
        "Razorpay AI Buildathon 2026. Uses Google Gemini (gemini-2.5-flash) with "
        "Pydantic v2 schema enforcement, deterministic guardrails, and the Razorpay "
        "Python SDK to recover failed payments and minimise GMV loss."
    ),
    version="1.0.0",
    contact={
        "name": "Razorpay Buildathon Team",
        "url": "https://razorpay.com",
    },
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Health / metadata
# ---------------------------------------------------------------------------

@app.get("/", tags=["System"])
async def health_check() -> dict:
    """Return system health and configuration metadata."""
    return {
        "service": "Razorpay AI Revenue Recovery Engine",
        "version": "1.0.0",
        "status": "healthy",
        "gemini_model": "gemini-3.8-flash",
        "gemini_live": bool(agent._GEMINI_API_KEY),
        "razorpay_live": not razorpay_service.is_mock_mode(),
        "description": (
            "Autonomous Payment Recovery & Dunning Orchestrator. "
            "POST /webhook/payment-failed to trigger recovery."
        ),
        "endpoints": {
            "webhook": "POST /webhook/payment-failed",
            "metrics": "GET /audit/metrics",
            "logs": "GET /audit/logs",
            "docs": "GET /docs",
        },
    }


# ---------------------------------------------------------------------------
# Core recovery webhook
# ---------------------------------------------------------------------------

@app.post(
    "/webhook/payment-failed",
    response_model=ExecutionResult,
    tags=["Recovery Pipeline"],
    summary="Ingest a failed payment event and run the full recovery pipeline.",
)
async def handle_payment_failed(event: FailedPaymentEvent) -> ExecutionResult:
    """
    Full pipeline:
    1. Idempotency check — reject duplicate order_ids that are already active/resolved.
    2. Gemini policy inference — structured LLMRecoveryPlan.
    3. Guardrail enforcement — deterministic compliance rules applied in priority order.
    4. Action execution — create Razorpay payment link or schedule silent retry.
    5. Audit logging — persist outcome to SQLite.
    6. Return ExecutionResult to caller.
    """

    logger.info(
        "PIPELINE START | order=%s | amount=Rs.%.2f | error=%s | attempts=%d",
        event.order_id,
        event.amount / 100,
        event.error_code,
        event.attempts_made,
    )

    # ------------------------------------------------------------------
    # Step 1 — Idempotency guard
    # ------------------------------------------------------------------
    if database.is_order_active_or_resolved(event.order_id):
        logger.warning(
            "DUPLICATE | order=%s already processed — rejecting.",
            event.order_id,
        )
        raise HTTPException(
            status_code=409,
            detail={
                "error": "DUPLICATE_ORDER",
                "message": (
                    f"Order {event.order_id!r} has already been processed by the recovery "
                    "engine. Each order is processed exactly once (idempotency guarantee)."
                ),
            },
        )

    # ------------------------------------------------------------------
    # Step 2 — Gemini policy inference
    # ------------------------------------------------------------------
    logger.info("AGENT | Evaluating failure policy via Gemini…")
    llm_plan = agent.evaluate_failure_policy(event)
    logger.info(
        "AGENT | Result: strategy=%s, cause=%s, confidence=%.2f, channel=%s",
        llm_plan.recommended_strategy,
        llm_plan.root_cause_classification,
        llm_plan.confidence_score,
        llm_plan.recommended_channel,
    )

    original_ai_strategy = llm_plan.recommended_strategy

    # ------------------------------------------------------------------
    # Step 3 — Guardrail enforcement
    # ------------------------------------------------------------------
    final_plan, guardrail_fired, override_reason = guardrails.enforce_guardrails(
        event, llm_plan
    )
    if guardrail_fired:
        logger.warning("GUARDRAIL | Override applied: %s", override_reason)

    # ------------------------------------------------------------------
    # Step 4 — Execute approved action
    # ------------------------------------------------------------------
    payment_link_url: str | None = None
    final_action: str
    status: str

    if final_plan.recommended_strategy == "HALT_AND_ABORT":
        final_action = "HALTED — no automated recovery; manual review required."
        status = "ABORTED"
        logger.info("ACTION | ABORTED for order %s", event.order_id)

    elif final_plan.recommended_strategy == "SILENT_BACKGROUND_RETRY":
        final_action = (
            f"Queued silent background retry with {final_plan.cooldown_seconds}s cooldown."
        )
        status = "SCHEDULED_RETRY"
        logger.info(
            "ACTION | SCHEDULED_RETRY for order %s | cooldown=%ds",
            event.order_id,
            final_plan.cooldown_seconds,
        )

    elif final_plan.recommended_strategy == "DISPATCH_DYNAMIC_PAYMENT_LINK":
        notes = {
            "root_cause": final_plan.root_cause_classification,
            "channel": final_plan.recommended_channel,
            "confidence": str(round(final_plan.confidence_score, 3)),
        }
        payment_link_url = razorpay_service.create_recovery_payment_link(
            order_id=event.order_id,
            amount_paise=event.amount,
            customer_name=event.customer_name,
            phone=event.customer_phone,
            email=event.customer_email,
            notes=notes,
        )
        channel_label = final_plan.recommended_channel
        final_action = (
            f"Payment link dispatched via {channel_label}: {payment_link_url}"
        )
        status = "RECOVERED_PENDING_PAYMENT"
        logger.info(
            "ACTION | RECOVERED_PENDING_PAYMENT | order=%s | url=%s | channel=%s",
            event.order_id,
            payment_link_url,
            channel_label,
        )

    else:
        # Should be unreachable given the Literal type, but guard defensively
        final_action = f"Unknown strategy: {final_plan.recommended_strategy}"
        status = "ABORTED"

    # ------------------------------------------------------------------
    # Step 5 — Audit logging
    # ------------------------------------------------------------------
    try:
        database.log_recovery(
            event=event,
            ai_strategy=original_ai_strategy,
            final_action=final_action,
            overridden=guardrail_fired,
            override_reason=override_reason,
            payment_link_url=payment_link_url,
            status=status,
        )
        audit_logged = True
        logger.info("AUDIT | Logged recovery for order %s", event.order_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("AUDIT | Failed to log recovery for order %s: %s", event.order_id, exc)
        audit_logged = False

    # ------------------------------------------------------------------
    # Step 6 — Return result
    # ------------------------------------------------------------------
    result = ExecutionResult(
        order_id=event.order_id,
        original_amount=event.amount,
        ai_strategy=original_ai_strategy,
        final_action_taken=final_action,
        guardrail_overridden=guardrail_fired,
        override_reason=override_reason,
        payment_link_url=payment_link_url,
        status=status,
        audit_logged=audit_logged,
    )

    logger.info(
        "PIPELINE END | order=%s | status=%s | guardrail=%s",
        event.order_id,
        status,
        guardrail_fired,
    )
    return result


# ---------------------------------------------------------------------------
# Audit endpoints
# ---------------------------------------------------------------------------

@app.get("/audit/metrics", tags=["Audit"], summary="Aggregated GMV and recovery metrics.")
async def get_audit_metrics() -> dict:
    """
    Return aggregated business metrics across all processed events.

    Fields
    ------
    total_events_processed     : Number of unique payment failure events ingested.
    total_gmv_at_risk_inr      : Total transaction value at risk (Rs.).
    total_gmv_recovered_inr    : GMV under active recovery (payment links dispatched).
    total_gmv_scheduled_inr    : GMV queued for silent retry.
    total_gmv_aborted_inr      : GMV halted (no automated recovery attempted).
    guardrail_override_count   : Number of events where guardrails modified the LLM plan.
    recovery_success_rate_pct  : % of events resolved via recovery or scheduled retry.
    """
    return database.get_metrics()


@app.get("/audit/logs", tags=["Audit"], summary="Recent audit log entries.")
async def get_audit_logs(
    limit: int = Query(default=20, ge=1, le=100, description="Max entries to return."),
) -> list[dict]:
    """Return the most recent recovery audit log entries (newest first)."""
    return database.get_recent_logs(limit=limit)


# ---------------------------------------------------------------------------
# Dev-mode entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
