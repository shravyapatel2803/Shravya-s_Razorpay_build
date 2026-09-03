# Razorpay AI Revenue Recovery & Smart Dunning Engine
### Track 03: AI Revenue Recovery — Razorpay AI Buildathon 2026

An autonomous, enterprise-grade revenue recovery engine that prevents naive payment retries, protects merchant capital, and boosts payment success rates using **Google Gemini AI**, **Deterministic Fintech Guardrails**, **PostgreSQL**, and the **Razorpay SDK**.

---

## Architecture Overview

```
                          ┌────────────────────────┐
                          │   Razorpay Webhook     │
                          │   (payment.failed)     │
                          └───────────┬────────────┘
                                      │
                                      ▼
                        ┌────────────────────────────┐
                        │   FastAPI Enterprise API   │
                        │  (Dual Auth: JWT / API-Key)│
                        └─────────────┬──────────────┘
                                      │
                                      ▼
                        ┌────────────────────────────┐
                        │  Google Gemini 3.5 Flash   │
                        │  Policy Reasoning Engine   │
                        └─────────────┬──────────────┘
                                      │
                                      ▼
                        ┌────────────────────────────┐
                        │    Fintech Guardrails      │
                        │ (Anti-Fatigue / Cooldown)  │
                        └─────────────┬──────────────┘
                                      │
                ┌─────────────────────┴─────────────────────┐
                ▼                                           ▼
  ┌───────────────────────────┐               ┌───────────────────────────┐
  │  Razorpay Payment Link    │               │  Silent Outage Cooldown   │
  │  (Pending Recovery)       │               │  (Scheduled Retry)        │
  └─────────────┬─────────────┘               └─────────────┬─────────────┘
                │                                           │
                └─────────────────────┬─────────────────────┘
                                      ▼
                        ┌────────────────────────────┐
                        │ PostgreSQL / SQLite Ledger │
                        │  (Audit Trails & Metrics)  │
                        └─────────────┬──────────────┘
                                      │
                                      ▼
                        ┌────────────────────────────┐
                        │  React 19 + Tailwind + GSAP│
                        │    Executive Dashboard     │
                        └────────────────────────────┘
```

---

## Key Features

### 1. AI Decisioning (Gemini 3.5 Flash)
- Zero-shot classification of failure codes into root causes:
  - `GATEWAY_TECHNICAL_FAILURE` (timeouts, bank 503 errors).
  - `CUSTOMER_BALANCE_DEFICIT` (insufficient funds, limit breaches).
  - `AUTHENTICATION_ABANDONMENT` (expired OTPs, 3DS drops).
  - `SUSPECTED_RISK` (fraud anomalies, velocity flags).
- Enforces strict Pydantic JSON schemas with deterministic fallbacks if quota is exhausted.

### 2. Authoritative Fintech Guardrails
- **Rule 1 (Anti-Fatigue Ceiling)**: Orders with $\ge 3$ failed attempts are automatically aborted (`HALT_AND_ABORT`) to prevent customer spam and card blocks.
- **Rule 2 (Outage Isolation)**: Issuer bank or gateway failures force silent background retries with a minimum 300s cooldown without disturbing the customer.
- **Rule 3 (High-Value Verification)**: Special protection policies applied to transactions exceeding ₹50,000.
- **Rule 4 (Amount Immutability)**: Hard constraint preventing alteration of order amounts.

### 3. Enterprise Backend
- **Dual Authentication**: Accepts JWT Bearer tokens or programmatic `rzr_live_*` API keys.
- **Multi-Tenant SaaS Architecture**: Merchants operate with isolated credentials and audit logs.
- **Role-Based Access Control (RBAC)**: Supports `ADMIN`, `ANALYST`, and `VIEWER` roles.
- **Rate Limiting**: Sliding-window protection via `slowapi` (100 req/min for webhooks, 10 req/min for auth).
- **PostgreSQL & SQLite**: Native support for PostgreSQL via SQLAlchemy 2.0 and `psycopg3`, with seamless zero-configuration fallback to local SQLite.

### 4. Merchant Dashboard
- **React 19 + Tailwind CSS v4 + GSAP**: Dark-mode interface designed with the aesthetic of Stripe and Linear.
- **Real-Time Data**: Animated KPI counters, recovery funnel charts (Recharts), and a live audit feed.
- **Interactive Webhook Tester**: Fire simulated failure payloads with preset scenarios and observe recovery decisions in real time.
- **API Key & Team Management**: Provision and revoke API keys and invite sub-users.
- **1-Click Demo Login**: Pre-configured admin demo profile (`demo@razorpay-recovery.dev` / `DemoPass@2026!`).

---

## Directory Structure

```
Razorpay_build/
├── backend/                  # FastAPI Python backend
│   ├── main.py               # REST API, webhook routes & middleware
│   ├── agent.py              # Gemini 3.5 Flash policy reasoning engine
│   ├── guardrails.py         # Deterministic fintech compliance rules
│   ├── database.py           # PostgreSQL/SQLite schema (SQLAlchemy 2.0)
│   ├── security.py           # Argon2 hashing, JWT & HMAC verification
│   ├── auth.py               # Authentication endpoints (login, register, refresh)
│   ├── api_keys.py           # Programmatic API key management
│   ├── rate_limiter.py       # Sliding-window rate limiter
│   ├── razorpay_service.py   # Razorpay SDK payment link generation
│   ├── models.py             # Pydantic v2 data models
│   ├── simulate_batch.py     # 10-scenario end-to-end benchmark test
│   └── README.md             # Detailed backend documentation
│
├── frontend/                 # React 19 + Vite + Tailwind CSS v4
│   ├── src/
│   │   ├── pages/            # Auth, Dashboard, Webhook Tester, API Keys, Settings
│   │   ├── components/       # Layout, KPI Cards, Funnel Chart, Live Feed
│   │   ├── api/client.js     # Axios client with JWT auto-attachment
│   │   ├── store/            # Zustand auth state store
│   │   └── index.css         # Tailwind v4 theme & custom utilities
│   ├── vite.config.js        # Vite config & API reverse proxy
│   └── README.md             # Detailed frontend documentation
│
└── README.md                 # Project root documentation (this file)
```

---

## Quick Start Guide

### Prerequisites
- **Python**: 3.10+
- **Node.js**: 18+ & `npm`

---

### Step 1: Start the Backend

```bash
# Navigate to backend directory
cd backend

# Create & activate virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server on port 8001
python -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

*API Documentation (Swagger UI) is available at: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)*

---

### Step 2: Start the Frontend

```bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install packages
npm install

# Start Vite dev server
npm run dev
```

*Dashboard interface will be live at: [http://localhost:5174](http://localhost:5174)*

---

### Step 3: Run the 10-Scenario Test Suite

```bash
# In the backend terminal (with venv activated):
python simulate_batch.py
```

#### Benchmark Results (10 Complex Real-World Scenarios)
- **Scenarios Evaluated**: 10
- **Total GMV At Risk**: ₹1,37,030.00
- **GMV Under Active Recovery**: ₹1,06,234.00 (Payment Links generated)
- **GMV Queued for Silent Retry**: ₹24,498.00 (Gateway cooldowns)
- **GMV Aborted (Manual Review)**: ₹6,298.00 (Fraud flags / anti-fatigue limits)
- **Net Recovery Rate**: **95.4% of at-risk capital protected or active in recovery**

---

## Default Demo Credentials

The platform is pre-seeded with an active demo admin account:

| Field | Value |
|---|---|
| **Email** | `demo@razorpay-recovery.dev` |
| **Password** | `DemoPass@2026!` |
| **Role** | `ADMIN` |
| **1-Click Login** | Available directly on the sign-in page |

---

## Environment Configuration

Backend configuration (`backend/.env`):

```env
# Google Gemini API Key
GEMINI_API_KEY = "your_gemini_api_key"

# Razorpay API Credentials (Test or Live)
RAZORPAY_KEY_ID = "rzp_test_xxxxxx"
RAZORPAY_KEY_SECRET = "your_key_secret"

# JWT Secret Key for token signing
SECRET_KEY = "your_32_byte_secure_hex_key"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Environment (development | production)
ENVIRONMENT = development

# Optional: PostgreSQL Connection URI (defaults to SQLite if commented)
# DATABASE_URL = postgresql://user:password@localhost:5432/razorpay_recovery
```

---

## Track 03 Alignment: Razorpay AI Buildathon 2026

1. **Autonomous Action**: Goes beyond standard dashboards by actively evaluating webhooks, selecting strategies, and triggering payment link generation without human intervention.
2. **Fintech Compliance**: Integrates non-negotiable compliance rules (anti-fatigue, anti-double-charge safety, amount immutability).
3. **Multi-Tenant SaaS**: Ready for multi-merchant onboarding with isolated audit trails and API key management.
4. **Developer Experience**: Complete REST APIs with Swagger documentation, test scripts, and an interactive webhook sandbox.

---

## License

MIT License. Developed for the Razorpay AI Buildathon 2026.
