from dataclasses import dataclass
from typing import List, Optional

from models import RateLimitRequest


@dataclass
class EffectiveLimit:
    key: str
    window_seconds: int
    limit: int
    label: str


class PolicyResolver:
    """
    Very simple policy resolver:
    - Default user+model limit: 100 req/hour
    - Global per-model limit: 1000 req/hour
    - You can extend this to read from DB based on tenantId, apiKey, modelTier, etc.
    """

    DEFAULT_USER_LIMIT = 100
    DEFAULT_MODEL_GLOBAL_LIMIT = 1000
    WINDOW_SECONDS = 3600

    def resolve(self, body: RateLimitRequest) -> List[EffectiveLimit]:
        limits: List[EffectiveLimit] = []

        # User+model key
        user_key = f"rl:user:{body.userId}:model:{body.modelId}"
        limits.append(
            EffectiveLimit(
                key=user_key,
                window_seconds=self.WINDOW_SECONDS,
                limit=self.DEFAULT_USER_LIMIT,
                label="user_model",
            )
        )

        # Global per-model key (protect GPU pool)
        model_key = f"rl:model:{body.modelId}:global"
        limits.append(
            EffectiveLimit(
                key=model_key,
                window_seconds=self.WINDOW_SECONDS,
                limit=self.DEFAULT_MODEL_GLOBAL_LIMIT,
                label="model_global",
            )
        )

        # Example: stricter limit for "premium" (pretend it's expensive like GPT-4)
        if body.modelTier == "premium":
            tier_key = f"rl:tier:premium:model:{body.modelId}"
            limits.append(
                EffectiveLimit(
                    key=tier_key,
                    window_seconds=self.WINDOW_SECONDS,
                    limit=60,   # 60/hr for premium tier
                    label="model_tier_premium",
                )
            )

        # You can add tenant/API-key-based keys here too.

        return limits
