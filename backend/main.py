# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import redis
import os

from models import RateLimitRequest, RateLimitResponse
from rate_limiter import SlidingWindowRateLimiterTx
from policy_resolver import PolicyResolver, SCOPE_PRECEDENCE

app = FastAPI(title="AI Rate Limiter Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = redis.Redis(host="localhost", port=6379, db=0)
rate_limiter = SlidingWindowRateLimiterTx(redis_client)

# Postgres DSN – adjust as needed
DB_DSN = os.getenv(
    "RL_PG_DSN",
    "dbname=rate_limiter user=postgres password=postgres host=localhost port=5432",
)

policy_resolver = PolicyResolver(DB_DSN)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/rate-limit/check", response_model=RateLimitResponse)
def check_rate_limit(body: RateLimitRequest):
    if not body.userId or not body.modelId:
        raise HTTPException(status_code=400, detail="userId and modelId are required")

    try:
        policies = policy_resolver.resolve(body)
    except Exception as e:
        # In a real system you'd log this; for now, surface it
        raise HTTPException(status_code=500, detail=f"Policy resolve error: {e}")

    # We'll evaluate all policies and collect results so we can return a clear cause
    evaluated = []  # list of dicts: {policy, allowed, count}
    for p in policies:
        allowed, count = rate_limiter.check_and_consume(
            key=p.key,
            window_seconds=p.window_seconds,
            limit=p.limit,
        )
        evaluated.append(
            {
                "policy": p,
                "allowed": allowed,
                "count": count,
            }
        )

    # Find any failing policies
    failures = [e for e in evaluated if not e["allowed"]]

    if failures:
        # Pick the most specific failure using precedence map
        failures_sorted = sorted(
            failures,
            key=lambda x: SCOPE_PRECEDENCE.get(x["policy"].scope, 0),
            reverse=True,
        )
        f = failures_sorted[0]
        p = f["policy"]
        count = f["count"]
        # build a human readable cause
        cause = (
            f"{p.label} exceeded: {count}/{p.limit} in the last {p.window_seconds} seconds "
            f"(key={p.key})"
        )

        if len(failures_sorted) > 1:
            other = []
            for o in failures_sorted[1:]:
                op = o["policy"]
                other.append(f"{op.label} ({o['count']}/{op.limit})")
            cause += "; also violated: " + ", ".join(other)

        return RateLimitResponse(
            allowed=False,
            limit=p.limit,
            count=count,
            windowSeconds=p.window_seconds,
            cause=cause,
        )

    # All policies passed; determine primary policy by smallest remaining capacity (limit - count)
    if not evaluated:
        raise HTTPException(status_code=500, detail="No policy resolved")

    # consider only allowed entries (should be all here); compute left capacity and tie-break by scope precedence
    allowed_entries = [e for e in evaluated if e["allowed"]]
    if not allowed_entries:
        raise HTTPException(status_code=500, detail="No allowed policies after evaluation")

    def _sort_key(entry):
        # left = remaining capacity
        left = entry["policy"].limit - entry["count"]
        # tie-break: higher precedence (more specific) wins -> use negative so higher precedence sorts earlier
        prec = SCOPE_PRECEDENCE.get(entry["policy"].scope, 0)
        return (left, -prec)

    allowed_entries.sort(key=_sort_key)
    primary_entry = allowed_entries[0]
    primary = primary_entry["policy"]
    primary_count = primary_entry["count"]

    # return fulfilled policy details as well
    fulfilled = [
        {
            "label": e["policy"].label,
            "key": e["policy"].key,
            "limit": e["policy"].limit,
            "count": e["count"],
            "windowSeconds": e["policy"].window_seconds,
        }
        for e in evaluated
        if e["allowed"]
    ]

    return RateLimitResponse(
        allowed=True,
        limit=primary.limit,
        count=primary_count,
        windowSeconds=primary.window_seconds,
        fulfilled=fulfilled,
    )
