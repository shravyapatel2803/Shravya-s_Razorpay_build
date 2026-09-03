# Backend Architecture & Technical Reference
### Track 03: AI Revenue Recovery — Razorpay AI Buildathon 2026

Production-grade, modular FastAPI microservice powering autonomous payment failure recovery, deterministic guardrail enforcement, and cryptographic audit ledgers.

---

## 1. System Responsibilities & Boundaries

The backend implements a clear separation between **advisory AI reasoning** and **deterministic fintech authority**:

```
[Razorpay Webhook]
       │
       ▼
[Security & HMAC Auth] ──> Reject invalid signatures / unauthenticated requests
       │
       ▼
[Idempotency Check] ──────> Atomic DB lock prevents double-charging and race conditions
       │
       ▼
[Gemini Policy Engine] ───> Suggests root cause & drafts Hinglish nudge (typed JSON)
       │
       ▼
[Python Guardrails] ─────> AUTHORITATIVE: Overrides LLM on caps, outages, and amounts
       │
       ▼
[Razorpay API Client] ───> Issues dynamic 1-click UPI/card recovery link
       │
       ▼
[Audit Ledger] ──────────> Persists immutable transaction record for reconciliation
```

---

## 2. API Contract & Endpoint Specification

### Public / System Endpoints
- `GET /health` — Service readiness, active database dialect (`sqlite` or `postgresql`), Gemini model availability, and Razorpay SDK mode (`live` vs `mock`).

### Authentication Endpoints (`/auth`)
- `POST /auth/register` — Self-serve merchant registration (hashes passwords with Argon2).
- `POST /auth/login` — Issues short-lived access tokens (15m) and persistent refresh tokens (7d).
- `POST /auth/refresh` — Rotates and re-issues access tokens using valid refresh tokens.
- `POST /auth/logout` — Revokes refresh token in the database.
- `GET /auth/me` — Authenticated merchant profile details and credential configurations.
- `PUT /auth/me` — Updates merchant business name, Razorpay credentials, and Gemini API keys.
- `POST /auth/sub-users` — [ADMIN] Provision team member access (`ANALYST` or `VIEWER`).

### API Key Management (`/api-keys`)
- `POST /api-keys/` — [ADMIN] Generate a programmatic `rzr_live_*` key for server-to-server webhook ingestion.
- `GET /api-keys/` — List all issued keys with masked prefixes (`rzr_live_xxxx...`).
- `DELETE /api-keys/{id}` — Revoke programmatic access.

### Recovery Pipeline (`/webhook`)
- `POST /webhook/payment-failed` — Core ingestion endpoint for Razorpay `payment.failed` webhooks.
  - **Headers**: `Authorization: Bearer <token>` OR `X-API-Key: rzr_live_*`
  - **Rate Limit**: 100 requests / minute per merchant
  - **Payload**:
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

### Audit & Observability (`/audit`)
- `GET /audit/metrics` — Aggregate financial metrics (At-Risk GMV, Active Recovering GMV, Scheduled Retry GMV, Aborted GMV, Guardrail Override Count, Net Recovery %).
- `GET /audit/logs?limit=20` — Paginated real-time ledger entries.
- `POST /audit/reset` — [ADMIN] Flushes audit logs for the authenticated merchant (used during benchmarking).

---

## 3. Deterministic Guardrail Rules (`guardrails.py`)

No LLM decision ever executes unchecked. The guardrail engine enforces non-negotiable compliance rules:

1. **Rule 1: Anti-Fatigue Ceiling**: If `attempts_made >= 3`, the recovery strategy is unconditionally overridden to `HALT_AND_ABORT`, suppressing all customer contact.
2. **Rule 2: Outage Disturbance Suppression**: If root cause is `GATEWAY_TECHNICAL_FAILURE`, the strategy is forced to `SILENT_BACKGROUND_RETRY` with a minimum 300s cooldown. Customer channel is forced to `NONE` (preventing buyer panic during bank downtime).
3. **Rule 3: High-Value Verification Guard**: For transactions $> ₹50,000$, channel verification is strictly mandated to avoid spoofing vulnerabilities.
4. **Rule 4: Amount Immutability**: Payable amounts cannot be mutated by the LLM; amounts are strictly locked to the original webhook event.

---

## 4. Local Execution & Zero-Configuration Testing

```bash
# 1. Activate environment
cd backend
source venv/bin/activate  # Or venv\Scripts\activate on Windows

# 2. Start server
uvicorn main:app --host 127.0.0.1 --port 8001 --reload

# 3. In another terminal, run the 10-scenario benchmark suite
python simulate_batch.py
```
