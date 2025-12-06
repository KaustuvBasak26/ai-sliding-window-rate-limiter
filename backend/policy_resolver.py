from dataclasses import dataclass
from typing import List, Optional

from models import RateLimitRequest


@dataclass
class EffectiveLimit:
    key: str
    window_seconds: int
    limit: int
    name: str  # Human-readable name for the cause


class PolicyResolver:
    """
    Very simple policy resolver:
    - Default user+model limit: 100 req/hour
    - Global per-model limit: 1000 req/hour
    - You can extend this to read from DB based on tenantId, apiKey, modelTier, etc.
    """

    DEFAULT_USER_LIMIT = 100
    DEFAULT_MODEL_GLOBAL_LIMIT = 10000
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
                name="User + Model Limit",
            )
        )

        # Global per-model key (protect GPU pool)
        model_key = f"rl:model:{body.modelId}:global"
        limits.append(
            EffectiveLimit(
                key=model_key,
                window_seconds=self.WINDOW_SECONDS,
                limit=self.DEFAULT_MODEL_GLOBAL_LIMIT,
                name="Global Model Limit",
            )
        )

        # Example: stricter limit for "premium" (pretend it's expensive like GPT-4)
        if body.modelTier == "premium":
            tier_key = f"rl:tier:premium:model:{body.modelId}"
            limits.append(
                EffectiveLimit(
                    key=tier_key,
                    window_seconds=self.WINDOW_SECONDS,
                    limit=1000,   # 1000/hr for premium tier
                    name="Premium Tier Limit",
                )
            )
        if body.modelTier == "standard":
            tier_key = f"rl:tier:premium:model:{body.modelId}"
            limits.append(
                EffectiveLimit(
                    key=tier_key,
                    window_seconds=self.WINDOW_SECONDS,
                    limit=100,   # 100/hr for premium tier
                    name="Standard Tier Limit",
                )
            )

        if body.modelTier == "free":
            tier_key = f"rl:tier:premium:model:{body.modelId}"
            limits.append(
                EffectiveLimit(
                    key=tier_key,
                    window_seconds=self.WINDOW_SECONDS,
                    limit=10,   # 10/hr for premium tier
                    name="Free Tier Limit",
                )
            )


        # You can add tenant/API-key-based keys here too.

        return limits
