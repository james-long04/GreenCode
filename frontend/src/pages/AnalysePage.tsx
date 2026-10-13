import { useMemo, useState, type KeyboardEvent } from "react";

import { api } from "../api";
import { CodeBlock } from "../components/code";
import { Icon } from "../components/icons";
import { Alert, Badge, ConditionLabel, Empty, ErrorBox, LoadingBlock, PageHeader, Section, Spinner, TableWrap, RowLink, fmt } from "../components/ui";
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

function specProblem(text: string): string | null {
  try {
    const v = JSON.parse(text) as Record<string, unknown>;
    if (typeof v !== "object" || v === null || Array.isArray(v)) return "The specification must be a JSON object.";
    if (typeof v.entry_point !== "string") return 'Missing "entry_point": the name of the function to call, for example "solve".';
    if (!Array.isArray(v.tests) || v.tests.length === 0) return 'Add at least one test under "tests" so correctness can be checked.';
    const b = v.benchmark as Record<string, unknown> | undefined;
    if (!b || typeof b.call !== "string") return 'Missing "benchmark.call": the expression to time, for example "solve(records, allowed)".';
    return null;
  } catch (e) {
    return `This is not valid JSON: ${e instanceof Error ? e.message : String(e)}`;
  }
}

/** Submit code for static analysis, then launch optimisations under either condition. */
export function AnalysePage({ projectId, navigate }: { projectId: string | null; navigate: (p: string) => void }) {
  const [language, setLanguage] = useState<Language>("python");
  const [name, setName] = useState("ad-hoc analysis");
  const [source, setSource] = useState(PY_EXAMPLE);
  const [spec, setSpec] = useState(JSON.stringify(PY_SPEC, null, 2));
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const problem = useMemo(() => (language === "python" ? specProblem(spec) : null), [language, spec]);
  const canSubmit = !!projectId && !!source.trim() && !problem && !busy;

  const switchLanguage = (l: Language) => {
    setLanguage(l);
    setSource(l === "python" ? PY_EXAMPLE : SQL_EXAMPLE);
  };

  const submit = async () => {
    if (!canSubmit) return;
    setBusy(true);
    setErr(null);
    try {
      const case_spec = language === "python" ? (JSON.parse(spec) as Record<string, unknown>) : {};
      const a = await api.createAnalysis({ project_id: projectId!, name, language, source, case_spec });
      navigate(`/analyses/${a.id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const onKey = (e: KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      void submit();
    }
  };

  return (
    <div className="stack">
      <PageHeader
        title="Analyse"
        lede="Paste Python or SQL. Deterministic static-analysis rules find and explain inefficiencies before any AI is involved."
      />
      {!projectId && (
        <Alert
          kind="warn"
          title="Choose a project first"
          action={
            <button className="small" onClick={() => navigate("/projects")}>
              Go to projects
            </button>
          }
        >
          Analyses are saved inside a project so results stay grouped.
        </Alert>
      )}
      <ErrorBox error={err} />

      <div className="panel">
        <div className="stack-sm">
          <div className="row spread">
            <div className="row" style={{ alignItems: "end", gap: 16 }}>
              <div className="field" style={{ display: "grid", gap: 5 }}>
                <span id="lang-label" style={{ fontSize: "var(--text-sm)", fontWeight: 500, color: "var(--text-2)" }}>
                  Language
                </span>
                <div className="segmented" role="group" aria-labelledby="lang-label">
                  <button aria-pressed={language === "python"} onClick={() => switchLanguage("python")}>
                    Python
                  </button>
                  <button aria-pressed={language === "sql"} onClick={() => switchLanguage("sql")}>
                    SQL
                  </button>
                </div>
              </div>
              <label className="field">
                Name
                <input type="text" value={name} onChange={(e) => setName(e.target.value)} style={{ minWidth: 240 }} />
              </label>
            </div>
            <div className="row">
              <span className="muted small">
                <span className="kbd">Ctrl</span> + <span className="kbd">Enter</span> to run
              </span>
              <button className="primary" onClick={() => void submit()} disabled={!canSubmit}>
                {busy ? <Spinner /> : <Icon name="play" size={16} />}
                {busy ? "Analysing…" : "Run static analysis"}
              </button>
            </div>
          </div>

          <label className="field">
            {language === "python" ? "Python module" : "SQL query"}
            <span className="help">
              {language === "python"
                ? "Define the entry-point function named in the specification below (the example uses solve)."
                : "Runs against the controlled bench schema (customers, products, orders, order_items)."}
            </span>
            <textarea
              value={source}
              onChange={(e) => setSource(e.target.value)}
              onKeyDown={onKey}
              spellCheck={false}
              aria-label={language === "python" ? "Python source" : "SQL source"}
            />
          </label>

          {language === "python" && (
            <details className="disclosure">
              <summary>
                Tests and benchmark workload {problem ? <Badge kind="bad">needs attention</Badge> : <Badge kind="ok">valid</Badge>}
              </summary>
              <div className="disclosure-body stack-sm">
                <p className="muted small" style={{ maxWidth: "68ch" }}>
                  Tests decide whether an optimised version is correct (its output must match the original on every test). The benchmark setup builds the
                  workload and the call is what gets timed. The default matches the example above.
                </p>
                <label className="field">
                  <span className="sr-only">Case specification (JSON)</span>
                  <textarea
                    className={problem ? "invalid" : ""}
                    value={spec}
                    onChange={(e) => setSpec(e.target.value)}
                    onKeyDown={onKey}
                    spellCheck={false}
                    aria-invalid={!!problem}
                    aria-describedby={problem ? "spec-problem" : undefined}
                    aria-label="Case specification in JSON"
                  />
                </label>
                {problem && (
                  <div id="spec-problem" className="alert error" role="alert">
                    <Icon name="x-circle" className="alert-icon" />
                    <div className="alert-body">{problem}</div>
                  </div>
                )}
              </div>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}

function flaggedLines(findings: Finding[]): Set<number> {
  const marks = new Set<number>();
  for (const f of findings) {
    if (f.line == null) continue;
    const end = f.end_line ?? f.line;
    for (let l = f.line; l <= Math.min(end, f.line + 40); l++) marks.add(l);
  }
  return marks;
}

export function AnalysisDetailPage({ id, navigate }: { id: string; navigate: (p: string) => void }) {
  const analysis = useAsync<Analysis>(() => api.analysis(id), [id]);
  const opts = useAsync<OptimisationSummary[]>(() => api.analysisOptimisations(id), [id], 3000);
  const [err, setErr] = useState<string | null>(null);
  const [launching, setLaunching] = useState<Condition | null>(null);
  const a = analysis.data;
  const marks = useMemo(() => flaggedLines(a?.findings ?? []), [a]);

  const launch = async (condition: Condition) => {
    setLaunching(condition);
    setErr(null);
    try {
      const o = await api.createOptimisation(id, condition);
      await opts.reload();
      navigate(`/optimisations/${o.id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLaunching(null);
    }
  };

  if (analysis.error) return <ErrorBox error={analysis.error} onRetry={() => void analysis.reload()} />;
  if (!a) return <LoadingBlock label="Loading analysis" rows={5} />;
  const n = a.findings.length;
  return (
    <div className="stack">
      <PageHeader
        title={a.name}
        meta={
          <>
            <Badge>{a.language}</Badge>
            {a.case_id && <span className="mono">{a.case_id}</span>}
            <span>analysed in {fmt.ms(a.duration_ms)}</span>
            <span>analyser v{a.analyser_version}</span>
          </>
        }
      />
      <ErrorBox error={err} />

      <div className="panel">
        <div className="stack-sm">
          <h2>Optimise with a local model</h2>
          <p className="muted" style={{ maxWidth: "70ch" }}>
            Run it both ways and compare. The two prompts are identical except that GreenCode also receives the {n} finding{n === 1 ? "" : "s"} below.
          </p>
          <div className="row">
            <button onClick={() => void launch("ai_only")} disabled={launching !== null}>
              {launching === "ai_only" && <Spinner />}
              AI-only
              <span className="muted small">sees the code only</span>
            </button>
            <button className="primary" onClick={() => void launch("greencode")} disabled={launching !== null}>
              {launching === "greencode" && <Spinner />}
              GreenCode
              <span className="small" style={{ opacity: 0.85 }}>
                code + static-analysis findings
              </span>
            </button>
          </div>
        </div>
      </div>

      <div className="grid two">
        <Section id="source" title="Source" hint={marks.size ? `${marks.size} line${marks.size === 1 ? "" : "s"} flagged` : undefined}>
          <CodeBlock source={a.source} marks={marks} label="Source code" />
          {typeof a.case_spec.analysis_error === "string" && (
            <div style={{ marginTop: 10 }}>
              <Alert kind="error" title="Analysis problem">
                {a.case_spec.analysis_error}
              </Alert>
            </div>
          )}
        </Section>
        <Section id="findings" title={`Findings (${n})`}>
          {n ? (
            <div className="divided">
              {a.findings.map((f) => (
                <FindingCard key={f.id} f={f} />
              ))}
            </div>
          ) : (
            <Empty title="No known inefficiency pattern detected">
              The rule set did not match this code. You can still optimise it, but GreenCode will have no findings to add over AI-only.
            </Empty>
          )}
        </Section>
      </div>

      <Section id="runs" title="Optimisations">
        {opts.data?.length ? (
          <div className="panel flush">
            <TableWrap label="Optimisations for this analysis">
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
                    <tr key={o.id} className="linked">
                      <RowLink href={`#/optimisations/${o.id}`}>
                        <ConditionLabel condition={o.condition} />
                      </RowLink>
                      <td>
                        <Badge kind={o.status}>{o.status}</Badge>
                      </td>
                      <td className="mono small">{o.model_name}</td>
                      <td className="num">{fmt.x(o.summary.timing?.speedup)}</td>
                      <td>{o.summary.timing && <Badge kind={o.summary.timing.verdict}>{fmt.label(o.summary.timing.verdict)}</Badge>}</td>
                      <td className="muted small">{o.failure_reason}</td>
                      <td className="muted small nowrap">{fmt.date(o.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          </div>
        ) : (
          <Empty title="No optimisations yet">Run one under each condition above to compare them.</Empty>
        )}
      </Section>
    </div>
  );
}

export function FindingCard({ f }: { f: Finding }) {
  return (
    <div className="finding">
      <div className="finding-head">
        <span className="finding-title">
          <span className="mono">{f.rule_id}</span> · {f.title}
          {f.line != null && <span className="muted"> · line {f.line}</span>}
        </span>
        <span className="row" style={{ gap: 6 }}>
          <Badge kind={f.severity}>{f.severity} severity</Badge>
          <Badge title="How sure the rule is that this is a true positive">{(f.confidence * 100).toFixed(0)}% confidence</Badge>
        </span>
      </div>
      <dl>
        <dt>Why</dt>
        <dd>{f.explanation}</dd>
        <dt>Fix</dt>
        <dd>{f.suggestion}</dd>
      </dl>
      {f.snippet && <pre className="plain mono">{f.snippet}</pre>}
    </div>
  );
}
