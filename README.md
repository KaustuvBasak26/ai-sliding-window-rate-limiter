# Rate Limiter Demo - Backend Setup

## Prerequisites

- Python 3.8+
- Docker (for Redis)

## Backend Implementation

// ...existing backend implementation details...

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