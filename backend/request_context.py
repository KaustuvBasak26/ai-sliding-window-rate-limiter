"""Helpers for scoping demo counters and exposing match metadata."""

from __future__ import annotations

from models import RateLimitRequest, RequestContextMatch


def scope_limit_key(key: str, body: RateLimitRequest) -> str:
    """Isolate counters per request identity in session/demo mode."""
    tenant = (body.tenantId or "").strip()
    user = body.userId.strip()
    model = body.modelId.strip()
    tier = (body.modelTier or "").strip()
    api_key = (body.apiKey or "").strip()
    return f"{key}@{tenant}|{user}|{model}|{tier}|{api_key}"


def build_context_match(
    *,
    tenant_matched: bool,
    user_matched: bool,
    model_matched: bool,
    tier_matched: bool,
) -> RequestContextMatch:
    return RequestContextMatch(
        tenantMatched=tenant_matched,
        userMatched=user_matched,
        modelMatched=model_matched,
        tierMatched=tier_matched,
    )
