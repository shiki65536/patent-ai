import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";
const API_KEY = import.meta.env.VITE_API_KEY || "";

function App() {
  const [text, setText] = useState("本発明は、半導体装置およびその製造方法に関する。");
  const [domain, setDomain] = useState("semiconductor");
  const [sectionType, setSectionType] = useState("general");
  const [provider, setProvider] = useState("gemini");
  const [useRag, setUseRag] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");

  async function apiFetch(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(API_KEY ? { "x-api-key": API_KEY } : {}),
        ...(options.headers || {})
      }
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }
    return data;
  }

  async function checkStatus() {
    setError("");
    try {
      const data = await apiFetch("/system/status");
      setStatus(data);
    } catch (err) {
      setError(err.message || "Status check failed");
    }
  }

  async function translate() {
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
          num_examples: 3
        })
      });
      setResult(data);
    } catch (err) {
      setError(err.message || "Translation failed");
    } finally {
      setLoading(false);
    }
  }

  const metadata = result?.metadata || {};

  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">AWS Serverless Demo</p>
        <h1>Patent AI Translation Platform</h1>
        <p className="subtitle">
          Japanese → Traditional Chinese patent translation with RAG examples,
          terminology management, model routing, latency and cost visibility.
        </p>
      </section>

      <section className="panel controls">
        <div>
          <label>Model</label>
          <select value={provider} onChange={(event) => setProvider(event.target.value)}>
            <option value="gemini">Gemini</option>
            <option value="claude">Claude</option>
          </select>
        </div>
        <div>
          <label>Domain</label>
          <select value={domain} onChange={(event) => setDomain(event.target.value)}>
            <option value="semiconductor">Semiconductor</option>
            <option value="mechanical">Mechanical</option>
            <option value="general">General</option>
            <option value="">None</option>
          </select>
        </div>
        <div>
          <label>Section</label>
          <select value={sectionType} onChange={(event) => setSectionType(event.target.value)}>
            <option value="general">General</option>
            <option value="abstract">Abstract</option>
            <option value="claims">Claims</option>
            <option value="description">Description</option>
            <option value="background">Background</option>
          </select>
        </div>
        <label className="checkbox">
          <input type="checkbox" checked={useRag} onChange={(event) => setUseRag(event.target.checked)} />
          Use RAG
        </label>
        <button className="secondary" onClick={checkStatus}>Check system</button>
      </section>

      {status && (
        <section className="status-grid">
          <Metric label="Translations" value={status.database?.total_translations ?? "N/A"} />
          <Metric label="Terms" value={status.database?.total_terminology ?? "N/A"} />
          <Metric label="Vector Index" value={status.vector_search?.indexed_embeddings ?? "N/A"} />
          <Metric label="Vector Status" value={status.vector_search?.status ?? "N/A"} />
        </section>
      )}

      <section className="grid">
        <div className="panel">
          <label>Japanese Patent Text</label>
          <textarea value={text} onChange={(event) => setText(event.target.value)} maxLength={3000} />
          <div className="footer-row">
            <span>{text.length}/3000 characters</span>
            <button onClick={translate} disabled={loading}>{loading ? "Translating..." : "Translate"}</button>
          </div>
          {error && <p className="error">{error}</p>}
        </div>

        <div className="panel">
          <h2>Translation</h2>
          {result ? (
            <p className="translation">{result.translation}</p>
          ) : (
            <p className="empty">Run a translation to see the result.</p>
          )}
        </div>
      </section>

      {result && (
        <>
          <section className="status-grid">
            <Metric label="Provider" value={metadata.provider || provider} />
            <Metric label="Latency" value={`${metadata.latency_seconds ?? "N/A"}s`} />
            <Metric label="Estimated Cost" value={`$${metadata.estimated_cost_usd ?? "0"}`} />
            <Metric label="Confidence" value={result.confidence_score?.toFixed?.(2) || "N/A"} />
          </section>

          <section className="grid">
            <div className="panel">
              <h2>Retrieved RAG Examples</h2>
              {(result.retrieved_examples || []).map((item, index) => (
                <article className="example" key={index}>
                  <div className="example-header">
                    <strong>Example {index + 1}</strong>
                    <span>{typeof item.similarity_score === "number" ? item.similarity_score.toFixed(3) : "fallback"}</span>
                  </div>
                  <p><b>JP</b>: {item.source_text}</p>
                  <p><b>ZH</b>: {item.translation}</p>
                </article>
              ))}
            </div>

            <div className="panel">
              <h2>Terminology Used</h2>
              {(result.terminology_used || []).length === 0 ? (
                <p className="empty">No terms matched.</p>
              ) : (
                (result.terminology_used || []).map((term, index) => (
                  <div className="term" key={index}>
                    <span>{term.japanese_term}</span>
                    <strong>{term.chinese_term}</strong>
                  </div>
                ))
              )}
            </div>
          </section>
        </>
      )}
    </main>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
