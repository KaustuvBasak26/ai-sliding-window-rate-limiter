-- 001_create_types_and_tables.sql

-- 1) Enum for policy scope
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'policy_scope') THEN
        CREATE TYPE policy_scope AS ENUM (
          'GLOBAL',
          'TENANT',
          'API_KEY',
          'MODEL',
          'MODEL_TIER',
          'USER_MODEL'
        );
    END IF;
END$$;


-- 2) Core tables

CREATE TABLE IF NOT EXISTS tenant (
  id          SERIAL PRIMARY KEY,
  name        VARCHAR(100) NOT NULL,
  created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_account (
  id          SERIAL PRIMARY KEY,
  tenant_id   INTEGER NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
  external_id VARCHAR(255),
  created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS api_key (
  id          SERIAL PRIMARY KEY,
  tenant_id   INTEGER NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
  key_hash    VARCHAR(255) NOT NULL UNIQUE,
  name        VARCHAR(100),
  revoked     BOOLEAN NOT NULL DEFAULT FALSE,
  created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS model_tier (
  id          SERIAL PRIMARY KEY,
  name        VARCHAR(50) UNIQUE NOT NULL,  -- 'premium', 'standard', 'free'
  description TEXT
);

CREATE TABLE IF NOT EXISTS model (
  id          SERIAL PRIMARY KEY,
  name        VARCHAR(100) UNIQUE NOT NULL, -- e.g. 'gpt-4o'
  tier_id     INTEGER REFERENCES model_tier(id),
  created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);


-- 3) Rate limit policy table

CREATE TABLE IF NOT EXISTS rate_limit_policy (
  id              SERIAL PRIMARY KEY,
  scope           policy_scope NOT NULL,

  tenant_id       INTEGER REFERENCES tenant(id),
  user_id         INTEGER REFERENCES user_account(id),
  api_key_id      INTEGER REFERENCES api_key(id),
  model_id        INTEGER REFERENCES model(id),
  model_tier_id   INTEGER REFERENCES model_tier(id),

  window_seconds  INTEGER NOT NULL,
  limit_value     INTEGER NOT NULL,
  enabled         BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);


-- 4) Helpful indexes for PolicyResolver lookups

CREATE INDEX IF NOT EXISTS idx_rate_limit_policy_scope
  ON rate_limit_policy(scope);

CREATE INDEX IF NOT EXISTS idx_rate_limit_policy_tenant
  ON rate_limit_policy(tenant_id);

CREATE INDEX IF NOT EXISTS idx_rate_limit_policy_user
  ON rate_limit_policy(user_id);

CREATE INDEX IF NOT EXISTS idx_rate_limit_policy_apikey
  ON rate_limit_policy(api_key_id);

CREATE INDEX IF NOT EXISTS idx_rate_limit_policy_model
  ON rate_limit_policy(model_id);

CREATE INDEX IF NOT EXISTS idx_rate_limit_policy_model_tier
  ON rate_limit_policy(model_tier_id);

