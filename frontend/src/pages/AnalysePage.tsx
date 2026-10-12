import { useState } from "react";

import { api } from "../api";
import { Badge, ConditionLabel, Empty, ErrorBox, fmt } from "../components/ui";
import { useAsync } from "../hooks";
import type { Analysis, Condition, Finding, Language, OptimisationSummary } from "../types";

const PY_EXAMPLE = `def solve(records, allowed_ids):
    allowed = [r["id"] for r in allowed_ids]
    out = []
    for r in records:
        if r["id"] in allowed:
            out.append(r)
    return out
`;

const SQL_EXAMPLE = `SELECT * FROM orders
WHERE EXTRACT(YEAR FROM created_at) = 2023 AND status = 'paid'`;

const PY_SPEC = {
  entry_point: "solve",
  tests: [
    { name: "basic", args: "([{'id': 1}, {'id': 2}], [{'id': 2}])", expected: [{ id: 2 }] },
    { name: "empty", args: "([], [])", expected: [] },
  ],
  benchmark: {
    setup: "records = [{'id': i} for i in range(6000)]\nallowed = [{'id': i} for i in range(0, 6000, 2)]",
    call: "solve(records, allowed)",
  },
};

/** Submit code for static analysis, then launch optimisations under either condition. */
export function AnalysePage({ projectId, navigate }: { projectId: string | null; navigate: (p: string) => void }) {
  const [language, setLanguage] = useState<Language>("python");
  const [name, setName] = useState("ad-hoc analysis");
  const [source, setSource] = useState(PY_EXAMPLE);
  const [spec, setSpec] = useState(JSON.stringify(PY_SPEC, null, 2));
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const switchLanguage = (l: Language) => {
    setLanguage(l);
    setSource(l === "python" ? PY_EXAMPLE : SQL_EXAMPLE);
  };

  const submit = async () => {
    if (!projectId) {
      setErr("Select or create a project first.");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      let case_spec: Record<string, unknown> = {};
      if (language === "python") case_spec = JSON.parse(spec) as Record<string, unknown>;
      const a = await api.createAnalysis({ project_id: projectId, name, language, source, case_spec });
      navigate(`/analyses/${a.id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h1>Analyse</h1>
      <div className="subtitle">Detect and explain inefficiencies with deterministic static-analysis rules before any AI is involved.</div>
      <ErrorBox error={err} />
      <div className="card">
        <div className="row spread" style={{ marginBottom: 12 }}>
          <div className="row">
            <label className="field">
              Language
              <select value={language} onChange={(e) => switchLanguage(e.target.value as Language)}>
                <option value="python">Python</option>
                <option value="sql">SQL (PostgreSQL)</option>
              </select>
            </label>
            <label className="field">
              Name
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </label>
          </div>
          <button className="primary" onClick={() => void submit()} disabled={busy || !source.trim()}>
            {busy ? "Analysing…" : "Run static analysis"}
          </button>
        </div>
        <div className={language === "python" ? "grid two" : ""}>
          <label className="field">
            {language === "python" ? "Python module (must define the entry point, e.g. solve)" : "SQL query (runs against the bench schema)"}
            <textarea value={source} onChange={(e) => setSource(e.target.value)} spellCheck={false} />
          </label>
          {language === "python" && (
            <label className="field">
              Case specification — tests (differential + expected) and benchmark workload
              <textarea value={spec} onChange={(e) => setSpec(e.target.value)} spellCheck={false} />
            </label>
          )}
        </div>
      </div>
    </div>
  );
}

export function AnalysisDetailPage({ id, navigate }: { id: string; navigate: (p: string) => void }) {
  const analysis = useAsync<Analysis>(() => api.analysis(id), [id]);
  const opts = useAsync<OptimisationSummary[]>(() => api.analysisOptimisations(id), [id], 3000);
  const [err, setErr] = useState<string | null>(null);
  const a = analysis.data;

  const launch = async (condition: Condition) => {
    try {
      const o = await api.createOptimisation(id, condition);
      await opts.reload();
      navigate(`/optimisations/${o.id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  };

  if (analysis.error) return <ErrorBox error={analysis.error} />;
  if (!a) return <Empty>Loading…</Empty>;
  return (
    <div>
      <div className="row spread">
        <div>
          <h1>{a.name}</h1>
          <div className="subtitle">
            <Badge>{a.language}</Badge> {a.case_id && <span className="mono">{a.case_id}</span>} · analysed in {fmt.ms(a.duration_ms)} · analyser v{a.analyser_version}
          </div>
        </div>
        <div className="row">
          <button onClick={() => void launch("ai_only")}>Optimise: AI-only</button>
          <button className="primary" onClick={() => void launch("greencode")}>
            Optimise: GreenCode (guided)
          </button>
        </div>
      </div>
      <ErrorBox error={err} />
      <div className="grid two">
        <div className="card">
          <h3>Source</h3>
          <pre>{a.source}</pre>
          {typeof a.case_spec.analysis_error === "string" && <div className="error">{a.case_spec.analysis_error}</div>}
        </div>
        <div className="card">
          <h3>Findings ({a.findings.length})</h3>
          {a.findings.length ? a.findings.map((f) => <FindingCard key={f.id} f={f} />) : <Empty>No known inefficiency pattern detected.</Empty>}
        </div>
      </div>
      <div className="card">
        <h3>Optimisations</h3>
        {opts.data?.length ? (
          <table>
            <thead>
              <tr>
                <th>Condition</th>
                <th>Status</th>
                <th>Model</th>
                <th className="num">Speed-up</th>
                <th>Verdict</th>
                <th>Failure</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {opts.data.map((o) => (
                <tr key={o.id} className="clickable" onClick={() => navigate(`/optimisations/${o.id}`)}>
                  <td>
                    <ConditionLabel condition={o.condition} />
                  </td>
                  <td>
                    <Badge kind={o.status}>{o.status}</Badge>
                  </td>
                  <td className="mono small">{o.model_name}</td>
                  <td className="num">{fmt.x(o.summary.timing?.speedup)}</td>
                  <td>{o.summary.timing && <Badge kind={o.summary.timing.verdict}>{o.summary.timing.verdict.replace(/_/g, " ")}</Badge>}</td>
                  <td className="muted small">{o.failure_reason}</td>
                  <td className="muted small">{fmt.date(o.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <Empty>No optimisations yet. Launch one under each condition to compare.</Empty>
        )}
      </div>
    </div>
  );
}

export function FindingCard({ f }: { f: Finding }) {
  return (
    <div className={`finding ${f.severity}`}>
      <div className="row spread">
        <span className="title">
          <span className="mono">{f.rule_id}</span> · {f.title}
          {f.line != null && <span className="muted"> · line {f.line}</span>}
        </span>
        <span className="row">
          <Badge kind={f.severity}>{f.severity}</Badge>
          <Badge>{f.category.replace(/_/g, " ")}</Badge>
          <Badge>confidence {(f.confidence * 100).toFixed(0)}%</Badge>
        </span>
      </div>
      <p>
        <b>Why:</b> {f.explanation}
      </p>
      <p>
        <b>Suggestion:</b> {f.suggestion}
      </p>
      {f.snippet && <pre className="light">{f.snippet}</pre>}
    </div>
  );
}
