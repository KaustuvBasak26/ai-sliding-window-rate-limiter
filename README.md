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
- Docker (for Redis)

## Backend Implementation

### Step 1: Set up Redis

```bash
docker run -d --name redis -p 6379:6379 redis
```

### Step 2: Install dependencies

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
