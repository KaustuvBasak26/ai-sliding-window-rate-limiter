from pydantic import BaseModel


class RateLimitRequest(BaseModel):
    userId: str
    modelId: str
    tenantId: str | None = None
    apiKey: str | None = None
    modelTier: str | None = None  # e.g. "premium", "standard", "free"


class RateLimitResponse(BaseModel):
    allowed: bool
    limit: int
    count: int
    windowSeconds: int
