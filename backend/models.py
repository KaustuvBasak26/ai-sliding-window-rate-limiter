from pydantic import BaseModel
from typing import Optional, List


class RateLimitRequest(BaseModel):
    userId: str
    modelId: str
    tenantId: str | None = None
    apiKey: str | None = None
    modelTier: str | None = None  # e.g. "premium", "standard", "free"


# New: per-policy result returned when request is accepted
class PolicyResult(BaseModel):
    label: str
    key: str
    limit: int
    count: int
    windowSeconds: int


class RateLimitResponse(BaseModel):
    allowed: bool
    limit: int
    count: int
    windowSeconds: int
    cause: Optional[str] = None
    # If accepted, include all policies that were successfully fulfilled
    fulfilled: Optional[List[PolicyResult]] = None
