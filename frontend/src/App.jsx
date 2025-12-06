import { useState } from "react";

function App() {
  const [userId, setUserId] = useState("user-1");
  const [modelId, setModelId] = useState("gpt-4");
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

  const statusColor =
    result && result.allowed ? "green" : result ? "red" : "gray";

  return (
    <div
      style={{
        fontFamily: "system-ui, sans-serif",
        padding: "2rem",
        maxWidth: 600,
        margin: "0 auto",
      }}
    >
      <h1>AI Rate Limiter Demo</h1>

      <div style={{ marginBottom: "1rem" }}>
        <label>
          User ID:{" "}
          <input
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            style={{ marginLeft: "0.5rem" }}
          />
        </label>
      </div>

      <div style={{ marginBottom: "1rem" }}>
        <label>
          Model ID:{" "}
          <input
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
            style={{ marginLeft: "0.5rem" }}
          />
        </label>
      </div>

      <div style={{ marginBottom: "1rem" }}>
        <label>
          Model Tier:{" "}
          <select
            value={modelTier}
            onChange={(e) => setModelTier(e.target.value)}
            style={{ marginLeft: "0.5rem" }}
          >
            <option value="premium">premium</option>
            <option value="standard">standard</option>
            <option value="free">free</option>
          </select>
        </label>
      </div>

      <button
        onClick={handleCheck}
        disabled={loading}
        style={{
          padding: "0.5rem 1rem",
          fontWeight: "bold",
          cursor: "pointer",
        }}
      >
        {loading ? "Checking..." : "Send Request"}
      </button>

      {error && (
        <div style={{ marginTop: "1rem", color: "red" }}>
          Error: {error}
        </div>
      )}

      {result && (
        <div
          style={{
            marginTop: "1.5rem",
            padding: "1rem",
            border: "1px solid #ddd",
            borderRadius: "8px",
          }}
        >
          <h2 style={{ color: statusColor }}>
            {result.allowed ? "ALLOWED ✅" : "BLOCKED 🚫"}
          </h2>

          <p>
            <strong>Count:</strong> {result.count} / {result.limit} in the last{" "}
            {result.windowSeconds / 60} minutes
          </p>

          {/* Rejection cause (if blocked) */}
          {result.cause && !result.allowed && (
            <p style={{ color: "red", marginTop: "0.5rem" }}>
              <strong>Cause:</strong> {result.cause}
            </p>
          )}

          {/* Fulfilled policies (if allowed) */}
          {result.allowed &&
            result.fulfilled &&
            result.fulfilled.length > 0 && (
              <div style={{ marginTop: "0.75rem" }}>
                <strong>Fulfilled policies:</strong>
                <ul style={{ marginTop: "0.5rem" }}>
                  {result.fulfilled.map((f, idx) => (
                    <li key={idx} style={{ marginBottom: "0.35rem" }}>
                      <span style={{ fontWeight: 600 }}>{f.label}</span>
                      {" — "}
                      {f.count}/{f.limit} in last {f.windowSeconds / 60} min
                      {" "}
                      <span style={{ color: "#666", fontSize: "0.9em" }}>
                        (key: {f.key})
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

          <p>Try clicking multiple times quickly to see the limiter kick in.</p>
        </div>
      )}
    </div>
  );
}

export default App;
