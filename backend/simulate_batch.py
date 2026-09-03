"""
simulate_batch.py -- 10-scenario end-to-end batch simulation.

v4: Includes full auth flow:
  1. Auto-registers (or skips if email exists) a test admin.
  2. Logs in and obtains JWT access token.
  3. Passes Bearer token in all webhook requests.
  4. Resets audit log before each run.
"""
from __future__ import annotations

import os
import sys
import time

import httpx

# ---------------------------------------------------------------------------
# Target server auto-discovery
# ---------------------------------------------------------------------------
PORTS = [8001, 8000]
BASE_URL: str | None = None

for _port in PORTS:
    try:
        r = httpx.get(f"http://127.0.0.1:{_port}/health", timeout=2)
        if r.status_code == 200:
            BASE_URL = f"http://127.0.0.1:{_port}"
            break
    except Exception:
        pass

if not BASE_URL:
    print("\n  ❌  No server found on ports 8000 or 8001. Start uvicorn first.\n")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Auth: register + login to get Bearer token
# ---------------------------------------------------------------------------
TEST_EMAIL = "simtest@razorpay-sim.dev"
TEST_PASSWORD = "SimTest@2026!"
TEST_BUSINESS = "Simulation Test Merchant"

def get_auth_token() -> str:
    """Register (ignore 409) then login and return Bearer token."""
    with httpx.Client(base_url=BASE_URL, timeout=15) as client:
        # Try to register
        client.post("/auth/register", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "business_name": TEST_BUSINESS,
        })
        # Login
        resp = client.post("/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        })
        if resp.status_code != 200:
            print(f"  [ERROR] Login failed ({resp.status_code}): {resp.text}")
            sys.exit(1)
        return resp.json()["access_token"]

# ---------------------------------------------------------------------------
# Test scenarios
# ---------------------------------------------------------------------------
SCENARIOS = [
    {
        "order_id": "order_FLIGHT001",
        "payment_id": "pay_FLIGHT001a",
        "amount": 1_250_000,
        "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
        "error_description": "Payment gateway timed out.",
        "customer_name": "Arjun Mehra",
        "customer_phone": "+919876543210",
        "customer_tier": "VIP",
        "attempts_made": 0,
    },
    {
        "order_id": "order_GROC002",
        "payment_id": "pay_GROC002a",
        "amount": 73_500,
        "error_code": "BAD_REQUEST_PAYMENT_CARD_INSUFFICIENT_FUNDS",
        "error_description": "Insufficient funds in account.",
        "customer_name": "Priya Sharma",
        "customer_phone": "+919876543211",
        "customer_tier": "STANDARD",
        "attempts_made": 0,
    },
    {
        "order_id": "order_FASH003",
        "payment_id": "pay_FASH003a",
        "amount": 349_900,
        "error_code": "BAD_REQUEST_PAYMENT_OTP_EXPIRED",
        "error_description": "OTP expired during 3DS authentication.",
        "customer_name": "Rahul Khanna",
        "customer_phone": "+919876543212",
        "customer_tier": "REPEAT_DROPOFF",
        "attempts_made": 0,
    },
    {
        "order_id": "order_MAXR004",
        "payment_id": "pay_MAXR004a",
        "amount": 89_900,
        "error_code": "BAD_REQUEST_PAYMENT_CARD_INSUFFICIENT_FUNDS",
        "error_description": "Insufficient funds — 3rd attempt.",
        "customer_name": "Sunita Patel",
        "customer_phone": "+919876543213",
        "customer_tier": "STANDARD",
        "attempts_made": 3,
    },
    {
        "order_id": "order_JEWL005",
        "payment_id": "pay_JEWL005a",
        "amount": 7_500_000,
        "error_code": "BAD_REQUEST_PAYMENT_OTP_EXPIRED",
        "error_description": "High-value jewellery purchase — OTP expired.",
        "customer_name": "Vikram Nair",
        "customer_phone": "+919876543214",
        "customer_tier": "VIP",
        "attempts_made": 0,
    },
    {
        "order_id": "order_RISK006",
        "payment_id": "pay_RISK006a",
        "amount": 539_900,
        "error_code": "BAD_REQUEST_PAYMENT_POSSIBLE_FRAUD",
        "error_description": "Fraud risk flag triggered.",
        "customer_name": "Unknown Customer",
        "customer_phone": "+919876543215",
        "customer_tier": "STANDARD",
        "attempts_made": 1,
    },
    {
        "order_id": "order_BANK007",
        "payment_id": "pay_BANK007a",
        "amount": 999_900,
        "error_code": "GATEWAY_ERROR_BANK_SYSTEM_ERROR",
        "error_description": "Issuer bank 503 outage.",
        "customer_name": "Amit Desai",
        "customer_phone": "+919876543216",
        "customer_tier": "STANDARD",
        "attempts_made": 0,
    },
    {
        "order_id": "order_NACH008",
        "payment_id": "pay_NACH008a",
        "amount": 500_000,
        "error_code": "BAD_REQUEST_PAYMENT_CARD_INSUFFICIENT_FUNDS",
        "error_description": "e-NACH debit mandate bounce.",
        "customer_name": "Deepa Reddy",
        "customer_phone": "+919876543217",
        "customer_tier": "STANDARD",
        "attempts_made": 0,
    },
    {
        "order_id": "order_EDTC009",
        "payment_id": "pay_EDTC009a",
        "amount": 199_900,
        "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
        "error_description": "UPI collect request timed out.",
        "customer_name": "Ravi Kumar",
        "customer_phone": "+919876543218",
        "customer_tier": "STANDARD",
        "attempts_made": 1,
    },
    {
        "order_id": "order_HOTL010",
        "payment_id": "pay_HOTL010a",
        "amount": 2_200_000,
        "error_code": "BAD_REQUEST_PAYMENT_CARD_HOLDER_AUTHENTICATION_FAILED",
        "error_description": "Card holder authentication failed.",
        "customer_name": "Sneha Iyer",
        "customer_phone": "+919876543219",
        "customer_tier": "VIP",
        "attempts_made": 0,
    },
]

# ---------------------------------------------------------------------------
# Run simulation
# ---------------------------------------------------------------------------
def main():
    print()
    print("=" * 80)
    print("  RAZORPAY AI REVENUE RECOVERY ENGINE -- BATCH SIMULATION (10 SCENARIOS)")
    print("=" * 80)
    print(f"\n  Target : {BASE_URL}")
    print(f"  Count  : {len(SCENARIOS)}\n")

    # Auth
    print("  Authenticating...", end=" ", flush=True)
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Token obtained.\n")

    # Reset audit log
    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=15) as client:
        client.post("/audit/reset")

    col_w = [15, 37, 30, 12, 16, 28]
    sep = "  " + "-" * col_w[0] + "+" + "-" * col_w[1] + "+" + "-" * col_w[2] + "+" + "-" * col_w[3] + "+" + "-" * col_w[4] + "+" + "-" * col_w[5]

    print(sep)
    print(
        f"  {'Order ID':<{col_w[0]}}| {'Error Code':<{col_w[1]}}| {'AI Decision':<{col_w[2]}}| {'Guardrail?':<{col_w[3]}}| {'Recovered':<{col_w[4]}}| {'Status':<{col_w[5]}}"
    )
    print(sep)

    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=60) as client:
        for scenario in SCENARIOS:
            resp = client.post("/webhook/payment-failed", json=scenario)
            short_order = scenario["order_id"].replace("order_", "")

            if resp.status_code == 409:
                print(f"  {short_order:<{col_w[0]}}| {scenario['error_code'][:col_w[1]-1]:<{col_w[1]}}| {'N/A(dup)':<{col_w[2]}}| {'no':<{col_w[3]}}| {'--':<{col_w[4]}}| DUPLICATE")
                continue

            if resp.status_code not in (200, 201):
                print(f"  {short_order:<{col_w[0]}}| {scenario['error_code'][:col_w[1]-1]:<{col_w[1]}}| {'ERROR':<{col_w[2]}}| {'--':<{col_w[3]}}| {'--':<{col_w[4]}}| HTTP {resp.status_code}")
                continue

            data = resp.json()
            strategy = data.get("ai_strategy", "?")[:col_w[2]-1]
            guardrail = "yes" if data.get("guardrail_overridden") else "no"
            recovered = f"Rs.{data['original_amount']//100:,}" if data.get("status") == "RECOVERED_PENDING_PAYMENT" else "--"
            status_val = data.get("status", "?")

            print(f"  {short_order:<{col_w[0]}}| {scenario['error_code'][:col_w[1]-1]:<{col_w[1]}}| {strategy:<{col_w[2]}}| {guardrail:<{col_w[3]}}| {recovered:<{col_w[4]}}| {status_val:<{col_w[5]}}")
            time.sleep(0.3)  # brief pause between requests

    print(sep)

    # Fetch final metrics
    print("\n  Fetching metrics...\n")
    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=15) as client:
        m_resp = client.get("/audit/metrics")

    if m_resp.status_code != 200:
        print(f"  ⚠  Could not fetch metrics: HTTP {m_resp.status_code}")
        return

    m = m_resp.json()
    total_at_risk = m.get("total_gmv_at_risk_inr", 0)
    recovered = m.get("total_gmv_recovered_inr", 0)
    scheduled = m.get("total_gmv_scheduled_inr", 0)
    aborted = m.get("total_gmv_aborted_inr", 0)
    overrides = m.get("guardrail_override_count", 0)
    rate = m.get("recovery_success_rate_pct", 0)

    net_recovery_pct = round(((recovered + scheduled) / total_at_risk * 100), 1) if total_at_risk else 0.0

    print("=" * 80)
    print("  FINAL METRICS SUMMARY")
    print("=" * 80)
    print(f"  Total Events Processed      : {m.get('total_events_processed', 0)}")
    print(f"  Total GMV At Risk           : Rs.{total_at_risk:,.2f}")
    print(f"  GMV Under Active Recovery   : Rs.{recovered:,.2f}  (payment links sent)")
    print(f"  GMV Queued for Silent Retry : Rs.{scheduled:,.2f}  (background retry)")
    print(f"  GMV Aborted (Manual Review) : Rs.{aborted:,.2f}")
    print(f"  Guardrail Overrides         : {overrides}")
    print(f"  Net Recovery Rate           : {rate}%")
    print()
    print(f"  *** NET GMV RECOVERY: {net_recovery_pct}% of Rs.{total_at_risk:,.2f} at risk ***")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
