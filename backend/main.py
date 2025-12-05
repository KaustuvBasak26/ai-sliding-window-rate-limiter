from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import redis

from models import RateLimitRequest, RateLimitResponse
from rate_limiter import SlidingWindowRateLimiterTx
from policy_resolver import PolicyResolver

app = FastAPI(title="AI Rate Limiter Demo")

# CORS so React can call it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis client (adjust host/port if Docker is different)
redis_client = redis.Redis(host="localhost", port=6379, db=0)
rate_limiter = SlidingWindowRateLimiterTx(redis_client)
policy_resolver = PolicyResolver()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/rate-limit/check", response_model=RateLimitResponse)
def check_rate_limit(body: RateLimitRequest):
    # Very basic validation
    if not body.userId or not body.modelId:
        raise HTTPException(status_code=400, detail="userId and modelId are required")

    # Resolve all effective limits (user, model-global, tier, tenant, etc.)
    policies = policy_resolver.resolve(body)

    # We'll enforce *all* policies; if any fails, request is blocked
    last_detail = None
    for p in policies:
        allowed, count = rate_limiter.check_and_consume(
            key=p.key,
            window_seconds=p.window_seconds,
            limit=p.limit,
        )

        last_detail = (p, count)

        # fail-fast: if any limit hit, block
        if not allowed:
            if count == -1:
                raise HTTPException(
                    status_code=503, detail="rate limiter contention"
                )
            return RateLimitResponse(
                allowed=False,
                limit=p.limit,
                count=count,
                windowSeconds=p.window_seconds,
            )

    # If we reach here everything passed; respond with the "primary" user limit
    if last_detail is None:
        raise HTTPException(status_code=500, detail="No policy resolved")

    p, count = last_detail
    return RateLimitResponse(
        allowed=True,
        limit=p.limit,
        count=count,
        windowSeconds=p.window_seconds,
    )
