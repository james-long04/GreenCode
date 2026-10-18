import { useEffect, useMemo, useState } from "react";

import { api } from "../api";
import { ConditionBars, Legend } from "../components/charts";
import { Icon } from "../components/icons";
import { Alert, Badge, ConditionLabel, Empty, ErrorBox, PageHeader, Section, Spinner, TableWrap, Term, fmt } from "../components/ui";
import { useAsync, useDocumentTitle } from "../hooks";
import type { Condition, Language, ResultRow, ResultsSummary, SuiteCase, SuiteJob } from "../types";
import { HypothesisList } from "./OverviewPage";

export function ExperimentsPage({ projectId }: { projectId: string | null; navigate?: (p: string) => void }) {
  useDocumentTitle("Experiments");
  const cases = useAsync<SuiteCase[]>(() => api.suiteCases(), []);
  const jobs = useAsync<SuiteJob[]>(() => api.suiteJobs(), [], 2000);
  const [language, setLanguage] = useState<Language | "">("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [conditions, setConditions] = useState<Condition[]>(["ai_only", "greencode"]);
  const [err, setErr] = useState<string | null>(null);
  const results = useAsync<ResultRow[]>(() => api.results(projectId ?? undefined, language || undefined), [projectId, language], 5000);
  const summary = useAsync<ResultsSummary>(() => api.resultsSummary(projectId ?? undefined, language || undefined), [projectId, language], 5000);

  const visible = useMemo(() => (cases.data ?? []).filter((c) => !language || c.language === language), [cases.data, language]);
  useEffect(() => {
    if (cases.data && selected.size === 0) setSelected(new Set(cases.data.map((c) => c.id)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cases.data]);

  const running = jobs.data?.find((j) => j.status === "running");
  const chosen = visible.filter((c) => selected.has(c.id));

  const run = async () => {
    if (!projectId) return;
    setErr(null);
    try {
      await api.runSuite({ project_id: projectId, case_ids: chosen.map((c) => c.id), conditions });
      await jobs.reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  };

  const toggleCond = (c: Condition) => setConditions((cs) => (cs.includes(c) ? cs.filter((x) => x !== c) : [...cs, c]));

  const s = summary.data;
  const ai = s?.conditions.ai_only;
  const gc = s?.conditions.greencode;
  const failures = (f?: Record<string, number>) => Object.entries(f ?? {}).map(([k, v]) => `${fmt.label(k)} ×${v}`).join(", ") || "none";

  const rows: [string, number | null | undefined, number | null | undefined, (v: number) => string][] = [
    ["Runs", ai?.runs, gc?.runs, String],
    ["Correct (verified)", ai?.correct, gc?.correct, String],
    ["Correctness rate", ai?.correctness_rate, gc?.correctness_rate, fmt.rate],
    ["Unchanged candidates", ai?.unchanged, gc?.unchanged, String],
    ["Significantly faster", ai?.faster_significant, gc?.faster_significant, String],
    ["Significantly slower", ai?.slower_significant, gc?.slower_significant, String],
    ["Median speed-up", ai?.median_speedup, gc?.median_speedup, fmt.x],
    ["Geomean speed-up", ai?.geomean_speedup, gc?.geomean_speedup, fmt.x],
    ["Median time change", ai?.median_time_change_pct, gc?.median_time_change_pct, fmt.pct],
    ["Geomean energy ratio", ai?.geomean_energy_ratio, gc?.geomean_energy_ratio, fmt.x],
    ["Median energy change", ai?.median_energy_change_pct, gc?.median_energy_change_pct, fmt.pct],
  ];

  return (
    <div className="stack">
      <PageHeader
        title="Experiments"
        lede="Run the controlled benchmark suite under the AI-only and GreenCode conditions, then compare the evidence."
      />
      <ErrorBox error={err ?? cases.error ?? results.error} onRetry={() => { void cases.reload(); void results.reload(); }} />
      {!projectId && (
        <Alert kind="warn" title="No project selected">
          Choose or create a project on the Projects page before running the suite. Results below cover all projects.
        </Alert>
      )}

      <div className="grid two">
        <Section
          title="Benchmark suite"
          hint={`${chosen.length} of ${visible.length} selected`}
          id="suite"
          actions={
            <>
              <label className="sr-only" htmlFor="suite-language">
                Language filter
              </label>
              <select id="suite-language" value={language} onChange={(e) => setLanguage(e.target.value as Language | "")}>
                <option value="">All languages</option>
                <option value="python">Python</option>
                <option value="sql">SQL</option>
              </select>
              <button className="small" onClick={() => setSelected(new Set(visible.map((c) => c.id)))}>
                Select all
              </button>
              <button className="small quiet" onClick={() => setSelected(new Set())}>
                Clear
              </button>
            </>
          }
        >
          <div className="stack-sm">
            <div className="panel flush">
              <div className="table-wrap" style={{ maxHeight: 360 }} role="region" aria-label="Benchmark cases" tabIndex={0}>
                <table>
                  <thead>
                    <tr>
                      <th style={{ width: 36 }}>
                        <span className="sr-only">Include</span>
                      </th>
                      <th>Case</th>
                      <th>Expected rules</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visible.map((c) => (
                      <tr key={c.id}>
                        <td>
                          <input
                            type="checkbox"
                            aria-label={`Include ${c.id}`}
                            checked={selected.has(c.id)}
                            onChange={() =>
                              setSelected((prev) => {
                                const n = new Set(prev);
                                if (n.has(c.id)) n.delete(c.id);
                                else n.add(c.id);
                                return n;
                              })
                            }
                          />
                        </td>
                        <td>
                          <div className="mono">{c.id}</div>
                          <div className="muted">{c.title}</div>
                        </td>
                        <td>
                          <div className="row" style={{ gap: 4 }}>
                            {c.expected_rules.map((r) => (
                              <Badge key={r}>{r}</Badge>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="row spread">
              <fieldset className="row" style={{ border: 0, padding: 0, margin: 0 }}>
                <legend className="sr-only">Conditions to run</legend>
                <label className="row" style={{ gap: 6 }}>
                  <input type="checkbox" checked={conditions.includes("ai_only")} onChange={() => toggleCond("ai_only")} /> AI-only
                </label>
                <label className="row" style={{ gap: 6 }}>
                  <input type="checkbox" checked={conditions.includes("greencode")} onChange={() => toggleCond("greencode")} /> GreenCode
                </label>
              </fieldset>
              <button className="primary" onClick={() => void run()} disabled={!!running || !conditions.length || !projectId || chosen.length === 0}>
                {running ? <Spinner /> : <Icon name="play" />}
                {running ? "Suite running" : "Run suite"}
              </button>
            </div>
          </div>
        </Section>

        <Section title="Runs" id="runs">
          <div className="panel stack-sm">
            {jobs.data?.length ? (
              jobs.data.slice(0, 4).map((j) => {
                const last = j.results[j.results.length - 1];
                return (
                  <div key={j.job_id} className="stack-sm">
                    <div className="row spread">
                      <span>
                        <Badge kind={j.status === "completed" ? "ok" : j.status === "failed" ? "bad" : "warn"}>{j.status}</Badge>{" "}
                        <span className="muted">{fmt.date(j.started_at)}</span>
                      </span>
                      <span className="muted">
                        {j.done} of {j.total}
                      </span>
                    </div>
                    <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={j.total} aria-valuenow={j.done} aria-label="Suite progress">
                      <div style={{ width: `${j.total ? (100 * j.done) / j.total : 0}%` }} />
                    </div>
                    {j.error && <Alert kind="error">{j.error}</Alert>}
                    {j.status === "running" && last && (
                      <div className="muted">
                        Latest: {last.case_id}, {fmt.label(last.condition)}, {last.status}
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <Empty title="No runs in this server session">Start the suite to see progress here.</Empty>
            )}
            <p className="muted">Progress is kept in memory. Finished evidence is always stored in PostgreSQL and listed below.</p>
          </div>
        </Section>
      </div>

      {s && s.total_runs > 0 && (
        <div className="grid two">
          <Section title="Condition summary" id="summary">
            <div className="stack-sm">
              <div className="panel flush">
                <TableWrap label="Condition summary">
                  <table className="compare-table">
                    <thead>
                      <tr>
                        <th>Measure</th>
                        <th className="num">AI-only</th>
                        <th className="num">GreenCode</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map(([label, a, b, f]) => (
                        <tr key={label}>
                          <td>
                            {label === "Geomean speed-up" ? <Term id="geomean">{label}</Term> : label}
                          </td>
                          <td className="num">{a == null ? "–" : f(a)}</td>
                          <td className="num">{b == null ? "–" : f(b)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </TableWrap>
              </div>
              <p className="muted">
                Failures. AI-only: {failures(ai?.failures)}. GreenCode: {failures(gc?.failures)}.
              </p>
            </div>
          </Section>
          <Section title="Hypotheses" id="hypotheses">
            <div className="stack-sm">
              <HypothesisList summary={s} />
              <ConditionBars
                title="Geometric mean speed-up and energy ratio by condition"
                items={[
                  { label: "Geomean speed-up", ai_only: ai?.geomean_speedup ?? null, greencode: gc?.geomean_speedup ?? null },
                  { label: "Geomean energy ratio", ai_only: ai?.geomean_energy_ratio ?? null, greencode: gc?.geomean_energy_ratio ?? null },
                ]}
                format={(v) => `${v.toFixed(2)}×`}
              />
              <Legend items={[{ label: "AI-only", color: "ai_only" }, { label: "GreenCode", color: "greencode" }]} />
            </div>
          </Section>
        </div>
      )}

      <Section title="Per-case results" hint={projectId ? undefined : "All projects"} id="results">
        {results.data?.length ? <ResultsTable rows={results.data} /> : <Empty title="No results yet">Run the suite or optimise code from the Analyse page.</Empty>}
      </Section>
    </div>
  );
}

function ResultsTable({ rows }: { rows: ResultRow[] }) {
  const sorted = [...rows].sort((a, b) => (a.case_id ?? a.name).localeCompare(b.case_id ?? b.name) || a.condition.localeCompare(b.condition));
  return (
    <div className="panel flush">
      <TableWrap label="Per-case results">
        <table>
          <thead>
            <tr>
              <th>Case</th>
              <th>Condition</th>
              <th>Status</th>
              <th>Rules</th>
              <th className="num">Speed-up</th>
              <th className="num">Time</th>
              <th>Verdict</th>
              <th className="num">Energy</th>
              <th>Energy source</th>
              <th>Failure</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <tr key={r.optimisation_id} className="linked">
                <td className="link-cell">
                  <a href={`#/optimisations/${r.optimisation_id}`}>
                    <span className="mono">{r.case_id ?? r.name}</span>
                  </a>
                  <div className="muted">
                    {r.language}
                    {r.unchanged ? ", unchanged" : ""}
                  </div>
                </td>
                <td>
                  <ConditionLabel condition={r.condition} />
                </td>
                <td>
                  <Badge kind={r.status}>{r.status}</Badge>
                </td>
                <td>{r.rules.join(" ")}</td>
                <td className="num">{fmt.x(r.speedup)}</td>
                <td className="num">{fmt.pct(r.time_percent_change)}</td>
                <td>{r.verdict && <Badge kind={r.verdict}>{fmt.label(r.verdict)}</Badge>}</td>
                <td className="num">{fmt.pct(r.energy_percent_change)}</td>
                <td>
                  {r.energy_source} {r.energy_method && <Badge kind={r.energy_method === "measured" ? "ok" : r.energy_method === "derived" ? "info" : "warn"}>{r.energy_method}</Badge>}
                </td>
                <td className="muted">{r.failure_reason?.slice(0, 80)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>
    </div>
  );
}
