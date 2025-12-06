# Rate Limiter

## Architecture
- SRD (System Requirements Document): [docs/SRD.md](docs/SRD.md)
- HLD (High-Level Design): [docs/HLD.md](docs/HLD.md)
- LLD (Low-Level Design): [docs/LLD.md](docs/LLD.md)
- ERD (Entity Relationship Diagram): [docs/ERD.png](docs/ERD.png)

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