CREATE TABLE tenant (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_account (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
  external_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE api_key (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
  key_hash TEXT NOT NULL UNIQUE,
  name TEXT,
  revoked INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE model_tier (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  description TEXT
);

CREATE TABLE model (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  tier_id INTEGER REFERENCES model_tier(id),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rate_limit_policy (
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

INSERT INTO tenant (name) VALUES ('enterprise_co'), ('free_co');

INSERT INTO user_account (tenant_id, external_id)
VALUES
  ((SELECT id FROM tenant WHERE name = 'enterprise_co'), 'ent-user-1'),
  ((SELECT id FROM tenant WHERE name = 'enterprise_co'), 'ent-user-2'),
  ((SELECT id FROM tenant WHERE name = 'free_co'), 'free-user-1');

INSERT INTO api_key (tenant_id, key_hash, name)
VALUES
  ((SELECT id FROM tenant WHERE name = 'enterprise_co'), 'hash_enterprise_key', 'enterprise-main-key'),
  ((SELECT id FROM tenant WHERE name = 'free_co'), 'hash_free_key', 'free-main-key');

INSERT INTO model_tier (name, description)
VALUES
  ('premium', 'Expensive, high-capacity models like GPT-4'),
  ('standard', 'Mid-tier models'),
  ('free', 'Cheaper/smaller models');

INSERT INTO model (name, tier_id)
VALUES
  ('gpt-4o', (SELECT id FROM model_tier WHERE name = 'premium')),
  ('gpt-4o-mini', (SELECT id FROM model_tier WHERE name = 'standard')),
  ('tiny-model', (SELECT id FROM model_tier WHERE name = 'free'));

INSERT INTO rate_limit_policy (scope, window_seconds, limit_value, enabled)
VALUES ('GLOBAL', 3600, 1000000, 1);

INSERT INTO rate_limit_policy (scope, tenant_id, window_seconds, limit_value, enabled)
VALUES (
  'TENANT',
  (SELECT id FROM tenant WHERE name = 'enterprise_co'),
  3600,
  500,
  1
);

INSERT INTO rate_limit_policy (scope, tenant_id, window_seconds, limit_value, enabled)
VALUES (
  'TENANT',
  (SELECT id FROM tenant WHERE name = 'free_co'),
  3600,
  50,
  1
);

INSERT INTO rate_limit_policy (scope, api_key_id, window_seconds, limit_value, enabled)
VALUES (
  'API_KEY',
  (SELECT id FROM api_key WHERE key_hash = 'hash_free_key'),
  3600,
  20,
  1
);

INSERT INTO rate_limit_policy (scope, model_tier_id, window_seconds, limit_value, enabled)
VALUES
  ('MODEL_TIER', (SELECT id FROM model_tier WHERE name = 'premium'), 3600, 1000, 1),
  ('MODEL_TIER', (SELECT id FROM model_tier WHERE name = 'standard'), 3600, 100, 1),
  ('MODEL_TIER', (SELECT id FROM model_tier WHERE name = 'free'), 3600, 10, 1);

INSERT INTO rate_limit_policy (scope, user_id, model_id, window_seconds, limit_value, enabled)
VALUES (
  'USER_MODEL',
  (SELECT ua.id FROM user_account ua JOIN tenant t ON ua.tenant_id = t.id
   WHERE t.name = 'enterprise_co' AND ua.external_id = 'ent-user-2'),
  (SELECT id FROM model WHERE name = 'gpt-4o'),
  3600,
  10,
  1
);
