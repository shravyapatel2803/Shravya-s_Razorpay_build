"""
main.py — Razorpay AI Revenue Recovery Engine (v4.0 — Enterprise Edition)

Features:
  - JWT + API Key authentication (dual auth)
  - Role-Based Access Control (ADMIN / ANALYST / VIEWER)
  - Rate limiting via slowapi
  - Razorpay webhook HMAC-SHA256 signature verification
  - Request correlation ID middleware
  - Structured access logging
  - Multi-tenant merchant isolation
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

import agent
import database
import guardrails
import razorpay_service
from auth import router as auth_router
from api_keys import router as api_keys_router
from models import ExecutionResult, FailedPaymentEvent, paise_to_rupees
from rate_limiter import limiter
from security import get_current_merchant, require_role, enforce_webhook_signature

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initialising database schema and seeding default admin...")
    database.init_db()
    logger.info("Recovery Engine v4.0 (Enterprise) ready.")
    yield
    logger.info("Shutting down recovery engine.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Razorpay AI Revenue Recovery Engine",
    description=(
        "**Enterprise-grade** multi-tenant autonomous payment recovery orchestrator.\n\n"
        "## Authentication\n"
        "All protected endpoints require one of:\n"
        "- **Bearer JWT** — `Authorization: Bearer <access_token>` (obtain via `POST /auth/login`)\n"
        "- **API Key** — `X-API-Key: rzr_live_<key>` (manage via `POST /api-keys/`)\n\n"
        "## Roles\n"
        "- **ADMIN** — Full access including API key management, sub-user creation, audit reset\n"
        "- **ANALYST** — Can trigger recovery webhooks and view all audit data\n"
        "- **VIEWER** — Read-only access to metrics and logs\n"
    ),
    version="4.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Rate limiter state + middleware
# ---------------------------------------------------------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request correlation ID + access logging middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def request_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    start = time.perf_counter()

    response: Response = await call_next(request)

    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = str(elapsed_ms)

    logger.info(
        "%s %s → %d  [%sms] rid=%s",
        request.method, request.url.path,
        response.status_code, elapsed_ms, request_id,
    )
    return response


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------
@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    return JSONResponse(
        status_code=401,
        content={"error": "UNAUTHORIZED", "message": str(exc.detail) if hasattr(exc, "detail") else "Authentication required."},
    )


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    return JSONResponse(
        status_code=403,
        content={"error": "FORBIDDEN", "message": str(exc.detail) if hasattr(exc, "detail") else "Access denied."},
    )


# ---------------------------------------------------------------------------
# Mount routers
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(api_keys_router)


# ---------------------------------------------------------------------------
# System endpoints
# ---------------------------------------------------------------------------
@app.get("/", tags=["System"])
@app.get("/health", tags=["System"])
async def health_check() -> dict:
    return {
        "service": "Razorpay AI Revenue Recovery Engine",
        "version": "4.0.0",
        "edition": "Enterprise (Multi-Tenant SaaS)",
        "status": "healthy",
        "database_backend": database.engine.dialect.name,
        "gemini_model": "gemini-3.5-flash",
        "gemini_live": agent.is_live(),
        "razorpay_live": not razorpay_service.is_mock_mode(),
        "auth": "JWT + API Key (dual)",
        "rbac_roles": ["ADMIN", "ANALYST", "VIEWER"],
        "endpoints": {
            "register": "POST /auth/register",
            "login": "POST /auth/login",
            "refresh": "POST /auth/refresh",
            "me": "GET /auth/me",
            "api_keys": "POST|GET|DELETE /api-keys/",
            "webhook": "POST /webhook/payment-failed",
            "metrics": "GET /audit/metrics",
            "logs": "GET /audit/logs",
            "reset": "POST /audit/reset",
            "docs": "GET /docs",
        },
    }


# ---------------------------------------------------------------------------
# Webhook — Payment Failed
# ---------------------------------------------------------------------------
@app.post(
    "/webhook/payment-failed",
    response_model=ExecutionResult,
    tags=["Recovery Pipeline"],
    summary="Ingest a failed payment and execute autonomous recovery.",
)
@limiter.limit("100/minute")
async def handle_payment_failed(
    request: Request,
    event: FailedPaymentEvent,
    merchant: dict = Depends(require_role("ADMIN", "ANALYST")),
    x_razorpay_signature: str | None = Header(default=None),
) -> ExecutionResult:
    merchant_id = merchant["merchant_id"]

    # 0. Webhook Signature Verification (HMAC-SHA256)
    # Reads the raw body bytes for signature validation.
    # Verification is skipped unless VERIFY_WEBHOOK_SIGNATURE=true in .env
    raw_body = await request.body()
    enforce_webhook_signature(
        raw_body=raw_body,
        x_razorpay_signature=x_razorpay_signature,
        webhook_secret=os.getenv("RAZORPAY_WEBHOOK_SECRET", ""),
    )

    logger.info(
        "PIPELINE START | merchant=%s | order=%s | amount=Rs.%.2f | error=%s | role=%s",
        merchant_id, event.order_id, event.amount / 100, event.error_code, merchant["role"],
    )

    # 1. Idempotency Guard
    if database.is_order_active_or_resolved(event.order_id, merchant_id=merchant_id):
        logger.warning("DUPLICATE | order=%s for merchant=%s already handled.", event.order_id, merchant_id)
        raise HTTPException(
            status_code=409,
            detail={"error": "DUPLICATE_ORDER", "message": f"Order {event.order_id!r} already processed."},
        )

    # 2. AI Policy Evaluation
    llm_plan = agent.evaluate_failure_policy(event)
    ai_strategy = getattr(llm_plan, "strategy", None) or getattr(llm_plan, "recommended_strategy", "DISPATCH_DYNAMIC_PAYMENT_LINK")
    nudge_text = getattr(llm_plan, "nudge_message", "")

    # 3. Deterministic Guardrails (record issuer failure first for circuit breaker)
    guardrails.record_issuer_failure(event.error_code)
    final_plan, overridden, override_reason = guardrails.enforce_guardrails(event, llm_plan)
    final_strategy = getattr(final_plan, "strategy", None) or getattr(final_plan, "recommended_strategy", ai_strategy)
    final_cooldown = getattr(final_plan, "cooldown_seconds", 0)

    payment_link_url = None
    nudge_sent = None

    # 4. Strategy Execution
    if final_strategy == "HALT_AND_ABORT":
        final_action = "HALTED — no automated action; flagged for manual merchant review."
        status_val = "ABORTED"

    elif final_strategy == "SILENT_BACKGROUND_RETRY":
        final_action = f"Silent background retry queued with {final_cooldown}s cooldown."
        status_val = "SCHEDULED_RETRY"

    elif final_strategy == "DISPATCH_DYNAMIC_PAYMENT_LINK":
        payment_link_url = razorpay_service.create_payment_link(
            order_id=event.order_id,
            amount_paise=event.amount,
            name=event.customer_name,
            phone=event.customer_phone,
            description=f"Recovery checkout for Order #{event.order_id}",
        )
        nudge_sent = nudge_text
        final_action = f"Payment Link dispatched ({payment_link_url})"
        status_val = "RECOVERED_PENDING_PAYMENT"

    else:
        final_action = f"Unrecognised strategy: {final_strategy}"
        status_val = "ABORTED"

    # 5. Audit Ledger
    database.log_recovery(
        event=event,
        ai_strategy=ai_strategy,
        final_action=final_action,
        overridden=overridden,
        override_reason=override_reason,
        payment_link_url=payment_link_url,
        status=status_val,
        merchant_id=merchant_id,
        nudge_sent=nudge_sent,
    )

    return ExecutionResult(
        order_id=event.order_id,
        original_amount=event.amount,
        amount_paise=event.amount,
        ai_strategy=ai_strategy,
        final_action_taken=final_action,
        guardrail_overridden=overridden,
        override_reason=override_reason,
        payment_link_url=payment_link_url,
        nudge_message_sent=nudge_sent,
        status=status_val,
        audit_logged=True,
    )


# ---------------------------------------------------------------------------
# Audit Endpoints
# ---------------------------------------------------------------------------
@app.get("/audit/metrics", tags=["Audit"])
@limiter.limit("300/minute")
async def get_metrics(
    request: Request,
    merchant: dict = Depends(require_role("ADMIN", "ANALYST", "VIEWER")),
) -> dict:
    return database.get_metrics(merchant_id=merchant["merchant_id"])


@app.get("/audit/logs", tags=["Audit"])
@limiter.limit("300/minute")
async def get_logs(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    merchant: dict = Depends(require_role("ADMIN", "ANALYST", "VIEWER")),
) -> list[dict]:
    return database.get_recent_logs(limit=limit, merchant_id=merchant["merchant_id"])


@app.post("/audit/reset", tags=["Audit"])
async def reset_audit(
    merchant: dict = Depends(require_role("ADMIN")),
) -> dict:
    database.reset_db(merchant_id=merchant["merchant_id"])
    return {"status": "success", "message": f"Audit ledger reset for merchant {merchant['merchant_id']}."}


@app.get("/audit/circuit-breaker", tags=["Audit"])
async def get_circuit_breaker_status(
    merchant: dict = Depends(require_role("ADMIN", "ANALYST", "VIEWER")),
) -> dict:
    """Return the current state of the issuer outage circuit breaker."""
    return {
        "config": {
            "window_seconds": guardrails.CIRCUIT_BREAKER_WINDOW_S,
            "threshold": guardrails.CIRCUIT_BREAKER_THRESHOLD,
            "cooldown_seconds": guardrails.CIRCUIT_BREAKER_COOLDOWN_S,
        },
        "issuers": guardrails.get_circuit_breaker_status(),
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    is_dev = os.getenv("ENVIRONMENT", "development").lower() == "development"
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=is_dev)

