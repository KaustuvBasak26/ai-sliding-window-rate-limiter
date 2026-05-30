import sqlite3
from typing import List, Optional

from models import RateLimitRequest
from policy_resolver import EffectiveLimit


class SqlitePolicyResolver:
    """PolicyResolver backed by a SQLite connection (typically :memory: per demo session)."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _fetch_one(self, query: str, params: tuple) -> Optional[dict]:
        cur = self.conn.execute(query, params)
        row = cur.fetchone()
        if not row:
            return None
        return dict(row)

    def _get_tenant_id(self, tenant_name: Optional[str]) -> Optional[int]:
        if not tenant_name:
            return None
        row = self._fetch_one("SELECT id FROM tenant WHERE name = ?", (tenant_name,))
        return row["id"] if row else None

    def _get_user_id(self, tenant_id: Optional[int], external_id: Optional[str]) -> Optional[int]:
        if not tenant_id or not external_id:
            return None
        row = self._fetch_one(
            """
            SELECT id FROM user_account
            WHERE tenant_id = ? AND external_id = ?
            """,
            (tenant_id, external_id),
        )
        return row["id"] if row else None

    def _get_api_key_id(self, api_key_value: Optional[str]) -> Optional[int]:
        if not api_key_value:
            return None
        row = self._fetch_one(
            "SELECT id FROM api_key WHERE key_hash = ? AND revoked = 0",
            (api_key_value,),
        )
        return row["id"] if row else None

    def _get_model_id_and_tier(self, model_name: Optional[str]) -> tuple[Optional[int], Optional[int]]:
        if not model_name:
            return None, None
        row = self._fetch_one(
            "SELECT id, tier_id FROM model WHERE name = ?",
            (model_name,),
        )
        if not row:
            return None, None
        return row["id"], row["tier_id"]

    def _get_model_tier_id_by_name(self, tier_name: Optional[str]) -> Optional[int]:
        if not tier_name:
            return None
        row = self._fetch_one(
            "SELECT id FROM model_tier WHERE name = ?",
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
        cur = self.conn.execute(
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
            WHERE enabled = 1
              AND (
                    scope = 'GLOBAL'
                 OR (scope = 'TENANT'     AND tenant_id     = ?)
                 OR (scope = 'API_KEY'    AND api_key_id    = ?)
                 OR (scope = 'MODEL'      AND model_id      = ?)
                 OR (scope = 'MODEL_TIER' AND model_tier_id = ?)
                 OR (scope = 'USER_MODEL' AND user_id       = ? AND model_id = ?)
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
        return [dict(row) for row in cur.fetchall()]

    def _redis_key_for_policy(self, policy: dict) -> str:
        scope = policy["scope"]
        if scope == "GLOBAL":
            return "rl:global"
        if scope == "TENANT":
            return f"rl:tenant:{policy['tenant_id']}"
        if scope == "API_KEY":
            return f"rl:apikey:{policy['api_key_id']}"
        if scope == "MODEL":
            return f"rl:model:{policy['model_id']}"
        if scope == "MODEL_TIER":
            return f"rl:modeltier:{policy['model_tier_id']}"
        if scope == "USER_MODEL":
            return f"rl:user:{policy['user_id']}:model:{policy['model_id']}"
        return f"rl:unknown:{policy['id']}"

    def resolve(self, body: RateLimitRequest) -> List[EffectiveLimit]:
        tenant_id = self._get_tenant_id(body.tenantId)
        user_id = self._get_user_id(tenant_id, body.userId)
        api_key_id = self._get_api_key_id(body.apiKey)
        model_id, model_tier_id_from_model = self._get_model_id_and_tier(body.modelId)
        explicit_tier_id = self._get_model_tier_id_by_name(body.modelTier)
        model_tier_id = explicit_tier_id or model_tier_id_from_model

        policies = self._get_applicable_policies(
            tenant_id=tenant_id,
            user_id=user_id,
            api_key_id=api_key_id,
            model_id=model_id,
            model_tier_id=model_tier_id,
        )

        effective_limits: List[EffectiveLimit] = []
        for policy in policies:
            key = self._redis_key_for_policy(policy)
            scope_label = policy["scope"]
            if scope_label == "MODEL_TIER" and policy.get("model_tier_id"):
                tier_row = self._fetch_one(
                    "SELECT name FROM model_tier WHERE id = ?",
                    (policy["model_tier_id"],),
                )
                if tier_row:
                    scope_label = f"{tier_row['name'].upper()}_TIER"

            effective_limits.append(
                EffectiveLimit(
                    key=key,
                    window_seconds=policy["window_seconds"],
                    limit=policy["limit_value"],
                    label=scope_label,
                    scope=policy["scope"],
                )
            )

        return effective_limits
