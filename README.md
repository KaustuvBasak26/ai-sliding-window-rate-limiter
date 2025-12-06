# Rate Limiter

## Architecture
### 1.1 Purpose
Design and implement a distributed, Sliding Window Log based rate limiter for AI model serving.
This system prevents GPU overload, enforces fair usage, and supports tenant-based, API key-based, model-tier-based rate decisions.
The solution includes:
•	A standalone backend rate limiter in Python (FastAPI)
•	A Redis-based distributed Sliding Window Log
•	A simple React UI to demonstrate its behavior

<img width="468" height="205" alt="image" src="https://github.com/user-attachments/assets/c8342b02-4323-4b57-8ecb-62f4c38a3f5a" />

- SRD (System Requirements Document): [SRD.pdf](SRD.pdf)

### 2.1 Architecture Overview
Client → API Gateway → Rate Limiter → Model Router → GPU Pool
 
Purpose of rate limiter in AI serving
•	Stops abusive clients from overloading GPUs.
•	Enforces tenant-level SLAs.
•	Prioritizes internal / premium traffic (QoS tiers).

<img width="468" height="403" alt="image" src="https://github.com/user-attachments/assets/d577ff94-43a5-4254-9927-e5eebea09d07" />

- HLD (High-Level Design): [HLD.pdf](HLD.pdf)

### 3.1 Python Directory Structure
backend/
  main.py
  rate_limiter.py
  models.py
  policy_resolver.py (optional)
frontend/
  src/App.jsx

<img width="468" height="149" alt="image" src="https://github.com/user-attachments/assets/293ae4dc-d003-4cc8-b3f0-835c47ea8ceb" />

- LLD (Low-Level Design): [LLD.pdf](LLD.pdf)

<img width="419" height="304" alt="image" src="https://github.com/user-attachments/assets/9d0dd46e-e08e-40c0-97ea-99df8ed9a7f4" />

### 4.1 Entities
#### Tenant
Represents an organization using your API.

#### UserAccount
Represents individual users within a tenant.

#### ApiKey
Represents API keys used by external clients or services.
Required for per API key limits.

#### ModelTier
Represents model performance/price class (e.g., GPT-4, GPT-4-mini).
Required for per model tier limits.

#### Model
Represents actual base model used in inference (e.g., gpt-4, gpt-3.5).
RateLimitPolicy

#### Flexible policy table supporting:

•	GLOBAL rules

•	TENANT-level rules

•	API_KEY-level rules

•	MODEL-level rules

•	MODEL_TIER-level rules

•	USER_MODEL rules

<img width="468" height="657" alt="image" src="https://github.com/user-attachments/assets/cb5a856f-ae7f-42c8-ac32-a2e5d3a39356" />

- ERD (Entity Relationship Diagram): [ERD.pdf](ERD.pdf)

# Rate Limiter Setup

## 1. Backend (FastAPI + Redis)
## Prerequisites

- Python 3.8+
- Docker (for Redis and Postgres)

## Backend Implementation

### Step 1: Set up Redis

```bash
docker run -d --name redis -p 6379:6379 redis
```

### Step 2: Postgres Setup & Database Seeding

The rate limiter uses a Postgres database to store policies, tenants, users, API keys, models, and tiers.

#### 2.1 Start Postgres in Docker

```bash
docker run -d \
  --name rl-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_DB=rate_limiter \
  -p 5432:5432 \
  postgres:16
```

#### 2.2 Test connection

```bash
psql -h localhost -U postgres -d rate_limiter
# Enter password: postgres
```

Once connected, type `\q` to exit.

#### 2.3 Seed the database

Create two migration files in a `migrations/` folder at the backend root:

**migrations/001_create_types_and_tables.sql**

**migrations/002_seed_demo_data.sql**

Run both migrations:

```bash
psql -h localhost -U postgres -d rate_limiter -f migrations/001_create_types_and_tables.sql
psql -h localhost -U postgres -d rate_limiter -f migrations/002_seed_demo_data.sql
```

#### 1.4 Verify seed data

Connect to psql and run these queries:

```bash
psql -h localhost -U postgres -d rate_limiter
```

```sql
SELECT name FROM tenant;
SELECT external_id, tenant_id FROM user_account;
SELECT name FROM model_tier;
SELECT name, tier_id FROM model;
SELECT scope, limit_value FROM rate_limit_policy;
```

You should see:
- **Tenants**: `enterprise_co`, `free_co`
- **Users**: `ent-user-1`, `ent-user-2`, `free-user-1`
- **Tiers**: `premium`, `standard`, `free`
- **Models**: `gpt-4o` (premium), `gpt-4o-mini` (standard), `tiny-model` (free)
- **Policies**: GLOBAL=100, TENANT=500/50, API_KEY=20, MODEL_TIER=60/30/10, USER_MODEL=10

## Viewing seeded data (quick psql checks)

After running the migrations, connect to Postgres and run these short queries to inspect the seeded rows:

```bash
psql -h localhost -U postgres -d rate_limiter
# then in psql:
SELECT * FROM tenant;
SELECT * FROM model_tier;
SELECT * FROM model;
SELECT external_id, tenant_id FROM user_account;
SELECT scope, window_seconds, limit_value FROM rate_limit_policy;
```

Example of expected output (trimmed) — this matches the demo seed used above:

```
 rate_limiter=# SELECT * FROM tenant;
  id |    name     |         created_at
 ----+-------------+----------------------------
   1 | enterprise_co | 2025-12-06 09:15:22.981628
   2 | free_co       | 2025-12-06 09:15:22.981628

 rate_limiter=# SELECT * FROM model_tier;
  id |  name   |               description
 ----+---------+------------------------------------
   1 | premium | Expensive, high-capacity models like GPT-4
   2 | standard| Mid-tier models
   3 | free   | Cheaper/smaller models

 rate_limiter=# SELECT * FROM model;
 id |    name     | tier_id
 ----+-------------+---------
  1 | gpt-4o      |       1
  2 | gpt-4o-mini |       2
  3 | tiny-model  |       3

 rate_limiter=# SELECT scope, window_seconds, limit_value FROM rate_limit_policy;
   scope    | window_seconds | limit_value
------------+----------------+-------------
 GLOBAL     |           3600 |       1000000
 TENANT     |           3600 |         500
 API_KEY    |           3600 |          20
 MODEL_TIER |           3600 |        1000
 MODEL_TIER |           3600 |         100
 MODEL_TIER |           3600 |          10
 USER_MODEL |           3600 |          10
```

### Step 2: Install backend dependencies

```bash
cd backend
python -m venv venv
source .venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Run the backend server

```bash
uvicorn main:app --reload --port 8000
```

The backend API will be available at **http://localhost:8000**.

### API Documentation (Swagger)

Once the backend is running, access the interactive API documentation at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Backend Features

- Flask/FastAPI for REST API
- Redis for sliding window rate limiting
- Real-time request tracking and limiting
- Swagger/OpenAPI documentation

## Troubleshooting

- **Redis connection error**: Ensure Redis container is running with `docker ps`
- **Port already in use**: Change port with `--port 8001` flag
- **Module not found**: Verify virtual environment is activated and packages are installed

## 3. Frontend (React + Vite)

### Step 1: Install dependencies

```bash
cd frontend
npm install
```

### Step 2: Run the frontend development server

```bash
npm run dev
```

The frontend will be available at the URL printed by Vite (usually **http://localhost:5173**).

### Frontend Features

- Vite for fast development and build
- React for UI components
- Hot module replacement for instant updates

<img width="1512" height="910" alt="Screenshot 2025-12-06 at 7 47 14 PM" src="https://github.com/user-attachments/assets/70d6e972-5bb4-4f5f-909d-8bc2a9c74e40" />

## Policies included (seeded)

The example migration seeds a set of policies to demonstrate precedence and collisions. These are present in `migrations/002_seed_demo_data.sql` and in the DB after seeding.

- GLOBAL
  - scope: GLOBAL
  - window: 3600s
  - limit_value: 1_000_000 (demo-high default)
  - Purpose: fallback global cap (effectively not restrictive in demo)

- TENANT
  - scope: TENANT
  - example: enterprise_co → 500 / hour
  - example: free_co → 50 / hour
  - Purpose: tenant-wide quota; overrides generic global behavior for tenants.

- API_KEY
  - scope: API_KEY
  - example: api key assigned to free_co → 20 / hour
  - Purpose: per-client key limits (useful for throttling single API consumers).

- MODEL_TIER
  - scope: MODEL_TIER
  - premium → 1000 / hour
  - standard → 100 / hour
  - free → 10 / hour
  - Purpose: tier-based protection (e.g., premium models may be throttled to protect capacity).

- USER_MODEL
  - scope: USER_MODEL
  - example: ent-user-2 + gpt-4o → 10 / hour (very strict for testing)
  - Purpose: specific user+model overrides (most specific — highest precedence).

Notes on precedence
- The resolver orders policies by specificity (USER_MODEL > API_KEY > TENANT > MODEL > MODEL_TIER > GLOBAL).
- All applicable policies are enforced: a request must satisfy every applicable policy key. If any applicable policy is violated the request is blocked and the most specific failing policy is shown as the primary cause.

## How to test from the frontend (step-by-step)
1. Start services (Redis + Postgres), seed the DB, and run backend & frontend as described above.

2. Open the frontend (default: http://localhost:5173). Example default form values in the demo UI:
   - Tenant ID: enterprise_co
   - User ID: ent-user-1
   - Model ID: gpt-4o
   - Model Tier: Premium
   
<img width="382" height="861" alt="Screenshot 2025-12-06 at 8 12 23 PM" src="https://github.com/user-attachments/assets/a7c5c206-5695-4b36-8fcb-545fb051d469" />

<img width="381" height="849" alt="Screenshot 2025-12-06 at 8 13 10 PM" src="https://github.com/user-attachments/assets/75bf60bf-34f8-48f6-a4db-f24258958e50" />

<img width="382" height="859" alt="Screenshot 2025-12-06 at 8 13 34 PM" src="https://github.com/user-attachments/assets/15af74a5-134a-4a5c-8cf7-a2cb1384fe2b" />

<img width="385" height="715" alt="Screenshot 2025-12-06 at 8 13 52 PM" src="https://github.com/user-attachments/assets/d176d975-8964-48ea-bfbd-75cfd2880d4a" />

<img width="380" height="849" alt="Screenshot 2025-12-06 at 8 14 16 PM" src="https://github.com/user-attachments/assets/29461e11-ecb8-4dad-ab33-1591d880bc36" />

<img width="381" height="856" alt="Screenshot 2025-12-06 at 8 14 48 PM" src="https://github.com/user-attachments/assets/9ce6179d-6163-45e1-8b04-a85dd9fde0b7" />

<img width="380" height="856" alt="Screenshot 2025-12-06 at 8 15 12 PM" src="https://github.com/user-attachments/assets/b67db562-619f-445e-b313-370c473debfc" />

<img width="388" height="725" alt="Screenshot 2025-12-06 at 8 15 44 PM" src="https://github.com/user-attachments/assets/0aa8fc00-f4bc-4ad7-afec-73ff807ee340" />

<img width="393" height="860" alt="Screenshot 2025-12-06 at 8 16 05 PM" src="https://github.com/user-attachments/assets/40fb4418-c876-4d50-9dbb-82833a3b6565" />

3. Test scenarios and expected UI:

- Scenario A — Typical allowed request (enterprise_co, ent-user-1, gpt-4o, premium)
  - Why: tenant (500/hr) and tier (1000/hr) and user default all permit this single request.
  - Action: Click "Check Rate Limit" once.
  - Expected frontend:
    - Status: "✅ Request Allowed"
    - Primary Limit Usage: shows count/limit (e.g., 1 / 500 if the tenant policy is primary) and a colored progress bar.
    - Fulfilled policies list: shows entries for the matched policies (labels, counts, windows). Each entry lists label, count/limit and window minutes.

- Scenario B — Hitting a stricter tier/user limit (ent-user-2 on gpt-4o)
  - Why: ent-user-2 has a USER_MODEL policy set to 10/hr (very strict). If you send >10 requests within the hour you will hit that policy.
  - Action: Rapidly click the "Check Rate Limit" button > 10 times (or send 11 quick requests).
  - Expected frontend once exceeded:
    - Status: "🚫 Request Blocked"
    - Reason: e.g. "USER_MODEL exceeded: 11/10 in the last 3600 seconds (key=rl:user:...)" (or similar human label from resolver)
    - The fulfilled list will not appear when blocked; instead the cause is shown in the reason box.

- Scenario C — API key / free tenant limits (simulate free_co / free model)
  - Set Tenant ID to `free_co`, choose a free model (tiny-model) or use the API key from the seed.
  - Because free tier limits are low (10/hr or API_KEY 20/hr), a few rapid clicks will show the "Blocked" state.
  - Expected frontend:
    - Blocked message with cause referencing `MODEL_TIER` or `API_KEY` (whichever policy was first to fail).
    - Fulfilled list absent.

4. Inspect policy precedence and multiple failures
  - If multiple policies are violated simultaneously, the UI will show the primary cause (most specific) and the backend cause string will append "also violated: ..." with the other violations summarized.
  - Example UI cause: "USER_MODEL exceeded: 11/10 ...; also violated: MODEL_TIER (11/100)"

5. API testing via curl (optional)
  - Allowed example:
    curl -X POST http://localhost:8000/rate-limit/check -H "Content-Type: application/json" \
      -d '{"userId":"ent-user-1","modelId":"gpt-4o","tenantId":"enterprise_co","modelTier":"premium"}'
  - Blocked example (after exceeding): same curl after you have sent enough requests to violate a policy; response JSON will contain allowed=false and a human-readable cause.

6. What to inspect in logs / debugs
  - Backend logs print policy evaluations (key, label, limit, count) — use them to confirm which Redis key hit the limit.
  - Use psql queries (see verification section) to check the exact policy rows and values if behavior appears inconsistent.
