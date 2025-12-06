# backend/policy_resolver.py
from dataclasses import dataclass
from typing import List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from models import RateLimitRequest


@dataclass
class EffectiveLimit:
    key: str
    window_seconds: int
    limit: int
    label: str


# Scope precedence (higher = more specific)
SCOPE_PRECEDENCE = {
    "USER_MODEL": 6,
    "API_KEY": 5,
    "TENANT": 4,
    "MODEL": 3,
    "MODEL_TIER": 2,
    "GLOBAL": 1,
}


class PolicyResolver:
    """
    DB-backed PolicyResolver using Postgres.

    Mapping assumptions:
    - body.tenantId   = tenant.name
    - body.userId     = user_account.external_id
    - body.apiKey     = api_key.key_hash
    - body.modelId    = model.name
    - body.modelTier  = model_tier.name (optional hint; tier can also be derived from model)
    """

    def __init__(self, dsn: str):
        self.dsn = dsn
        # simple persistent connection for demo; in prod use a pool
        self.conn = psycopg2.connect(self.dsn)

    def _fetch_one(self, query: str, params: tuple) -> Optional[dict]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def _get_tenant_id(self, tenant_name: Optional[str]) -> Optional[int]:
        if not tenant_name:
            return None
        row = self._fetch_one(
            "SELECT id FROM tenant WHERE name = %s",
            (tenant_name,),
        )
        return row["id"] if row else None

    def _get_user_id(self, tenant_id: Optional[int], external_id: Optional[str]) -> Optional[int]:
        if not tenant_id or not external_id:
            return None
        row = self._fetch_one(
            """
            SELECT id FROM user_account
            WHERE tenant_id = %s AND external_id = %s
            """,
            (tenant_id, external_id),
        )
        return row["id"] if row else None

    def _get_api_key_id(self, api_key_value: Optional[str]) -> Optional[int]:
        if not api_key_value:
            return None
        row = self._fetch_one(
            "SELECT id FROM api_key WHERE key_hash = %s AND revoked = FALSE",
            (api_key_value,),
        )
        return row["id"] if row else None

    def _get_model_id_and_tier(self, model_name: Optional[str]) -> tuple[Optional[int], Optional[int]]:
        if not model_name:
            return None, None
        row = self._fetch_one(
            "SELECT id, tier_id FROM model WHERE name = %s",
            (model_name,),
        )
        if not row:
            return None, None
        return row["id"], row["tier_id"]

    def _get_model_tier_id_by_name(self, tier_name: Optional[str]) -> Optional[int]:
        if not tier_name:
            return None
        row = self._fetch_one(
            "SELECT id FROM model_tier WHERE name = %s",
            (tier_name,),
        )
        return row["id"] if row else None

    def _get_applicable_policies(
        self,
        tenant_id: Optional[int],
        user_id: Optional[int],
        api_key_id: Optional[int],
        model_id: Optional[int],
        model_tier_id: Optional[int],
    ) -> List[dict]:
        # We'll pass all IDs; for NULLs, the matching WHERE conditions simply won't fire.
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT *,
                       CASE scope
                         WHEN 'USER_MODEL' THEN 6
                         WHEN 'API_KEY'    THEN 5
                         WHEN 'TENANT'     THEN 4
                         WHEN 'MODEL'      THEN 3
                         WHEN 'MODEL_TIER' THEN 2
                         WHEN 'GLOBAL'     THEN 1
                         ELSE 0
                       END AS precedence
                FROM rate_limit_policy
                WHERE enabled = TRUE
                  AND (
                        scope = 'GLOBAL'
                     OR (scope = 'TENANT'     AND tenant_id     = %s)
                     OR (scope = 'API_KEY'    AND api_key_id    = %s)
                     OR (scope = 'MODEL'      AND model_id      = %s)
                     OR (scope = 'MODEL_TIER' AND model_tier_id = %s)
                     OR (scope = 'USER_MODEL' AND user_id       = %s AND model_id = %s)
                  )
                ORDER BY precedence DESC, id ASC
                """,
                (
                    tenant_id,
                    api_key_id,
                    model_id,
                    model_tier_id,
                    user_id,
                    model_id,
                ),
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def _redis_key_for_policy(self, policy: dict) -> str:
        scope = policy["scope"]
        if scope == "GLOBAL":
            return "rl:global"
        elif scope == "TENANT":
            return f"rl:tenant:{policy['tenant_id']}"
        elif scope == "API_KEY":
            return f"rl:apikey:{policy['api_key_id']}"
        elif scope == "MODEL":
            return f"rl:model:{policy['model_id']}"
        elif scope == "MODEL_TIER":
            return f"rl:modeltier:{policy['model_tier_id']}"
        elif scope == "USER_MODEL":
            return f"rl:user:{policy['user_id']}:model:{policy['model_id']}"
        else:
            # Fallback (should not happen)
            return f"rl:unknown:{policy['id']}"

    def resolve(self, body: RateLimitRequest) -> List[EffectiveLimit]:
        """
        Resolve all applicable policies for this request context and translate them
        into EffectiveLimit objects (each one corresponds to a Redis key to enforce).
        """

        # 1) Map request context -> DB IDs
        tenant_id = self._get_tenant_id(body.tenantId)
        user_id = self._get_user_id(tenant_id, body.userId)
        api_key_id = self._get_api_key_id(body.apiKey)

        model_id, model_tier_id_from_model = self._get_model_id_and_tier(body.modelId)

        # allow explicit modelTier override from request if provided
        explicit_tier_id = self._get_model_tier_id_by_name(body.modelTier)
        model_tier_id = explicit_tier_id or model_tier_id_from_model

        # 2) Fetch matching policies from DB
        policies = self._get_applicable_policies(
            tenant_id=tenant_id,
            user_id=user_id,
            api_key_id=api_key_id,
            model_id=model_id,
            model_tier_id=model_tier_id,
        )

        # 3) Translate policies → EffectiveLimit list
        effective_limits: List[EffectiveLimit] = []
        for p in policies:
            key = self._redis_key_for_policy(p)
            # Get tier name from DB if this is a MODEL_TIER scope
            scope_label = p["scope"]
            if scope_label == "MODEL_TIER" and p.get("model_tier_id"):
                tier_row = self._fetch_one(
                    "SELECT name FROM model_tier WHERE id = %s",
                    (p["model_tier_id"],),
                )
                if tier_row:
                    scope_label = f"{tier_row['name'].upper()}_TIER"
            
            effective_limits.append(
                EffectiveLimit(
                    key=key,
                    window_seconds=p["window_seconds"],
                    limit=p["limit_value"],
                    label=scope_label,
                )
            )

        return effective_limits
