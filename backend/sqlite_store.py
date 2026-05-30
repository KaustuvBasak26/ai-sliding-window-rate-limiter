"""SQLite schema + demo seed for policy storage."""

import os
import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tenant (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_account (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
  external_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_key (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
  key_hash TEXT NOT NULL UNIQUE,
  name TEXT,
  revoked INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_tier (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  description TEXT
);

CREATE TABLE IF NOT EXISTS model (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  tier_id INTEGER REFERENCES model_tier(id),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rate_limit_policy (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scope TEXT NOT NULL,
  tenant_id INTEGER REFERENCES tenant(id),
  user_id INTEGER REFERENCES user_account(id),
  api_key_id INTEGER REFERENCES api_key(id),
  model_id INTEGER REFERENCES model(id),
  model_tier_id INTEGER REFERENCES model_tier(id),
  window_seconds INTEGER NOT NULL,
  limit_value INTEGER NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rate_limit_policy_scope ON rate_limit_policy(scope);
CREATE INDEX IF NOT EXISTS idx_rate_limit_policy_tenant ON rate_limit_policy(tenant_id);
CREATE INDEX IF NOT EXISTS idx_rate_limit_policy_user ON rate_limit_policy(user_id);
CREATE INDEX IF NOT EXISTS idx_rate_limit_policy_apikey ON rate_limit_policy(api_key_id);
CREATE INDEX IF NOT EXISTS idx_rate_limit_policy_model ON rate_limit_policy(model_id);
CREATE INDEX IF NOT EXISTS idx_rate_limit_policy_model_tier ON rate_limit_policy(model_tier_id);
"""


SEED_SQL = """
INSERT OR IGNORE INTO tenant (name) VALUES ('enterprise_co'), ('free_co');

INSERT OR IGNORE INTO user_account (tenant_id, external_id)
SELECT id, 'ent-user-1' FROM tenant WHERE name = 'enterprise_co';
INSERT OR IGNORE INTO user_account (tenant_id, external_id)
SELECT id, 'ent-user-2' FROM tenant WHERE name = 'enterprise_co';
INSERT OR IGNORE INTO user_account (tenant_id, external_id)
SELECT id, 'free-user-1' FROM tenant WHERE name = 'free_co';

INSERT OR IGNORE INTO api_key (tenant_id, key_hash, name)
SELECT id, 'hash_enterprise_key', 'enterprise-main-key' FROM tenant WHERE name = 'enterprise_co';
INSERT OR IGNORE INTO api_key (tenant_id, key_hash, name)
SELECT id, 'hash_free_key', 'free-main-key' FROM tenant WHERE name = 'free_co';

INSERT OR IGNORE INTO model_tier (name, description) VALUES
  ('premium', 'Expensive, high-capacity models like GPT-4'),
  ('standard', 'Mid-tier models'),
  ('free', 'Cheaper/smaller models');

INSERT OR IGNORE INTO model (name, tier_id)
SELECT 'gpt-4o', id FROM model_tier WHERE name = 'premium';
INSERT OR IGNORE INTO model (name, tier_id)
SELECT 'gpt-4o-mini', id FROM model_tier WHERE name = 'standard';
INSERT OR IGNORE INTO model (name, tier_id)
SELECT 'tiny-model', id FROM model_tier WHERE name = 'free';

INSERT INTO rate_limit_policy (scope, window_seconds, limit_value, enabled)
SELECT 'GLOBAL', 3600, 1000000, 1
WHERE NOT EXISTS (SELECT 1 FROM rate_limit_policy WHERE scope = 'GLOBAL');

INSERT INTO rate_limit_policy (scope, tenant_id, window_seconds, limit_value, enabled)
SELECT 'TENANT', id, 3600, 500, 1 FROM tenant WHERE name = 'enterprise_co'
AND NOT EXISTS (
  SELECT 1 FROM rate_limit_policy WHERE scope = 'TENANT' AND tenant_id = tenant.id
);

INSERT INTO rate_limit_policy (scope, tenant_id, window_seconds, limit_value, enabled)
SELECT 'TENANT', id, 3600, 50, 1 FROM tenant WHERE name = 'free_co'
AND NOT EXISTS (
  SELECT 1 FROM rate_limit_policy p JOIN tenant t ON p.tenant_id = t.id
  WHERE p.scope = 'TENANT' AND t.name = 'free_co'
);

INSERT INTO rate_limit_policy (scope, api_key_id, window_seconds, limit_value, enabled)
SELECT 'API_KEY', id, 3600, 20, 1 FROM api_key WHERE key_hash = 'hash_free_key'
AND NOT EXISTS (
  SELECT 1 FROM rate_limit_policy WHERE scope = 'API_KEY' AND api_key_id = api_key.id
);

INSERT INTO rate_limit_policy (scope, model_tier_id, window_seconds, limit_value, enabled)
SELECT 'MODEL_TIER', id, 3600, 1000, 1 FROM model_tier WHERE name = 'premium'
AND NOT EXISTS (
  SELECT 1 FROM rate_limit_policy WHERE scope = 'MODEL_TIER' AND model_tier_id = model_tier.id
);

INSERT INTO rate_limit_policy (scope, model_tier_id, window_seconds, limit_value, enabled)
SELECT 'MODEL_TIER', id, 3600, 100, 1 FROM model_tier WHERE name = 'standard'
AND NOT EXISTS (
  SELECT 1 FROM rate_limit_policy WHERE scope = 'MODEL_TIER' AND model_tier_id = model_tier.id
);

INSERT INTO rate_limit_policy (scope, model_tier_id, window_seconds, limit_value, enabled)
SELECT 'MODEL_TIER', id, 3600, 10, 1 FROM model_tier WHERE name = 'free'
AND NOT EXISTS (
  SELECT 1 FROM rate_limit_policy WHERE scope = 'MODEL_TIER' AND model_tier_id = model_tier.id
);

INSERT INTO rate_limit_policy (scope, user_id, model_id, window_seconds, limit_value, enabled)
SELECT ua.id, m.id, 3600, 10, 1
FROM user_account ua
JOIN tenant t ON ua.tenant_id = t.id
JOIN model m ON m.name = 'gpt-4o'
WHERE t.name = 'enterprise_co' AND ua.external_id = 'ent-user-2'
AND NOT EXISTS (
  SELECT 1 FROM rate_limit_policy
  WHERE scope = 'USER_MODEL' AND user_id = ua.id AND model_id = m.id
);
"""


def reset_sqlite_file(path: str) -> None:
    if path == ":memory:":
        return
    file_path = Path(path)
    if file_path.exists():
        file_path.unlink()


def initialize_sqlite(path: str, reset: bool = False) -> None:
    if reset:
        reset_sqlite_file(path)

    conn = sqlite3.connect(path, check_same_thread=False)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.executescript(SEED_SQL)
        conn.commit()
        print(f"SQLite policy store ready at {path}")
    finally:
        conn.close()


def is_initialized(path: str) -> bool:
    if path != ":memory:" and not Path(path).exists():
        return False

    conn = sqlite3.connect(path, check_same_thread=False)
    try:
        row = conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'rate_limit_policy'
            """
        ).fetchone()
        return row is not None
    finally:
        conn.close()
