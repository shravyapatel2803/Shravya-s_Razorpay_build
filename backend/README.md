# Autonomous Revenue Recovery & Smart Dunning Engine
### Track 03: AI Revenue Recovery — Razorpay AI Buildathon 2026

An autonomous, multi-tenant payment failure recovery and dunning orchestrator built with **FastAPI**, **Google Gemini AI (gemini-3.5-flash)**, **PostgreSQL (SQLAlchemy 2.0)**, and the official **Razorpay Python SDK**.

---

## The Problem
In online commerce, payment failures are common. Traditional retry mechanisms:
1. **Blindly retry** transactions regardless of root cause, causing merchant losses and bank penalty fees.
2. **Fatigue customers** with repetitive and inappropriate notifications.
3. **Trigger bank blocking** due to rate-limit or velocity violations.
4. Risk **double debits** during bank/gateway technical outages.

## The Solution
This engine acts as an autonomous revenue guardian for merchants:
1. **Ingests Webhook Failures** (`payment.failed`) with idempotency locks.
2. **AI Failure Classification**: Google Gemini evaluates failure taxonomy, customer tier, and history using strict Pydantic schemas.
3. **Deterministic Guardrails**: Python compliance engine enforces anti-fatigue ceilings, anti-double-charge safety buffers, and amount immutability.
4. **Autonomous Recovery**: Generates dynamic Razorpay Payment Links or schedules silent background cooldown retries.
5. **Auditing & Metrics**: PostgreSQL ledger records every decision and tracks GMV at risk vs. GMV recovered.

```
┌────────────────────────┐
│ Razorpay payment.failed│
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Multi-Tenant Webhook   │  (Idempotency Check)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Google Gemini AI Agent │  (Strict Pydantic JSON Schema)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Fintech Guardrails     │  (Anti-Fatigue, Cooldown, Limits)
└───────────┬────────────┘
            │
      ┌─────┴─────────────────────────┐
      ▼                               ▼
┌────────────────────────┐     ┌────────────────────────┐
│ Razorpay Payment Link  │     │ Silent Outage Cooldown │
│ (Pending Recovery)     │     │ (Scheduled Retry)      │
└───────────┬────────────┘     └───────────┬────────────┘
            │                             │
            └──────────────┬──────────────┘
                           ▼
            ┌─────────────────────────────┐
            │ PostgreSQL Audit Ledger &   │
            │ Real-Time Recovery Metrics  │
            └─────────────────────────────┘
```

---

## Features

- **Multi-Tenant SaaS Ready**: Supports multiple merchants with individual credentials and isolated recovery logs via `X-Merchant-Id`.
- **Google Gemini 3.5 Flash**: Zero-shot structured failure inference using official `google-genai` SDK.
- **Fail-Safe Fallbacks**: Works out of the box even without external API keys via deterministic rule-based evaluation and mock Razorpay links.
- **PostgreSQL & SQLite**: Built with SQLAlchemy 2.0 and `psycopg3`. Connects to PostgreSQL via `DATABASE_URL` or falls back to local SQLite with zero setup.
- **Deterministic Fintech Guardrails**:
  - **Rule 1 (Anti-Fatigue)**: Hard ceiling of maximum 3 retries (`attempts_made >= 3 -> HALT_AND_ABORT`).
  - **Rule 2 (Outage Protection)**: Bank/Gateway timeouts trigger silent cooldowns (no customer disruption).
  - **Rule 3 (High-Value Verification)**: Special validation for tickets exceeding ₹50,000.
  - **Rule 4 (Amount Immutability)**: Ensures payment amounts cannot be modified.

---

## Directory Structure

```
backend/
├── main.py              # FastAPI application, webhooks, and REST endpoints
├── agent.py             # Google Gemini AI policy reasoning & fallback logic
├── guardrails.py        # Authoritative fintech compliance rules
├── razorpay_service.py  # Razorpay SDK client & dynamic payment link creation
├── database.py          # PostgreSQL / SQLAlchemy schema and audit metrics
├── models.py            # Pydantic v2 schemas for events, plans, and results
├── simulate_batch.py    # 10-scenario end-to-end simulation test suite
├── requirements.txt     # Python dependencies
└── .env                 # Environment configuration (keys, database)
```

---

## Getting Started

### 1. Prerequisites
- Python 3.10+
- Virtual environment (`venv`)

### 2. Installation

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration (`.env`)

Create or update `.env` in the `backend/` directory:

```env
# Google Gemini API Key (Get from Google AI Studio)
GEMINI_API_KEY = "your_gemini_api_key"

# Razorpay API Credentials (Test or Live mode)
RAZORPAY_KEY_ID = "rzp_test_xxxxxx"
RAZORPAY_KEY_SECRET = "your_key_secret"

# PostgreSQL Database (Optional - defaults to local SQLite if omitted)
# DATABASE_URL = "postgresql://user:password@localhost:5432/razorpay_recovery"
```

*(Note: If API keys are omitted, the application runs in self-contained simulation mode using built-in deterministic fallbacks).*

### 4. Running the Server

```bash
uvicorn main:app --reload --port 8000
```

Interactive API documentation will be available at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## Running the 10-Scenario Test Suite

Open a separate terminal window and execute:

```bash
python simulate_batch.py
```

### Tested Scenarios
1. **FLIGHT001** (Gateway Timeout, ₹12,500) -> Silent Background Retry
2. **GROC002** (Insufficient Funds, ₹735) -> Dynamic Payment Link Generated
3. **FASH003** (OTP Expired, ₹3,499) -> Dynamic Payment Link Generated
4. **MAXR004** (3rd Failed Attempt, ₹899) -> Guardrail Override to `HALT_AND_ABORT`
5. **JEWL005** (High-Value VIP, ₹75,000) -> High-Ticket Payment Link
6. **RISK006** (Fraud Anomaly, ₹4,500) -> Halted for Merchant Review
7. **BANK007** (Issuer Bank 503, ₹9,999) -> Silent Background Cooldown
8. **NACH008** (e-NACH Mandate Bounce, ₹5,000) -> Alternate Payment Link
9. **EDTC009** (UPI Collect Timeout, ₹1,999) -> Silent Background Retry
10. **HOTL010** (Card Auth Failure, ₹22,000) -> Dynamic Payment Link Generated

### Expected Benchmark
- **Processed**: 10 Scenarios
- **Net GMV Recovery Rate**: **96.0%** of at-risk capital protected or active in recovery.

---

## API Reference

### `GET /health`
Returns service status, active database dialect, and live SDK status indicators.

### `POST /webhook/payment-failed`
Ingests a `FailedPaymentEvent`.
- **Headers**: `X-Merchant-Id: string` (optional, defaults to `default_merchant`)
- **Body**:
```json
{
  "order_id": "order_FLIGHT001",
  "payment_id": "pay_FLIGHT001a",
  "amount": 1250000,
  "currency": "INR",
  "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
  "error_description": "Payment gateway timed out.",
  "customer_name": "Arjun Mehra",
  "customer_phone": "+919876543210",
  "customer_tier": "VIP",
  "attempts_made": 0
}
```

### `GET /audit/metrics`
Returns aggregate GMV recovery performance:
- Total GMV At Risk
- Total GMV Under Active Recovery
- Total GMV Scheduled for Silent Retry
- Total GMV Aborted (Manual Review)
- Net Recovery Rate (%)

### `GET /audit/logs`
Returns the recent audit trail entries with timestamps and actions taken.

### `POST /audit/reset`
Clears the audit ledger for the specified merchant (useful for fresh simulation tests).

---

## License
MIT License. Built for the Razorpay AI Buildathon 2026.
