# Rate Limiter Demo - Backend Setup

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

### Backend Features

- Flask/FastAPI for REST API
- Redis for sliding window rate limiting
- Real-time request tracking and limiting

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