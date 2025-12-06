-- 002_seed_demo_data.sql

-- 1) Tenants
INSERT INTO tenant (name)
VALUES 
  ('enterprise_co'),
  ('free_co')
ON CONFLICT DO NOTHING;

-- 2) Users
INSERT INTO user_account (tenant_id, external_id)
VALUES
  ((SELECT id FROM tenant WHERE name = 'enterprise_co'), 'ent-user-1'),
  ((SELECT id FROM tenant WHERE name = 'enterprise_co'), 'ent-user-2'),
  ((SELECT id FROM tenant WHERE name = 'free_co'), 'free-user-1')
ON CONFLICT DO NOTHING;

-- 3) API Keys (hash values are fake placeholders)
INSERT INTO api_key (tenant_id, key_hash, name)
VALUES
  ((SELECT id FROM tenant WHERE name = 'enterprise_co'),
    'hash_enterprise_key', 'enterprise-main-key'),
  ((SELECT id FROM tenant WHERE name = 'free_co'),
    'hash_free_key', 'free-main-key')
ON CONFLICT DO NOTHING;

-- 4) Model tiers
INSERT INTO model_tier (name, description)
VALUES
  ('premium',  'Expensive, high-capacity models like GPT-4'),
  ('standard', 'Mid-tier models'),
  ('free',     'Cheaper/smaller models')
ON CONFLICT DO NOTHING;

-- 5) Models
INSERT INTO model (name, tier_id)
VALUES
  ('gpt-4o', (SELECT id FROM model_tier WHERE name = 'premium')),
  ('gpt-4o-mini', (SELECT id FROM model_tier WHERE name = 'standard')),
  ('tiny-model', (SELECT id FROM model_tier WHERE name = 'free'))
ON CONFLICT DO NOTHING;


-- 6) Rate limit policies

-- 6.1 Global default: 100 req/hour (used when no more specific rule)
INSERT INTO rate_limit_policy (
    scope, window_seconds, limit_value, enabled
) VALUES (
    'GLOBAL', 3600, 1000000, TRUE
);


-- 6.2 Tenant-level override for enterprise_co: 500 req/hour
INSERT INTO rate_limit_policy (
    scope, tenant_id, window_seconds, limit_value, enabled
) VALUES (
    'TENANT',
    (SELECT id FROM tenant WHERE name = 'enterprise_co'),
    3600,
    500,
    TRUE
);


-- 6.3 API key override for free_co: 20 req/hour
INSERT INTO rate_limit_policy (
    scope, api_key_id, window_seconds, limit_value, enabled
) VALUES (
    'API_KEY',
    (SELECT id FROM api_key WHERE key_hash = 'hash_free_key'),
    3600,
    20,
    TRUE
);


-- 6.4 Model tier override for premium: 1000 req/hour
INSERT INTO rate_limit_policy (
    scope, model_tier_id, window_seconds, limit_value, enabled
) VALUES (
    'MODEL_TIER',
    (SELECT id FROM model_tier WHERE name = 'premium'),
    3600,
    1000,
    TRUE
);

-- 6.5 Model tier override for standard: 100 req/hour
INSERT INTO rate_limit_policy (
    scope, model_tier_id, window_seconds, limit_value, enabled
) VALUES (
    'MODEL_TIER',
    (SELECT id FROM model_tier WHERE name = 'standard'),
    3600,
    100,
    TRUE
);

-- 6.5 Model tier override for free: 10 req/hour
INSERT INTO rate_limit_policy (
    scope, model_tier_id, window_seconds, limit_value, enabled
) VALUES (
    'MODEL_TIER',
    (SELECT id FROM model_tier WHERE name = 'free'),
    3600,
    10,
    TRUE
);



-- 6.6 A very strict user+model limit for testing:
-- ent-user-2 on gpt-4o only gets 8 req/hour
INSERT INTO rate_limit_policy (
    scope, user_id, model_id, window_seconds, limit_value, enabled
) VALUES (
    'USER_MODEL',
    (SELECT ua.id
       FROM user_account ua
       JOIN tenant t ON ua.tenant_id = t.id
      WHERE t.name = 'enterprise_co'
        AND ua.external_id = 'ent-user-2'),
    (SELECT id FROM model WHERE name = 'gpt-4o'),
    3600,
    10,
    TRUE
);
