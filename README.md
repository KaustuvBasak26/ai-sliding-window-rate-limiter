# AI Sliding Window Rate Limiter

A distributed **Sliding Window Log** rate limiter for AI model serving. It protects GPU capacity, enforces tenant and API-key quotas, and supports multi-scope policy precedence — backed by **FastAPI**, **Redis**, **PostgreSQL**, and a **React** demo UI.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Policy Model](#policy-model)
- [Testing the Demo UI](#testing-the-demo-ui)
- [Automated Tests](#automated-tests)
- [Production Security (Deploy)](#production-security-deploy)
- [Deploy to Render](#deploy-to-render)
- [Troubleshooting](#troubleshooting)
- [Design Documents](#design-documents)

---

## Overview

This project implements a production-style rate limiter for AI inference platforms:

- **Sliding window log** in Redis (sorted sets + `WATCH`/`MULTI`/`EXEC` for atomicity)
- **Policy resolver** that loads limits from PostgreSQL by scope (global, tenant, API key, model tier, user+model)
- **REST API** for checking and consuming quota
- **React UI** to interactively test allowed/blocked flows

Typical placement in an AI serving stack:

```
Client → API Gateway → Rate Limiter → Model Router → GPU Pool
```

<img width="468" height="205" alt="System context diagram" src="https://github.com/user-attachments/assets/c8342b02-4323-4b57-8ecb-62f4c38a3f5a" />

---

## Architecture

### Components

| Component | Role |
|-----------|------|
| **FastAPI backend** | Resolves policies, evaluates Redis limits, returns allow/block decisions |
| **PostgreSQL** | Stores tenants, users, API keys, models, tiers, and rate limit policies |
| **Redis** | Sliding window counters (one sorted set per policy key) |
| **React frontend** | Demo UI for submitting requests and viewing policy usage |

### Request flow

1. Client sends `userId`, `modelId`, and optional `tenantId`, `apiKey`, `modelTier`.
2. `PolicyResolver` maps request fields to DB IDs and fetches all applicable policies.
3. Each policy becomes a Redis key; `SlidingWindowRateLimiterTx` atomically checks and increments.
4. If **any** applicable policy is exceeded → request is **blocked** (most specific failure shown).
5. If all pass → request is **allowed** (primary policy = tightest remaining capacity).

<img width="468" height="403" alt="High-level design diagram" src="https://github.com/user-attachments/assets/d577ff94-43a5-4254-9927-e5eebea09d07" />

### Policy precedence

All applicable policies are enforced. On conflict, the **most specific** scope wins for the error message:

```
USER_MODEL > API_KEY > TENANT > MODEL > MODEL_TIER > GLOBAL
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Rate limiting | Redis 7 (sorted sets) |
| Policy store | PostgreSQL 16 |
| Frontend | React 19, Vite 7 |
| Tests | pytest, Vitest, React Testing Library |

---

## Project Structure

```
.
├── backend/
│   ├── main.py                 # FastAPI app, auth, static hosting, rate-limit API
│   ├── security.py             # Production hardening, sessions, login throttling
│   ├── rate_limiter.py         # SlidingWindowRateLimiterTx (Redis)
│   ├── policy_resolver.py      # Postgres-backed policy resolution
│   ├── models.py               # Pydantic request/response models
│   ├── config.py               # Environment variable helpers
│   ├── start.sh                # Render/production startup (validate + migrate + uvicorn)
│   ├── scripts/init_db.py      # Auto-applies SQL migrations on first boot
│   ├── migrations/
│   │   ├── 001_create_types_and_tables.sql
│   │   └── 002_seed_demo_data.sql
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/App.jsx             # Demo UI + access gate
│   ├── src/protectApp.js       # Production-only UI deterrents
│   ├── public/robots.txt       # Discourage indexing of deployed demo
│   └── vite.config.js
├── .env.example                # Local/production env template
├── render.yaml                 # Render Blueprint (one-click deploy)
└── README.md
```

<img width="468" height="149" alt="Low-level design diagram" src="https://github.com/user-attachments/assets/293ae4dc-d003-4cc8-b3f0-835c47ea8ceb" />

---

## Prerequisites

- **Python 3.12+**
- **Node.js 18+** and npm
- **Docker** (for local Redis and PostgreSQL)

---

## Local Development

### 1. Start Redis

```bash
docker run -d --name redis -p 6379:6379 redis
```

### 2. Start PostgreSQL and seed data

```bash
docker run -d \
  --name rl-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_DB=rate_limiter \
  -p 5432:5432 \
  postgres:16
```

Apply migrations:

```bash
psql -h localhost -U postgres -d rate_limiter -f backend/migrations/001_create_types_and_tables.sql
psql -h localhost -U postgres -d rate_limiter -f backend/migrations/002_seed_demo_data.sql
```

Verify seed data:

```sql
SELECT name FROM tenant;
SELECT scope, limit_value FROM rate_limit_policy;
```

Expected tenants: `enterprise_co`, `free_co`. See [Policy Model](#policy-model) for full seeded limits.

### 3. Run the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health

### 4. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (usually http://localhost:5173).

### 5. Optional — preview production locally

```bash
cd frontend && npm install && npm run build
cd ../backend
export APP_ACCESS_PASSWORD=local-demo-password
export SESSION_SECRET=local-demo-secret
export ENV=production
uvicorn main:app --port 8000
```

Open http://localhost:8000 (UI + API same origin, password gate enabled).

Copy `.env.example` to `.env` for local overrides if needed.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Render | local DSN below | PostgreSQL connection URL (`postgresql://...`) |
| `RL_PG_DSN` | No | see below | Alternative psycopg2-style DSN for local dev |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection URL |
| `CORS_ORIGINS` | No | `http://localhost:5173,...` | Comma-separated allowed frontend origins (local dev only) |
| `APP_ACCESS_PASSWORD` | Production deploy | unset | Gates the deployed app behind a password screen |
| `SESSION_SECRET` | Production deploy | auto on Render | Signs the httpOnly session cookie |
| `ENV` | No | unset locally | Set to `production` on Render to enable hardening |
| `VITE_API_URL` | Local frontend only | `http://localhost:8000` | Not needed in production (same-origin) |

Local defaults (no env vars needed):

```
RL_PG_DSN=dbname=rate_limiter user=postgres password=postgres host=localhost port=5432
REDIS_URL=redis://localhost:6379/0
```

---

## API Reference

### `GET /health`

Returns `{"status": "ok"}`. Public; used by Render health checks.

### `GET /auth/status`

Returns whether the deployment requires a password and whether the current browser session is authenticated.

### `POST /auth/login`

Body: `{"password":"..."}`. Sets an httpOnly session cookie on success. Rate-limited in production (10 attempts per 5 minutes per IP).

### `POST /auth/logout`

Clears the session cookie.

### `POST /rate-limit/check`

**Request body:**

```json
{
  "userId": "ent-user-1",
  "modelId": "gpt-4o",
  "tenantId": "enterprise_co",
  "modelTier": "premium",
  "apiKey": null
}
```

**Allowed response:**

```json
{
  "allowed": true,
  "limit": 500,
  "count": 1,
  "windowSeconds": 3600,
  "fulfilled": [
    {
      "label": "TENANT",
      "key": "rl:tenant:1",
      "limit": 500,
      "count": 1,
      "windowSeconds": 3600
    }
  ]
}
```

**Blocked response:**

```json
{
  "allowed": false,
  "limit": 10,
  "count": 11,
  "windowSeconds": 3600,
  "cause": "USER_MODEL exceeded: 11/10 in the last 3600 seconds (key=rl:user:...)"
}
```

**Example curl:**

```bash
curl -X POST http://localhost:8000/rate-limit/check \
  -H "Content-Type: application/json" \
  -d '{"userId":"ent-user-1","modelId":"gpt-4o","tenantId":"enterprise_co","modelTier":"premium"}'
```

---

## Policy Model

### Entities

| Entity | Description |
|--------|-------------|
| **Tenant** | Organization (e.g. `enterprise_co`) |
| **UserAccount** | User within a tenant (`external_id`) |
| **ApiKey** | Per-client key limits |
| **ModelTier** | `premium`, `standard`, `free` |
| **Model** | Inference model (e.g. `gpt-4o`) |
| **RateLimitPolicy** | Scoped limit rules |

<img width="468" height="657" alt="Entity relationship diagram" src="https://github.com/user-attachments/assets/cb5a856f-ae7f-42c8-ac32-a2e5d3a39356" />

### Seeded demo policies

| Scope | Example | Limit (per hour) |
|-------|---------|------------------|
| GLOBAL | fallback | 1,000,000 |
| TENANT | `enterprise_co` | 500 |
| TENANT | `free_co` | 50 |
| API_KEY | free tenant key | 20 |
| MODEL_TIER | premium / standard / free | 1000 / 100 / 10 |
| USER_MODEL | `ent-user-2` + `gpt-4o` | 10 |

---

## Testing the Demo UI

<img width="1512" height="910" alt="Demo UI screenshot" src="https://github.com/user-attachments/assets/70d6e972-5bb4-4f5f-909d-8bc2a9c74e40" />

### Scenario A — Allowed request

- Tenant: `enterprise_co`, User: `ent-user-1`, Model: `gpt-4o`, Tier: `premium`
- Click **Check Rate Limit** once
- Expect: ✅ Request Allowed, progress bar, satisfied policies list

### Scenario B — User+model limit

- User: `ent-user-2`, Model: `gpt-4o` (USER_MODEL limit = 10/hr)
- Click rapidly more than 10 times
- Expect: 🚫 Request Blocked with `USER_MODEL exceeded` cause

### Scenario C — Free tier limits

- Tenant: `free_co`, Model: `tiny-model`, Tier: `free`
- A few rapid clicks should trigger `MODEL_TIER` or `API_KEY` blocks

---

## Automated Tests

### Backend (pytest)

```bash
cd backend
pip install -r requirements.txt pytest
pytest
pytest --cov=. --cov-report=html
pytest tests/test_rate_limiter.py -v
```

Test files:

- `tests/test_rate_limiter.py` — sliding window logic
- `tests/test_policy_resolver.py` — scope precedence and Redis keys
- `tests/test_main_integration.py` — FastAPI endpoints (allowed/blocked responses, auth flow)
- `tests/test_security.py` — sessions, login throttling, static path safety, production config

### Frontend (Vitest / Jest)

```bash
cd frontend
npm install
npm test
npm run test:coverage
```

---

## Production Security (Deploy)

Deployed builds apply several layers of hardening. **Important:** any code that runs in the browser can still be inspected by a motivated user — DevTools and the Network tab cannot be fully blocked on the web. These measures raise the bar for casual access and hide internal implementation details.

| Protection | What it does |
|------------|----------------|
| **Startup validation** | Production refuses to boot without `APP_ACCESS_PASSWORD` and `SESSION_SECRET` |
| **Single-origin app** | Frontend is served by FastAPI (not a separate static URL), so there is no public repo-style source tree |
| **Access password** | `APP_ACCESS_PASSWORD` gates the UI; session stored in an **httpOnly** cookie with expiry (not in JS) |
| **Login throttling** | Failed login attempts rate-limited via Redis in production |
| **Timing-safe compare** | Password verification uses constant-time comparison |
| **Path traversal guard** | Static file handler rejects `../` escapes |
| **No source maps** | Production Vite build disables source maps |
| **Minified bundles** | Hashed filenames (`assets/[hash].js`) with no readable `.jsx` source |
| **Swagger disabled** | `/docs`, `/redoc`, and OpenAPI JSON are off in production |
| **Sanitized API responses** | Redis keys and stack traces are stripped from production responses |
| **Security headers** | CSP, `X-Frame-Options`, `X-Robots-Tag`, `no-store` caching, etc. |
| **robots.txt** | `Disallow: /` to discourage search engine indexing |
| **UI deterrents** | Right-click, view-source shortcut, and common DevTools shortcuts blocked in production builds |

### Known limits (honest)

| Claim | Reality |
|-------|---------|
| "Hide source code" | Minified JS is still downloadable; determined users can reverse it |
| "Block Network tab" | Impossible in browsers — API calls remain observable |
| "Block DevTools" | Client-side blocks are bypassed in seconds |
| Password gate | Stops casual visitors; not a substitute for enterprise IAM |

These controls are **defense in depth for a demo**, not DRM.

### After deploying on Render

1. Set **`APP_ACCESS_PASSWORD`** on the `rate-limiter` service (Render prompts for this during Blueprint sync).
2. Share that password only with people who should use the demo.
3. The app URL is a single service, e.g. `https://rate-limiter.onrender.com`.

Local development is unchanged — no password required unless you set `APP_ACCESS_PASSWORD` locally.

---

## Deploy to Render

This repo includes a [Render Blueprint](https://render.com/docs/blueprint-spec) (`render.yaml`) configured for the **free tier only**. All billable resources explicitly set `plan: free` — if you omit `plan`, Render defaults to paid instance types (`starter` for web/Key Value, `basic-256mb` for Postgres).

| Resource | Blueprint name | Instance type |
|----------|----------------|---------------|
| App + API (Python) | `rate-limiter` | **Free** |
| Key Value (Redis) | `rate-limiter-redis` | **Free** |
| PostgreSQL | `rate-limiter-db` | **Free** |

The Blueprint provisions:

1. **PostgreSQL** — policy database (auto-migrated on first boot)
2. **Redis** — sliding window counters
3. **Web service** — builds the React UI, serves it from FastAPI, and exposes the API on the same URL

### Option A — One-click Blueprint deploy

1. Push this repository to GitHub.
2. Open [Render Dashboard](https://dashboard.render.com/) → **New** → **Blueprint**.
3. Connect the repo; Render reads `render.yaml` and creates all services.
4. When prompted, set **`APP_ACCESS_PASSWORD`** to a strong password.
5. Wait for the first deploy to finish (migrations run automatically).
6. Open your service URL (e.g. `https://rate-limiter.onrender.com`) and enter the access password.

### Option B — Manual service setup

If you prefer creating services individually:

#### Web Service (API + frontend)

| Setting | Value |
|---------|-------|
| Runtime | Python 3 |
| Instance Type | **Free** |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt && cd ../frontend && npm install && npm run build` |
| Start Command | `bash start.sh` |
| Health Check Path | `/health` |

Environment variables:

- `ENV=production`
- `DATABASE_URL` — from Render Postgres (**Free** instance)
- `REDIS_URL` — from Render Key Value (**Free** instance)
- `APP_ACCESS_PASSWORD` — your chosen gate password
- `SESSION_SECRET` — random string (Render can generate this)

#### Render Key Value (Redis-compatible)

| Setting | Value |
|---------|-------|
| Instance Type | **Free** |
| Internal connections only | Yes (`ipAllowList: []` in blueprint) |

#### Render Postgres

| Setting | Value |
|---------|-------|
| Instance Type | **Free** |

### Post-deploy verification

```bash
curl https://YOUR-APP.onrender.com/health
```

Open the app URL, enter your `APP_ACCESS_PASSWORD`, then run the demo scenarios. Unauthenticated API calls return `401 Authentication required`.

### Render free tier notes

- All services in `render.yaml` use `plan: free` where applicable; do not change to `starter`, `standard`, or `basic-*` unless you intend to pay.
- Web services spin down after inactivity; the first request may take ~30s.
- Free PostgreSQL **expires after 30 days** and is permanently deleted — export data or upgrade for long-lived demos.
- Free Key Value has limited memory; suitable for this demo's sliding-window counters.
- Redis and Postgres must both be running before the API can serve traffic.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Redis connection error | Ensure Redis is running (`docker ps`) or `REDIS_URL` is set |
| Postgres connection error | Check `DATABASE_URL` / `RL_PG_DSN`; on Render, SSL is enabled automatically |
| `401 Authentication required` | Log in via the app UI, or set `APP_ACCESS_PASSWORD` only on production |
| Deploy fails immediately on boot | Set `APP_ACCESS_PASSWORD` and ensure `SESSION_SECRET` is present |
| `429 Too many login attempts` | Wait 5 minutes or retry from a different network |
| Port in use locally | `uvicorn main:app --port 8001` |
| Module not found | Activate venv and `pip install -r requirements.txt` |

---

## Design Documents

| Document | File |
|----------|------|
| System Requirements (SRD) | [SRD.pdf](SRD.pdf) |
| High-Level Design (HLD) | [HLD.pdf](HLD.pdf) |
| Low-Level Design (LLD) | [LLD.pdf](LLD.pdf) |
| Entity Relationship (ERD) | [ERD.pdf](ERD.pdf) |

<img width="419" height="304" alt="LLD detail" src="https://github.com/user-attachments/assets/9d0dd46e-e08e-40c0-97ea-99df8ed9a7f4" />

---

## License

Demo / educational project. See repository for usage terms.
