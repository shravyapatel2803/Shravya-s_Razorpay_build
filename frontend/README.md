# RecoveryAI — Frontend Dashboard
### AI Payment Failure Recovery & Smart Dunning Engine (Razorpay AI Buildathon 2026)

A dark-mode, enterprise SaaS merchant dashboard designed in the aesthetic of **Vercel × Stripe × Linear**. Built with **React 19**, **Vite**, **Tailwind CSS v4**, **GSAP**, **Recharts**, and **Zustand**.

---

## Key Highlights

- **Visuals**: Dark charcoal palette (`#08080f`), glowing accents, glassmorphic cards, and animated gradient borders.
- **GSAP Animations**:
  - Live animated particle background canvas.
  - Interactive entrance transitions and stagger animations.
  - Number ticker counters for KPI recovery metrics using `gsap.to()`.
  - Slide-in effects for real-time audit ledger feeds.
- **Interactive Webhook Tester**: Fire test `payment.failed` payloads directly from the dashboard and inspect Gemini's recovery reasoning in real-time with celebration micro-interactions (confetti).
- **Security & RBAC**:
  - JWT Bearer token authentication with automatic token attachment and 401 expiration handling.
  - Role-Based Access Control (`ADMIN`, `ANALYST`, `VIEWER`).
  - Programmatic API key generation with secure, one-time reveal modals.
- **1-Click Demo Login**: Instantly fills and authenticates using the pre-configured admin demo profile.

---

## Tech Stack

| Component | Technology | Description |
|---|---|---|
| **Framework** | [React 19](https://react.dev/) + [Vite](https://vitejs.dev/) | High-performance build toolchain & SPA engine |
| **Styling** | [Tailwind CSS v4](https://tailwindcss.com/) | Modern `@theme` CSS tokens & utility classes |
| **Animations** | [GSAP 3](https://greensock.com/gsap/) | Stagger reveals, particle canvas, smooth metric counters |
| **Charts** | [Recharts](https://recharts.org/) | GMV recovery funnel bar charts with dark tooltips |
| **State Management** | [Zustand](https://zustand-demo.pmnd.rs/) | Lightweight persisted client authentication store |
| **API Client** | [Axios](https://axios-http.com/) | Auto-attaches JWT Bearer tokens to `/api/*` requests |
| **Forms** | [React Hook Form](https://react-hook-form.com/) | High-performance input validation & form control |
| **Notifications** | [Sonner](https://sonner.emilkowal.ski/) | Floating toast notification engine |
| **Icons** | [Lucide React](https://lucide.dev/) | Clean, accessible vector icons |

---

## Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── client.js           # Axios instance, interceptors, and API methods
│   ├── components/
│   │   ├── Layout.jsx          # Collapsible sidebar navigation & session header
│   │   ├── KpiCard.jsx         # GSAP-animated financial counter card
│   │   ├── RecoveryFunnel.jsx  # Recharts funnel chart for at-risk vs recovered GMV
│   │   └── LiveFeed.jsx        # Real-time animated audit log stream
│   ├── pages/
│   │   ├── AuthPage.jsx        # Login, registration & 1-Click Demo access
│   │   ├── DashboardPage.jsx   # Metrics, funnel analysis, and audit feed
│   │   ├── WebhookPage.jsx     # Live webhook simulator with scenario presets
│   │   ├── ApiKeysPage.jsx     # Programmatic API key creation & revocation
│   │   └── SettingsPage.jsx    # Profile, credentials, and team member management
│   ├── store/
│   │   └── authStore.js        # Persisted Zustand store for tokens & profile
│   ├── App.jsx                 # Route protection & nested page layout
│   ├── main.jsx                # DOM root, BrowserRouter & Sonner toast container
│   └── index.css               # Tailwind v4 theme definitions & design utilities
├── index.html                  # HTML5 shell with Google Font optimization
├── vite.config.js              # Vite server configuration & backend proxy
└── package.json                # Dependencies and build scripts
```

---

## Dashboard Views

### 1. Authentication (`/`)
- Canvas particle animation with fluid floating points.
- Smooth form toggling between Sign In and Account Creation.
- **Quick Demo Access**: Click `1-Click Demo Login` to authenticate as `demo@razorpay-recovery.dev`.

### 2. Main Dashboard (`/dashboard`)
- **4 Key Performance Indicators**:
  - *Total GMV At Risk* (Sum of all incoming failed orders).
  - *GMV Under Recovery* (Payment links dispatched).
  - *Queued for Retry* (Bank outage cooldowns).
  - *Net Recovery Rate %* (Overall capital saved).
- **GMV Recovery Funnel**: Visualizes transaction volume across all recovery stages.
- **Live Decision Feed**: Displays real-time recovery strategies, status badges, and direct links to active payment checkouts.

### 3. Webhook Tester (`/webhook`)
- Pre-built scenario presets:
  - *OTP Timeout (VIP customer)*
  - *Card Insufficient Funds*
  - *Bank 503 Outage*
  - *Fraud Anomaly Alert (Halt)*
- Real-time response cards displaying AI root-cause analysis, guardrail compliance audits, and generated Razorpay payment URLs.

### 4. API Key Management (`/api-keys`)
- Generate `rzr_live_*` API keys for server-to-server webhook ingestion.
- One-time secure copy dialog.
- Revocation controls for compromised or expired credentials.

### 5. Settings & Team Management (`/settings`)
- Update merchant brand name, Razorpay Key ID/Secret, and Gemini API keys.
- Admin controls: Invite and manage sub-users (`ANALYST` or `VIEWER` roles).

---

## Getting Started

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Start Development Server
```bash
npm run dev
```

The app will launch at **`http://localhost:5174`** (or `http://localhost:5173`).

### 3. Backend Connection
The frontend uses Vite's proxy configured in `vite.config.js`:
```javascript
server: {
  port: 5174,
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8001',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
  },
}
```
Ensure your FastAPI backend is running on `http://127.0.0.1:8001`.

---

## Production Build

```bash
# Build optimized production bundle
npm run build

# Preview production build locally
npm run preview
```
