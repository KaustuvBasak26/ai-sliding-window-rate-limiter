import React, { useEffect, useRef, useState } from "react";
import { getPreferredTheme, initTheme, setTheme } from "./theme.js";

const API_BASE =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD ? "" : "http://localhost:8000");

const PORTFOLIO_URL = "https://kaustuvbasak.com/";

const DEMO_PRESETS = {
  enterprise: {
    label: "Enterprise demo",
    tenantId: "enterprise_co",
    userId: "ent-user-1",
    modelId: "gpt-4o",
    modelTier: "premium",
  },
  free: {
    label: "Free tier demo",
    tenantId: "free_co",
    userId: "free-user-1",
    modelId: "tiny-model",
    modelTier: "free",
  },
};

function createDemoSessionId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `demo-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function formatWindow(windowSeconds) {
  if (windowSeconds >= 3600 && windowSeconds % 3600 === 0) {
    const hours = windowSeconds / 3600;
    return `${hours} hour${hours === 1 ? "" : "s"} window`;
  }
  if (windowSeconds >= 60 && windowSeconds % 60 === 0) {
    const minutes = windowSeconds / 60;
    return `${minutes} minute${minutes === 1 ? "" : "s"} window`;
  }
  return `${windowSeconds} second${windowSeconds === 1 ? "" : "s"} window`;
}

function progressColor(count, limit) {
  if (!limit || limit <= 0) {
    return "var(--muted)";
  }
  const percentage = Math.min((count / limit) * 100, 100);
  if (percentage > 80) return "var(--danger)";
  if (percentage > 50) return "var(--warning)";
  return "var(--success)";
}

function usagePercent(count, limit) {
  if (!limit || limit <= 0) {
    return 0;
  }
  return Math.min((count / limit) * 100, 100);
}

function requestPayloadKey({ tenantId, userId, modelId, modelTier }) {
  return JSON.stringify({ tenantId, userId, modelId, modelTier });
}

function snapshotKey(snapshot) {
  if (!snapshot) {
    return "";
  }
  return requestPayloadKey(snapshot);
}

function formatMatchLabel(label, matched) {
  return `${label}: ${matched ? "matched" : "not in demo DB"}`;
}

function ThemeToggle({ theme, onChange }) {
  return (
    <div className="theme-toggle" role="group" aria-label="Color theme">
      <button
        type="button"
        className={theme === "light" ? "active" : ""}
        aria-pressed={theme === "light"}
        onClick={() => onChange("light")}
      >
        Light
      </button>
      <button
        type="button"
        className={theme === "dark" ? "active" : ""}
        aria-pressed={theme === "dark"}
        onClick={() => onChange("dark")}
      >
        Dark
      </button>
    </div>
  );
}

function AppHeader({ demoSessionId, theme, onThemeChange }) {
  return (
    <header className="header">
      <div className="header-row">
        <div>
          <div className="header-brand">
            <span className="header-kb">KB</span>
            <h1>Sliding Window Rate Limiter</h1>
          </div>
          <p>
            Interactive demo — check limits across tenant, user, model, and tier
            policies. Reload the page to reset your session.
          </p>
          <a
            href={PORTFOLIO_URL}
            className="header-portfolio-link"
            target="_blank"
            rel="noopener noreferrer"
          >
            ← Back to kaustuvbasak.com
          </a>
        </div>
        <div className="header-actions">
          <ThemeToggle theme={theme} onChange={onThemeChange} />
          <div className="header-stats">
            <div className="stat" title={demoSessionId}>
              <span className="stat-label">Session</span>
              <span className="stat-value">{demoSessionId.slice(0, 8)}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Mode</span>
              <span className="stat-value">Live</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

function App() {
  const [userId, setUserId] = useState("ent-user-1");
  const [modelId, setModelId] = useState("gpt-4o");
  const [tenantId, setTenantId] = useState("enterprise_co");
  const [modelTier, setModelTier] = useState("premium");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [authChecked, setAuthChecked] = useState(false);
  const [authRequired, setAuthRequired] = useState(false);
  const [authenticated, setAuthenticated] = useState(true);
  const [accessPassword, setAccessPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [demoSessionId] = useState(createDemoSessionId);
  const [hasCheckedOnce, setHasCheckedOnce] = useState(false);
  const [showResultsIntro, setShowResultsIntro] = useState(false);
  const [theme, setThemeState] = useState(getPreferredTheme);
  const [lastSnapshotKey, setLastSnapshotKey] = useState("");
  const requestIdRef = useRef(0);

  const currentSnapshotKey = requestPayloadKey({ tenantId, userId, modelId, modelTier });
  const inputsChangedSinceCheck =
    hasCheckedOnce && lastSnapshotKey && currentSnapshotKey !== lastSnapshotKey;

  const apiHeaders = {
    "Content-Type": "application/json",
    "X-Demo-Session": demoSessionId,
  };

  useEffect(() => {
    initTheme();
    setThemeState(getPreferredTheme());
  }, []);

  const handleThemeChange = (nextTheme) => {
    setTheme(nextTheme);
    setThemeState(nextTheme);
  };

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/status`, {
          credentials: "include",
          headers: { "X-Demo-Session": demoSessionId },
        });
        if (!res.ok) {
          return;
        }
        const data = await res.json();
        setAuthRequired(Boolean(data.protected));
        setAuthenticated(Boolean(data.authenticated));
      } catch {
        // Local dev without auth endpoints still works.
      } finally {
        setAuthChecked(true);
      }
    };

    checkAuth();
  }, [demoSessionId]);

  const applyPreset = (presetKey) => {
    const preset = DEMO_PRESETS[presetKey];
    if (!preset || loading) {
      return;
    }
    setTenantId(preset.tenantId);
    setUserId(preset.userId);
    setModelId(preset.modelId);
    setModelTier(preset.modelTier);
    setError("");
  };

  const handleLogin = async (event) => {
    event.preventDefault();
    setAuthError("");

    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: apiHeaders,
        credentials: "include",
        body: JSON.stringify({ password: accessPassword }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Login failed");
      }

      setAuthenticated(true);
      setAccessPassword("");
    } catch (err) {
      setAuthError(err.message);
    }
  };

  const handleCheck = async () => {
    const requestId = ++requestIdRef.current;
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/rate-limit/check`, {
        method: "POST",
        headers: apiHeaders,
        credentials: "include",
        body: JSON.stringify({
          userId,
          modelId,
          tenantId,
          modelTier,
        }),
      });

      if (requestId !== requestIdRef.current) {
        return;
      }

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Request failed");
      }

      const data = await res.json();
      if (requestId !== requestIdRef.current) {
        return;
      }

      if (!hasCheckedOnce) {
        setShowResultsIntro(true);
      }
      setResult(data);
      setHasCheckedOnce(true);
      setLastSnapshotKey(snapshotKey(data.requestSnapshot) || currentSnapshotKey);
    } catch (e) {
      if (requestId !== requestIdRef.current) {
        return;
      }
      setError(e.message);
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false);
      }
    }
  };

  const renderResults = () => {
    if (!hasCheckedOnce && !result) {
      return (
        <div className="results-placeholder">
          <p className="results-placeholder-title">Results panel</p>
          <p>
            Click <strong>Check Rate Limit</strong> to see usage, policies, and block
            reasons here.
          </p>
        </div>
      );
    }

    if (!result) {
      return null;
    }

    const percent = usagePercent(result.count, result.limit);
    const boundedCount = Math.min(result.count, result.limit);
    const snapshot = result.requestSnapshot || {
      tenantId,
      userId,
      modelId,
      modelTier,
    };
    const match = result.contextMatch;
    const unmatched = match
      ? [
          !match.tenantMatched && snapshot.tenantId ? "tenant" : null,
          !match.userMatched ? "user" : null,
          !match.modelMatched ? "model" : null,
          match.tierMatched === false && snapshot.modelTier ? "tier" : null,
        ].filter(Boolean)
      : [];

    return (
      <div
        className={`results-content${showResultsIntro ? " is-first-show" : ""}`}
      >
        {loading && (
          <div className="loading-pill" aria-hidden="true">
            <span className="loading-dot" />
            Updating...
          </div>
        )}

        {inputsChangedSinceCheck && !loading && (
          <div className="context-banner context-banner-stale" role="status">
            Form values changed — click <strong>Check Rate Limit</strong> to evaluate
            the new context.
          </div>
        )}

        <div className="context-strip">
          <div className="context-strip-row">
            <span className="context-chip">
              <span className="context-chip-label">Tenant</span>
              <code>{snapshot.tenantId || "—"}</code>
            </span>
            <span className="context-chip">
              <span className="context-chip-label">User</span>
              <code>{snapshot.userId}</code>
            </span>
            <span className="context-chip">
              <span className="context-chip-label">Model</span>
              <code>{snapshot.modelId}</code>
            </span>
            <span className="context-chip">
              <span className="context-chip-label">Tier</span>
              <code>{snapshot.modelTier || "—"}</code>
            </span>
          </div>
          {result.primaryPolicy && (
            <p className="context-primary-policy">
              Primary policy: <strong>{result.primaryPolicy}</strong>
            </p>
          )}
        </div>

        {match && unmatched.length > 0 && (
          <div className="context-banner context-banner-warn" role="note">
            Unknown {unmatched.join(", ")} — only tier/global policies apply. Use the
            demo presets or seeded names like <code>free_co</code>,{" "}
            <code>tiny-model</code>.
          </div>
        )}

        {match && (
          <div className="match-grid" aria-label="Database match status">
            <span className={`match-pill ${match.tenantMatched ? "ok" : "miss"}`}>
              {formatMatchLabel("Tenant", match.tenantMatched)}
            </span>
            <span className={`match-pill ${match.userMatched ? "ok" : "miss"}`}>
              {formatMatchLabel("User", match.userMatched)}
            </span>
            <span className={`match-pill ${match.modelMatched ? "ok" : "miss"}`}>
              {formatMatchLabel("Model", match.modelMatched)}
            </span>
            <span className={`match-pill ${match.tierMatched ? "ok" : "miss"}`}>
              {formatMatchLabel("Tier", match.tierMatched)}
            </span>
          </div>
        )}

        <div
          className={`status-badge ${result.allowed ? "allowed" : "blocked"}`}
          role="status"
        >
          {result.allowed ? "Request Allowed" : "Request Blocked"}
        </div>

        <div className="usage-block">
          <div className="usage-header">
            <span className="usage-label">Primary Limit Usage</span>
            <span className="usage-count" aria-live="polite" aria-atomic="true">
              {result.count} / {result.limit}
            </span>
          </div>
          <div
            className="progress-track"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={result.limit}
            aria-valuenow={boundedCount}
            aria-label="Primary limit usage"
          >
            <div
              className="progress-fill"
              style={{
                width: `${percent}%`,
                backgroundColor: progressColor(result.count, result.limit),
              }}
            />
          </div>
          <p className="window-caption">{formatWindow(result.windowSeconds)}</p>
        </div>

        {result.cause && !result.allowed && (
          <div className="cause-box" role="alert">
            <strong>Reason:</strong> {result.cause}
          </div>
        )}

        {result.allowed && result.fulfilled && result.fulfilled.length > 0 && (
          <div className="policies-box">
            <p className="policies-title">Satisfied Policies</p>
            {result.fulfilled.map((policy, idx) => (
              <div key={`${policy.label}-${idx}`} className="policy-row">
                <div className="policy-row-header">
                  <span className="policy-label">{policy.label}</span>
                  <span className="policy-count">
                    {policy.count}/{policy.limit}
                  </span>
                </div>
                <p className="policy-window">
                  {formatWindow(policy.windowSeconds)}
                </p>
              </div>
            ))}
          </div>
        )}

        <p className="results-hint">
          Click again to increment usage, or reload the page to reset your session
        </p>
      </div>
    );
  };

  if (!authChecked) {
    return (
      <div className="center-shell">
        <p className="loading-shell-text">Loading...</p>
      </div>
    );
  }

  if (authRequired && !authenticated) {
    return (
      <div className="app">
        <AppHeader
          demoSessionId={demoSessionId}
          theme={theme}
          onThemeChange={handleThemeChange}
        />
        <div className="center-shell">
          <div className="auth-card">
            <h1>Access Required</h1>
            <p>Enter the deployment password to continue</p>
            <form onSubmit={handleLogin}>
              <label className="field-label" htmlFor="access-password">
                Access Password
              </label>
              <input
                id="access-password"
                type="password"
                value={accessPassword}
                onChange={(e) => setAccessPassword(e.target.value)}
                className="field-input"
                style={{ marginBottom: "1rem" }}
                autoComplete="current-password"
              />
              <button type="submit" className="btn-primary">
                Unlock App
              </button>
            </form>
            {authError && <div className="alert-error">{authError}</div>}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <AppHeader
        demoSessionId={demoSessionId}
        theme={theme}
        onThemeChange={handleThemeChange}
      />

      <main className="main">
        <section className="panel">
          <div className="panel-header">
            <h2>Request context</h2>
            <span className="badge">Demo</span>
          </div>
          <div className="panel-body">
            <div className="preset-row">
              {Object.entries(DEMO_PRESETS).map(([key, preset]) => (
                <button
                  key={key}
                  type="button"
                  className="preset-btn"
                  disabled={loading}
                  onClick={() => applyPreset(key)}
                >
                  {preset.label}
                </button>
              ))}
            </div>
            <form
              className="form-grid form-grid-two"
              onSubmit={(e) => {
                e.preventDefault();
                handleCheck();
              }}
            >
              <div>
                <label className="field-label" htmlFor="tenant-id">
                  Tenant ID
                </label>
                <input
                  id="tenant-id"
                  type="text"
                  value={tenantId}
                  onChange={(e) => setTenantId(e.target.value)}
                  className="field-input"
                  placeholder="enterprise_co"
                  disabled={loading}
                />
              </div>

              <div>
                <label className="field-label" htmlFor="user-id">
                  User ID
                </label>
                <input
                  id="user-id"
                  type="text"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  className="field-input"
                  placeholder="ent-user-1"
                  disabled={loading}
                />
              </div>

              <div>
                <label className="field-label" htmlFor="model-id">
                  Model ID
                </label>
                <input
                  id="model-id"
                  type="text"
                  value={modelId}
                  onChange={(e) => setModelId(e.target.value)}
                  className="field-input"
                  placeholder="gpt-4o"
                  disabled={loading}
                />
              </div>

              <div>
                <label className="field-label" htmlFor="model-tier">
                  Model Tier
                </label>
                <select
                  id="model-tier"
                  value={modelTier}
                  onChange={(e) => setModelTier(e.target.value)}
                  className="field-select"
                  disabled={loading}
                >
                  <option value="premium">Premium</option>
                  <option value="standard">Standard</option>
                  <option value="free">Free</option>
                </select>
              </div>

              <div className="form-span-all">
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? "Checking..." : "Check Rate Limit"}
                </button>
              </div>
            </form>

            {error && <div className="alert-error">{error}</div>}
          </div>
        </section>

        <section
          className={`panel panel-results ${loading ? "is-loading" : ""}`}
          aria-live="polite"
          aria-busy={loading}
        >
          <div className="panel-header">
            <h2>Result</h2>
          </div>
          <div className="panel-body">
            <div
              className={`panel-results-body ${
                !hasCheckedOnce && !result ? "is-empty" : ""
              }`}
            >
              {renderResults()}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
