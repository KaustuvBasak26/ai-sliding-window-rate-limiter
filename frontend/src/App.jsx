import { useState } from "react";

function App() {
  const [userId, setUserId] = useState("ent-user-1");
  const [modelId, setModelId] = useState("gpt-4o");
  const [tenantId, setTenantId] = useState("enterprise_co");
  const [modelTier, setModelTier] = useState("premium");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCheck = async () => {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await fetch("http://localhost:8000/rate-limit/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          modelId,
          tenantId,
          modelTier,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Request failed");
      }

      const data = await res.json();
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const containerStyle = {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "1.5rem",
  };

  const mainCardStyle = {
    background: "white",
    borderRadius: "1rem",
    boxShadow:
      "0 10px 40px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.1)",
    padding: "2.5rem",
    maxWidth: "500px",
    width: "100%",
  };

  const headerStyle = {
    marginBottom: "2rem",
    textAlign: "center",
  };

  const titleStyle = {
    fontSize: "2rem",
    fontWeight: "700",
    color: "var(--gray-900)",
    marginBottom: "0.5rem",
  };

  const subtitleStyle = {
    fontSize: "0.95rem",
    color: "var(--gray-500)",
  };

  const formGroupStyle = {
    marginBottom: "1.25rem",
  };

  const labelStyle = {
    display: "block",
    fontSize: "0.875rem",
    fontWeight: "600",
    color: "var(--gray-700)",
    marginBottom: "0.5rem",
  };

  const inputStyle = {
    width: "100%",
    padding: "0.75rem",
    fontSize: "0.95rem",
    border: "1px solid var(--gray-300)",
    borderRadius: "0.5rem",
    transition: "all 0.25s ease",
    outline: "none",
    boxSizing: "border-box",
  };

  const buttonStyle = {
    width: "100%",
    padding: "0.875rem",
    fontSize: "1rem",
    fontWeight: "600",
    color: "white",
    background: "var(--primary)",
    border: "none",
    borderRadius: "0.5rem",
    marginTop: "0.5rem",
    transition: "all 0.25s ease",
  };

  const resultCardStyle = {
    marginTop: "2rem",
    padding: "1.5rem",
    borderRadius: "0.75rem",
    border: "1px solid var(--gray-200)",
  };

  const statusBadgeStyle = (allowed) => ({
    display: "inline-flex",
    alignItems: "center",
    gap: "0.5rem",
    padding: "0.5rem 1rem",
    borderRadius: "0.5rem",
    fontWeight: "600",
    marginBottom: "1rem",
    backgroundColor: allowed ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
    color: allowed ? "var(--success)" : "var(--danger)",
    fontSize: "0.9rem",
  });

  const progressBarStyle = {
    width: "100%",
    height: "8px",
    backgroundColor: "var(--gray-200)",
    borderRadius: "4px",
    overflow: "hidden",
    marginTop: "0.5rem",
  };

  const progressFillStyle = (count, limit) => {
    const percentage = Math.min((count / limit) * 100, 100);
    const color = percentage > 80 ? "var(--danger)" : percentage > 50 ? "var(--warning)" : "var(--success)";
    return {
      height: "100%",
      width: `${percentage}%`,
      backgroundColor: color,
      transition: "width 0.3s ease",
    };
  };

  const policyListStyle = {
    marginTop: "1.25rem",
    padding: "1rem",
    backgroundColor: "var(--gray-50)",
    borderRadius: "0.5rem",
  };

  const policyItemStyle = {
    fontSize: "0.9rem",
    color: "var(--gray-700)",
    marginBottom: "0.75rem",
    paddingBottom: "0.75rem",
    borderBottom: "1px solid var(--gray-200)",
  };

  const policyItemLastStyle = {
    fontSize: "0.9rem",
    color: "var(--gray-700)",
    marginBottom: 0,
    paddingBottom: 0,
    borderBottom: "none",
  };

  const errorStyle = {
    marginTop: "1rem",
    padding: "1rem",
    backgroundColor: "rgba(239, 68, 68, 0.1)",
    color: "var(--danger)",
    borderRadius: "0.5rem",
    fontSize: "0.9rem",
    borderLeft: "4px solid var(--danger)",
  };

  return (
    <div style={containerStyle}>
      <div style={mainCardStyle}>
        {/* Header */}
        <div style={headerStyle}>
          <h1 style={titleStyle}>🚀 Rate Limiter</h1>
          <p style={subtitleStyle}>Check request limits across policies</p>
        </div>

        {/* Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleCheck();
          }}
        >
          <div style={formGroupStyle}>
            <label style={labelStyle}>Tenant ID</label>
            <input
              type="text"
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
              style={inputStyle}
              onFocus={(e) => (e.target.style.cssText += "; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);)")}
              onBlur={(e) => (e.target.style.boxShadow = "none")}
              placeholder="e.g., enterprise_co"
            />
          </div>

          <div style={formGroupStyle}>
            <label style={labelStyle}>User ID</label>
            <input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              style={inputStyle}
              onFocus={(e) => (e.target.style.cssText += "; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);)")}
              onBlur={(e) => (e.target.style.boxShadow = "none")}
              placeholder="e.g., ent-user-1"
            />
          </div>

          <div style={formGroupStyle}>
            <label style={labelStyle}>Model ID</label>
            <input
              type="text"
              value={modelId}
              onChange={(e) => setModelId(e.target.value)}
              style={inputStyle}
              onFocus={(e) => (e.target.style.cssText += "; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);)")}
              onBlur={(e) => (e.target.style.boxShadow = "none")}
              placeholder="e.g., gpt-4o"
            />
          </div>

          <div style={formGroupStyle}>
            <label style={labelStyle}>Model Tier</label>
            <select
              value={modelTier}
              onChange={(e) => setModelTier(e.target.value)}
              style={{
                ...inputStyle,
                appearance: "none",
                paddingRight: "2.5rem",
                backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236b7280' d='M6 9L1 4h10z'/%3E%3C/svg%3E\")",
                backgroundRepeat: "no-repeat",
                backgroundPosition: "right 0.75rem center",
                backgroundColor: "white",
              }}
              onFocus={(e) => (e.target.style.cssText += "; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);)")}
              onBlur={(e) => (e.target.style.boxShadow = "none")}
            >
              <option value="premium">Premium</option>
              <option value="standard">Standard</option>
              <option value="free">Free</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              ...buttonStyle,
              backgroundColor: loading ? "var(--gray-400)" : "var(--primary)",
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.7 : 1,
            }}
            onMouseEnter={(e) => {
              if (!loading) e.target.style.backgroundColor = "var(--primary-dark)";
            }}
            onMouseLeave={(e) => {
              if (!loading) e.target.style.backgroundColor = "var(--primary)";
            }}
          >
            {loading ? "Checking..." : "Check Rate Limit"}
          </button>
        </form>

        {/* Error */}
        {error && <div style={errorStyle}>⚠️ {error}</div>}

        {/* Result */}
        {result && (
          <div style={resultCardStyle}>
            <div style={statusBadgeStyle(result.allowed)}>
              {result.allowed ? "✅ Request Allowed" : "🚫 Request Blocked"}
            </div>

            <div style={{ marginBottom: "1.25rem" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: "0.5rem",
                }}
              >
                <span style={{ fontSize: "0.9rem", color: "var(--gray-700)" }}>
                  Primary Limit Usage
                </span>
                <span
                  style={{
                    fontWeight: "600",
                    color: "var(--gray-900)",
                  }}
                >
                  {result.count} / {result.limit}
                </span>
              </div>
              <div style={progressBarStyle}>
                <div style={progressFillStyle(result.count, result.limit)} />
              </div>
              <p
                style={{
                  fontSize: "0.8rem",
                  color: "var(--gray-500)",
                  marginTop: "0.5rem",
                }}
              >
                {Math.round(
                  (result.windowSeconds / 60) % 60 === 0
                    ? result.windowSeconds / 3600
                    : result.windowSeconds / 60
                )}{" "}
                {result.windowSeconds >= 3600 ? "hours" : "minutes"} window
              </p>
            </div>

            {/* Rejection Cause */}
            {result.cause && !result.allowed && (
              <div
                style={{
                  padding: "0.75rem",
                  backgroundColor: "rgba(239, 68, 68, 0.05)",
                  border: "1px solid rgba(239, 68, 68, 0.3)",
                  borderRadius: "0.5rem",
                  marginBottom: "1rem",
                  fontSize: "0.9rem",
                  color: "var(--danger)",
                  lineHeight: "1.5",
                }}
              >
                <strong>Reason:</strong> {result.cause}
              </div>
            )}

            {/* Fulfilled Policies */}
            {result.allowed &&
              result.fulfilled &&
              result.fulfilled.length > 0 && (
                <div style={policyListStyle}>
                  <p
                    style={{
                      fontSize: "0.9rem",
                      fontWeight: "600",
                      color: "var(--gray-800)",
                      marginBottom: "0.75rem",
                    }}
                  >
                    ✅ Satisfied Policies
                  </p>
                  {result.fulfilled.map((f, idx) => (
                    <div
                      key={idx}
                      style={
                        idx === result.fulfilled.length - 1
                          ? policyItemLastStyle
                          : policyItemStyle
                      }
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          marginBottom: "0.35rem",
                        }}
                      >
                        <span style={{ fontWeight: "600", color: "var(--gray-900)" }}>
                          {f.label}
                        </span>
                        <span style={{ color: "var(--success)", fontWeight: "500" }}>
                          {f.count}/{f.limit}
                        </span>
                      </div>
                      <p
                        style={{
                          fontSize: "0.8rem",
                          color: "var(--gray-500)",
                          margin: 0,
                        }}
                      >
                        {Math.round(
                          (f.windowSeconds / 60) % 60 === 0
                            ? f.windowSeconds / 3600
                            : f.windowSeconds / 60
                        )}{" "}
                        {f.windowSeconds >= 3600 ? "hours" : "minutes"} window
                      </p>
                    </div>
                  ))}
                </div>
              )}

            <p
              style={{
                marginTop: "1rem",
                fontSize: "0.85rem",
                color: "var(--gray-500)",
                textAlign: "center",
              }}
            >
              💡 Click multiple times to test rate limiting behavior
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
