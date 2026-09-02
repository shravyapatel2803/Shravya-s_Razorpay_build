"""
scheduler.py -- Autonomous Background Retry Executor.

Runs as an asyncio background task inside the FastAPI lifespan.
Every POLL_INTERVAL_SECONDS it:
  1. Queries the DB for SCHEDULED_RETRY rows whose retry_at <= now
  2. Reconstructs a minimal FailedPaymentEvent and re-runs the full pipeline
  3. Updates the DB row to the new status (RECOVERED_PENDING_PAYMENT or ABORTED)

This closes the loop: a SCHEDULED_RETRY is no longer just a label -- it
actually retries.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import TYPE_CHECKING

import database

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 60   # check for due retries every minute
MAX_AUTO_RETRIES      = 2    # max scheduler-driven retries per order before aborting


# ---------------------------------------------------------------------------
# Public lifecycle helpers (called from main.py lifespan)
# ---------------------------------------------------------------------------

_scheduler_task: asyncio.Task | None = None


def start_scheduler() -> None:
    global _scheduler_task
    _scheduler_task = asyncio.create_task(_retry_loop(), name="retry-scheduler")
    logger.info("Scheduler started -- polling every %ds.", POLL_INTERVAL_SECONDS)


def stop_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        logger.info("Scheduler stopped.")


# ---------------------------------------------------------------------------
# Main poll loop
# ---------------------------------------------------------------------------

async def _retry_loop() -> None:
    """Infinite loop that wakes up every POLL_INTERVAL_SECONDS."""
    while True:
        try:
            await _process_due_retries()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Scheduler loop error (will retry next cycle): %s", exc)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _process_due_retries() -> None:
    now_iso = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    due = database.get_pending_retries(now_iso)

    if not due:
        logger.debug("Scheduler: no retries due at %s.", now_iso)
        return

    logger.info("Scheduler: %d retry(ies) due -- processing.", len(due))

    # Import here to avoid circular imports (main imports scheduler imports agent etc.)
    import agent
    import guardrails
    import razorpay_service
    import notifications
    from models import FailedPaymentEvent

    for row in due:
        order_id    = row["order_id"]
        retry_count = row["retry_count"]

        # Hard cap on scheduler-driven retries
        if retry_count >= MAX_AUTO_RETRIES:
            logger.warning(
                "Scheduler: order=%s exceeded MAX_AUTO_RETRIES (%d) -- aborting.",
                order_id, MAX_AUTO_RETRIES,
            )
            database.mark_retry_dispatched(order_id, "ABORTED")
            continue

        logger.info("Scheduler: retrying order=%s (attempt #%d)", order_id, retry_count + 1)

        # Reconstruct a FailedPaymentEvent from the stored row
        try:
            event = FailedPaymentEvent(
                order_id      = order_id,
                payment_id    = row.get("payment_id", "sched_retry"),
                amount        = row["amount_paise"],
                error_code    = row["error_code"],
                error_description = f"Scheduled retry #{retry_count + 1} for {row['error_code']}",
                customer_name  = row.get("customer_name", "Customer"),
                customer_phone = row.get("customer_phone", "+910000000000"),
                customer_email = row.get("customer_email", "unknown@recovery.engine"),
                customer_tier  = row.get("customer_tier", "STANDARD"),
                attempts_made  = row.get("attempts", 0) + retry_count,
            )
        except Exception as exc:
            logger.error("Scheduler: failed to reconstruct event for order=%s: %s", order_id, exc)
            continue

        # Run through agent + guardrails (run in executor to avoid blocking the event loop)
        try:
            loop = asyncio.get_running_loop()
            plan = await loop.run_in_executor(None, agent.evaluate_failure_policy, event)
            final_plan, guardrail_fired, override_reason = guardrails.enforce_guardrails(event, plan)
        except Exception as exc:
            logger.error("Scheduler: pipeline error for order=%s: %s", order_id, exc)
            database.mark_retry_dispatched(order_id, "ABORTED")
            continue

        # Execute action
        new_status    = "ABORTED"
        payment_link  = None

        if final_plan.recommended_strategy == "DISPATCH_DYNAMIC_PAYMENT_LINK":
            try:
                payment_link = await loop.run_in_executor(
                    None,
                    lambda: razorpay_service.create_recovery_payment_link(
                        order_id=event.order_id,
                        amount_paise=event.amount,
                        customer_name=event.customer_name,
                        phone=event.customer_phone,
                        email=event.customer_email,
                        notes={"scheduler_retry": str(retry_count + 1)},
                    )
                )
                new_status = "RECOVERED_PENDING_PAYMENT"

                # Dispatch notification if channel requested
                if final_plan.recommended_channel != "NONE" and final_plan.nudge_message:
                    await loop.run_in_executor(
                        None,
                        lambda: notifications.dispatch_nudge(
                            order_id=order_id,
                            channel=final_plan.recommended_channel,
                            phone=event.customer_phone,
                            message=final_plan.nudge_message,
                            payment_link_url=payment_link,
                        )
                    )
            except Exception as exc:
                logger.error("Scheduler: link creation failed for order=%s: %s", order_id, exc)
                new_status = "ABORTED"

        elif final_plan.recommended_strategy == "SILENT_BACKGROUND_RETRY":
            # Re-queue for another cooldown cycle
            new_status = "SCHEDULED_RETRY"

        database.mark_retry_dispatched(order_id, new_status)
        logger.info(
            "Scheduler: order=%s -> %s (guardrail=%s)", order_id, new_status, guardrail_fired
        )
