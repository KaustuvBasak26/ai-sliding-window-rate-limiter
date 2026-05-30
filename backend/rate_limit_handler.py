from fastapi import HTTPException

from models import (
    RateLimitRequest,
    RateLimitResponse,
    RequestContextMatch,
    RequestSnapshot,
)
from policy_resolver import SCOPE_PRECEDENCE
from request_context import build_context_match, scope_limit_key
from security import is_production, sanitize_cause, sanitize_fulfilled


def _resolve_context_match(body: RateLimitRequest, resolver) -> RequestContextMatch | None:
    if not hasattr(resolver, "get_context_match"):
        return None
    match = resolver.get_context_match(body)
    return build_context_match(
        tenant_matched=match["tenant_matched"],
        user_matched=match["user_matched"],
        model_matched=match["model_matched"],
        tier_matched=match["tier_matched"],
    )


def _request_snapshot(body: RateLimitRequest) -> RequestSnapshot:
    return RequestSnapshot(
        tenantId=body.tenantId,
        userId=body.userId,
        modelId=body.modelId,
        modelTier=body.modelTier,
    )


def _limiter_key(
    policy_key: str,
    body: RateLimitRequest,
    scope_keys_by_request: bool,
) -> str:
    if scope_keys_by_request:
        return scope_limit_key(policy_key, body)
    return policy_key


def evaluate_rate_limit(
    body: RateLimitRequest,
    resolver,
    limiter,
    scope_keys_by_request: bool = False,
) -> RateLimitResponse:
    try:
        policies = resolver.resolve(body)
    except Exception as exc:
        detail = "Policy resolve error" if is_production() else f"Policy resolve error: {exc}"
        raise HTTPException(status_code=500, detail=detail) from exc

    context_match = _resolve_context_match(body, resolver)
    snapshot = _request_snapshot(body)

    evaluated = []
    for policy in policies:
        allowed, count = limiter.check_and_consume(
            key=_limiter_key(policy.key, body, scope_keys_by_request),
            window_seconds=policy.window_seconds,
            limit=policy.limit,
        )
        evaluated.append({"policy": policy, "allowed": allowed, "count": count})

    failures = [entry for entry in evaluated if not entry["allowed"]]
    if failures:
        failures_sorted = sorted(
            failures,
            key=lambda entry: SCOPE_PRECEDENCE.get(entry["policy"].scope, 0),
            reverse=True,
        )
        failure = failures_sorted[0]
        policy = failure["policy"]
        count = failure["count"]
        cause = (
            f"{policy.label} exceeded: {count}/{policy.limit} "
            f"in the last {policy.window_seconds} seconds"
        )
        if not is_production():
            cause += f" (key={policy.key})"

        if len(failures_sorted) > 1:
            other = [
                f"{entry['policy'].label} ({entry['count']}/{entry['policy'].limit})"
                for entry in failures_sorted[1:]
            ]
            cause += "; also violated: " + ", ".join(other)

        if is_production():
            cause = sanitize_cause(cause)

        return RateLimitResponse(
            allowed=False,
            limit=policy.limit,
            count=count,
            windowSeconds=policy.window_seconds,
            cause=cause,
            primaryPolicy=policy.label,
            contextMatch=context_match,
            requestSnapshot=snapshot,
        )

    if not evaluated:
        raise HTTPException(status_code=500, detail="No policy resolved")

    allowed_entries = [entry for entry in evaluated if entry["allowed"]]
    if not allowed_entries:
        raise HTTPException(status_code=500, detail="No allowed policies after evaluation")

    allowed_entries.sort(
        key=lambda entry: (
            entry["policy"].limit - entry["count"],
            -SCOPE_PRECEDENCE.get(entry["policy"].scope, 0),
        )
    )
    primary = allowed_entries[0]["policy"]
    primary_count = allowed_entries[0]["count"]

    fulfilled = [
        {
            "label": entry["policy"].label,
            "key": entry["policy"].key,
            "limit": entry["policy"].limit,
            "count": entry["count"],
            "windowSeconds": entry["policy"].window_seconds,
        }
        for entry in evaluated
        if entry["allowed"]
    ]
    if is_production():
        fulfilled = sanitize_fulfilled(fulfilled)

    return RateLimitResponse(
        allowed=True,
        limit=primary.limit,
        count=primary_count,
        windowSeconds=primary.window_seconds,
        primaryPolicy=primary.label,
        contextMatch=context_match,
        requestSnapshot=snapshot,
        fulfilled=fulfilled,
    )
