import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";
const API_KEY = import.meta.env.VITE_API_KEY || "";

// ── API helper ──────────────────────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(API_KEY ? { "x-api-key": API_KEY } : {}),
      ...(options.headers || {}),
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  return data;
}

// ── Sub-components ──────────────────────────────────────────────────────────

function MetricCard({ label, value, isText = false }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className={`metric-value${isText ? " is-text" : ""}`}>{value}</div>
    </div>
  );
}

function ScoreBadge({ score }) {
  const isFallback = typeof score !== "number";
  return (
    <span className={`score-badge${isFallback ? " is-fallback" : ""}`}>
      {isFallback ? "fallback" : score.toFixed(3)}
    </span>
  );
}

function ExampleCard({ item, index }) {
  return (
    <div className="example-card">
      <div className="example-header">
        <span className="example-num">Example {index + 1}</span>
        <ScoreBadge score={item.similarity_score} />
      </div>
      <div className="example-body">
        <div className="example-col">
          <div className="example-col-label jp">JP</div>
          <div className="example-text">{item.source_text}</div>
        </div>
        <div className="example-col">
          <div className="example-col-label zh">ZH</div>
          <div className="example-text">{item.translation}</div>
        </div>
      </div>
    </div>
  );
}

function TermRow({ term }) {
  return (
    <div className="term-row">
      <span className="term-jp">{term.japanese_term}</span>
      <span className="term-arrow">→</span>
      <span className="term-zh">{term.chinese_term}</span>
      {term.domain && <span className="term-domain">{term.domain}</span>}
    </div>
  );
}

function SystemStatus({ data }) {
  return (
    <div className="system-status">
      <div className="system-status-grid">
        <div className="system-metric">
          <div className="metric-label">Translations</div>
          <div className="metric-value is-text">{data.database?.total_translations ?? "N/A"}</div>
        </div>
        <div className="system-metric">
          <div className="metric-label">Terms</div>
          <div className="metric-value is-text">{data.database?.total_terminology ?? "N/A"}</div>
        </div>
        <div className="system-metric">
          <div className="metric-label">Vector index</div>
          <div className="metric-value is-text">{data.vector_search?.indexed_embeddings ?? "N/A"}</div>
        </div>
        <div className="system-metric">
          <div className="metric-label">Vector status</div>
          <div className="metric-value is-text">{data.vector_search?.status ?? "N/A"}</div>
        </div>
      </div>
    </div>
  );
}

// ── Main App ────────────────────────────────────────────────────────────────
function App() {
  const [text, setText] = useState("本発明は、半導体装置およびその製造方法に関する。");
  const [domain, setDomain] = useState("semiconductor");
  const [sectionType, setSectionType] = useState("general");
  const [provider, setProvider] = useState("gemini");
  const [useRag, setUseRag] = useState(true);

  const [loading, setLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");

  async function checkStatus() {
    setStatusLoading(true);
    setError("");
    try {
      const data = await apiFetch("/system/status");
      setStatus(data);
    } catch (err) {
      setError(err.message || "Status check failed");
    } finally {
      setStatusLoading(false);
    }
  }

  async function translate() {
    if (!text.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await apiFetch("/translate", {
        method: "POST",
        body: JSON.stringify({
          japanese_text: text,
          domain: domain || null,
          section_type: sectionType,
          provider,
          use_rag: useRag,
          num_examples: 3,
        }),
      });
      setResult(data);
    } catch (err) {
      setError(err.message || "Translation failed");
    } finally {
      setLoading(false);
    }
  }

  function copyTranslation() {
    if (result?.translation) navigator.clipboard.writeText(result.translation);
  }

  const metadata = result?.metadata || {};
  const examples = result?.retrieved_examples || [];
  const terms = result?.terminology_used || [];

  return (
    <main className="page">

      {/* Topbar */}
      <header className="topbar">
        <div className="topbar-left">
          <div className="aws-badge">AWS Serverless</div>
          <span className="topbar-title">Patent AI</span>
          <div className="topbar-divider" />
          <span className="topbar-sub">JP → ZH Translation</span>
        </div>
        <button
          className="status-pill"
          onClick={checkStatus}
          disabled={statusLoading}
        >
          <span className={`status-dot${statusLoading ? " checking" : ""}`} />
          {statusLoading ? "Checking..." : "System status"}
        </button>
      </header>

      {/* System status (conditional) */}
      {status && <SystemStatus data={status} />}

      {/* Error bar */}
      {error && <div className="error-bar">{error}</div>}

      {/* Controls */}
      <div className="controls">
        <div className="field">
          <span className="field-label">Model</span>
          <select value={provider} onChange={(e) => setProvider(e.target.value)}>
            <option value="gemini">Gemini</option>
            <option value="claude">Claude</option>
          </select>
        </div>
        <div className="field">
          <span className="field-label">Domain</span>
          <select value={domain} onChange={(e) => setDomain(e.target.value)}>
            <option value="semiconductor">Semiconductor</option>
            <option value="mechanical">Mechanical</option>
            <option value="general">General</option>
            <option value="">None</option>
          </select>
        </div>
        <div className="field">
          <span className="field-label">Section</span>
          <select value={sectionType} onChange={(e) => setSectionType(e.target.value)}>
            <option value="general">General</option>
            <option value="abstract">Abstract</option>
            <option value="claims">Claims</option>
            <option value="description">Description</option>
            <option value="background">Background</option>
          </select>
        </div>
        <div className="rag-toggle">
          <label className="rag-label">
            <input
              type="checkbox"
              checked={useRag}
              onChange={(e) => setUseRag(e.target.checked)}
            />
            RAG enabled
          </label>
        </div>
      </div>

      {/* Workspace */}
      <div className="workspace">
        {/* Input panel */}
        <div className="panel">
          <div className="panel-header">
            <div className="lang-tag">
              <div className="lang-bar lang-bar-jp" />
              Japanese
            </div>
            <span className="panel-meta">{text.length} / 3000</span>
          </div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            maxLength={3000}
            placeholder="Paste Japanese patent text here..."
          />
          <div className="panel-footer">
            <button className="btn btn-primary" onClick={translate} disabled={loading || !text.trim()}>
              {loading ? "Translating..." : "Translate →"}
            </button>
          </div>
        </div>

        {/* Output panel */}
        <div className="panel">
          <div className="panel-header">
            <div className="lang-tag">
              <div className="lang-bar lang-bar-zh" />
              Traditional Chinese
            </div>
            {result && (
              <span className="panel-meta">
                confidence: {result.confidence_score?.toFixed(2) ?? "N/A"}
              </span>
            )}
          </div>
          <div className="translation-output">
            {result ? (
              result.translation
            ) : (
              <span className="translation-placeholder">
                Run a translation to see the result.
              </span>
            )}
          </div>
          {result && (
            <div className="panel-footer">
              <button className="btn" onClick={copyTranslation}>Copy</button>
            </div>
          )}
        </div>
      </div>

      {/* Post-translation metrics + details */}
      {result && (
        <>
          <div className="metrics-strip">
            <MetricCard label="Provider" value={metadata.provider || provider} isText />
            <MetricCard label="Latency" value={`${metadata.latency_seconds ?? "N/A"}s`} />
            <MetricCard label="Est. cost" value={`$${metadata.estimated_cost_usd ?? "0"}`} />
            <MetricCard label="Terms matched" value={terms.length} />
          </div>

          <div className="bottom-grid">
            {/* RAG Examples */}
            <div className="panel">
              <div className="section-header">
                <span className="section-title">Retrieved examples</span>
                <span className="section-count">{examples.length} results</span>
              </div>
              <div className="examples-list">
                {examples.length > 0 ? (
                  examples.map((item, i) => <ExampleCard key={i} item={item} index={i} />)
                ) : (
                  <p className="empty-state">No RAG examples returned.</p>
                )}
              </div>
            </div>

            {/* Terminology */}
            <div className="panel">
              <div className="section-header">
                <span className="section-title">Terminology</span>
                <span className="section-count">{terms.length} matched</span>
              </div>
              <div className="terms-list">
                {terms.length > 0 ? (
                  terms.map((term, i) => <TermRow key={i} term={term} />)
                ) : (
                  <p className="empty-state">No terms matched.</p>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
